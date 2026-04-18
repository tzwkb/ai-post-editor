"""
qa_module.py — AI QA + iterative repair.

AI QA: Sends rows to AI for comprehensive quality check (tags, punctuation,
       terminology, hallucination, context mismatches, etc.)
Repair: Re-sends failing rows to MTPE with QA failure context attached.
"""

import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from engine import (
    load_prompt, _call_api_raw,
    get_cell_text, parse_bold_markup,
    find_matching_terms, call_api,
    strip_json_fences,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

QA_BATCH_SIZE    = 1500   # max rows per AI QA call
QA_OVERLAP       = 50     # overlap between batches
MAX_REPAIR_ITERS = 2

COL_QA_STATUS = "QA Status"
COL_QA_FIXED  = "QA Fixed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_or_create_col(sheet, header_row: int, col_name: str) -> int:
    """Return column index for col_name; append it if not found."""
    for c in range(1, sheet.max_column + 2):
        if sheet.cell(row=header_row, column=c).value == col_name:
            return c
    new_col = sheet.max_column + 1
    sheet.cell(row=header_row, column=new_col).value = col_name
    return new_col


def _find_header_row(sheet, ref_col: int) -> int:
    """Return first row (1-3) where ref_col is non-empty, defaulting to 1."""
    return next(
        (r for r in range(1, 4) if sheet.cell(row=r, column=ref_col).value is not None),
        1
    )


def _row_term_context(row_idx: int, row_term_hits: dict) -> str:
    """
    Build a per-row terminology context string from MTPE-recorded hits.
    Returns empty string if no hits for this row.
    """
    hits = row_term_hits.get(row_idx)
    if not hits:
        return ""
    lines = "\n".join(f"  - {st} -> {tt}" for st, tt in hits)
    return f"\nTerminology hits for this row (verify consistency):\n{lines}"


# ---------------------------------------------------------------------------
# AI QA
# ---------------------------------------------------------------------------

def _parse_qa_json(raw: str) -> list:
    """Parse AI QA response into list of issue dicts. Returns [] on failure."""
    raw = strip_json_fences(raw)
    if not raw or raw.upper() == "PASS" or raw == "[]":
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
    except json.JSONDecodeError:
        m = re.search(r'\[[\s\S]*\]', raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return []


def _ai_qa_batch(rows: list, row_term_hits: dict = None) -> dict:
    """
    Send one batch of rows to AI QA.
    rows: list of (row_idx, source, translation, post_edit)
    row_term_hits: dict of row_idx -> [(st, tt)] from MTPE phase (per-row term context)
    Returns: dict of row_idx -> list of issue dicts
    """
    if not rows:
        return {}

    if row_term_hits is None:
        row_term_hits = {}

    input_lines = []
    for idx, src, tt, pe in rows:
        line = (
            f"[{idx}] ST: {src.replace(chr(10),' / ')} "
            f"| MT: {tt.replace(chr(10),' / ')} "
            f"| PE: {pe.replace(chr(10), r'\n')}"
        )
        term_ctx = _row_term_context(idx, row_term_hits)
        if term_ctx:
            line += term_ctx
        input_lines.append(line)

    input_block = "\n".join(input_lines)

    user_msg = (
        f"QA the following {len(rows)} rows of game localization text.\n"
        f"Only report Critical or Major errors.\n"
        f"Use the [N] row number as the 'line' field in your JSON output.\n"
        f"Where 'Terminology hits' are listed for a row, verify the exact term was used.\n"
        f"If all rows pass, return: []"
        f"\n\n--- INPUT ---\n{input_block}\n--- END ---"
    )

    raw = _call_api_raw([
        {"role": "system", "content": load_prompt("qa")},
        {"role": "user",   "content": user_msg},
    ], temperature=0.1)

    if raw is None:
        print(f"\n  [QA] API call failed.")
        return {}

    result = {}
    for issue in _parse_qa_json(raw):
        if not isinstance(issue, dict):
            continue
        line = issue.get("line") or issue.get("Line Number") or issue.get("line_number")
        if line is None:
            continue
        try:
            row_idx = int(str(line).strip("[] "))
        except (ValueError, TypeError):
            continue
        result.setdefault(row_idx, []).append(issue)
    return result


def ai_qa_sheet(rows: list, row_term_hits: dict = None) -> dict:
    """
    QA all rows, chunking automatically if > QA_BATCH_SIZE.
    row_term_hits: per-row terminology hits recorded during MTPE phase.
    Returns dict of row_idx -> list of issue dicts.
    """
    if row_term_hits is None:
        row_term_hits = {}

    if len(rows) <= QA_BATCH_SIZE:
        return _ai_qa_batch(rows, row_term_hits)

    merged = {}
    step = QA_BATCH_SIZE - QA_OVERLAP
    total_batches = (len(rows) + step - 1) // step
    for batch_num, i in enumerate(range(0, len(rows), step), 1):
        batch = rows[i: i + QA_BATCH_SIZE]
        print(f"    [QA] Batch {batch_num}/{total_batches} ({len(batch)} rows)...")
        for row_idx, issues in _ai_qa_batch(batch, row_term_hits).items():
            if row_idx not in merged:
                merged[row_idx] = issues
            else:
                existing = {iss.get("error_type") for iss in merged[row_idx]}
                merged[row_idx] += [iss for iss in issues if iss.get("error_type") not in existing]
    return merged


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------

def _repair_row(source: str, translation: str, post_edit: str,
                key: str, issues: list,
                glossary_hints: list = None, tm_refs: list = None) -> str | None:
    """Re-call MTPE API with QA failure context injected."""
    issue_lines = [
        f"  [{iss.get('severity','')}] {iss.get('error_type','')}: "
        f"{iss.get('issue_description','')} | Fix: {iss.get('suggested_fix','')}"
        for iss in issues
    ]
    qa_context = (
        "QA REVIEW FAILED — fix the following issues:\n"
        + "\n".join(issue_lines)
        + "\n\nCurrent (rejected) post-edit:\n" + post_edit
        + "\n\nProduce a corrected version using [[B]]..[[/B]] to mark changes."
    )
    return call_api(
        source_text=source,
        en_text=translation,
        key=key,
        glossary_hints=glossary_hints or [],
        ref_data=[{"note": "QA Failure — must fix", "value": qa_context}],
        tm_refs=tm_refs or [],
    )


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def qa_and_repair(sheet, post_edit_col: int, col_config: dict,
                  glossary: list = None, tm_index=None,
                  row_term_hits: dict = None) -> dict:
    """
    Full QA pipeline for one sheet.
    Runs AI QA, repairs failing rows, writes QA Status / QA Fixed columns.
    QA Status column stores the full raw JSON array of issues for each failing row.

    row_term_hits: dict of row_idx -> [(st, tt)] recorded during MTPE phase.
                   When provided, each row's QA prompt includes its specific
                   terminology hits for precise consistency checking.

    Returns {"pass": int, "total": int, "by_type": Counter, "fail_rows": list}
    """
    if row_term_hits is None:
        row_term_hits = {}

    header_row = _find_header_row(sheet, post_edit_col)

    tt_col  = col_config.get("tt", 1)
    st_col  = col_config.get("st")
    key_col = col_config.get("key")

    # Locate or append QA columns — NEVER use insert_cols (destroys CellRichText bold)
    qa_status_col = _find_or_create_col(sheet, header_row, COL_QA_STATUS)
    qa_fixed_col  = _find_or_create_col(sheet, header_row, COL_QA_FIXED)
    # Ensure QA Fixed comes after QA Status
    if qa_fixed_col <= qa_status_col:
        qa_fixed_col = qa_status_col + 1
        sheet.cell(row=header_row, column=qa_fixed_col).value = COL_QA_FIXED

    # Collect rows
    rows_to_qa = []
    for row_idx in range(header_row + 1, sheet.max_row + 1):
        pe = get_cell_text(sheet.cell(row=row_idx, column=post_edit_col))
        if not pe.strip():
            continue
        tt  = get_cell_text(sheet.cell(row=row_idx, column=tt_col))  if tt_col  else ""
        src = get_cell_text(sheet.cell(row=row_idx, column=st_col))  if st_col  else ""
        key = get_cell_text(sheet.cell(row=row_idx, column=key_col)) if key_col else ""
        rows_to_qa.append((row_idx, src, tt, pe, key))

    total = len(rows_to_qa)
    if total == 0:
        print("    [QA] No rows to check.")
        return {"pass": 0, "total": 0, "by_type": Counter(), "fail_rows": []}

    rows_with_hits = len(row_term_hits.keys() & {r[0] for r in rows_to_qa})
    print(f"    [QA] Checking {total} rows "
          f"({rows_with_hits} with terminology context)...")

    # AI QA — pass per-row term hits instead of a global termbase
    l2 = ai_qa_sheet(
        [(idx, src, tt, pe) for idx, src, tt, pe, _ in rows_to_qa],
        row_term_hits,
    )
    print(f"    [QA] {len(l2)} rows flagged.")

    # failing_issues: row_idx -> list of issue dicts (flat, no wrapper)
    failing_issues = dict(l2)

    row_lookup    = {r[0]: r for r in rows_to_qa}
    repaired      = {}
    still_failing = dict(failing_issues)

    # Repair loop
    for iteration in range(1, MAX_REPAIR_ITERS + 1):
        if not still_failing:
            break
        print(f"    [QA Repair] Iteration {iteration} — {len(still_failing)} rows...")

        # Snapshot still_failing so closure captures the current iteration's dict,
        # not a reference that will be rebound when the loop continues.
        _failing_snapshot = dict(still_failing)

        def do_repair(row_idx, _sf=_failing_snapshot):
            r = row_lookup[row_idx]
            src, tt, pe, key = r[1], r[2], repaired.get(row_idx, r[3]), r[4]
            all_iss = _sf[row_idx]
            hints   = find_matching_terms(src, glossary) if glossary else []
            tm_hits = tm_index.query(src) if tm_index and src.strip() else []
            return row_idx, _repair_row(src, tt, pe, key, all_iss, hints, tm_hits)

        repair_results = {}
        with ThreadPoolExecutor(max_workers=min(config.MAX_WORKERS, len(still_failing))) as ex:
            futures = {ex.submit(do_repair, rid): rid for rid in still_failing}
            for fut in as_completed(futures):
                row_idx, text = fut.result()
                if text:
                    repair_results[row_idx] = text

        # Update repaired dict and re-QA only rows that got new text
        repaired_rows = []
        repaired_idxs = set()
        for row_idx, text in repair_results.items():
            repaired[row_idx] = text
            r = row_lookup[row_idx]
            repaired_rows.append((row_idx, r[1], r[2], text))
            repaired_idxs.add(row_idx)

        if repaired_rows:
            re_l2 = ai_qa_sheet(repaired_rows, row_term_hits)
            still_failing = {
                idx: issues
                for idx, issues in still_failing.items()
                if idx not in repaired_idxs or re_l2.get(idx)
            }
            for idx in repaired_idxs:
                if idx in still_failing:
                    still_failing[idx] = re_l2.get(idx, [])

        print(f"    [QA Repair] {len(still_failing)} rows still failing.")

    # Write results
    by_type: Counter = Counter()
    fail_rows = []

    for row_idx, src, tt, pe, key in rows_to_qa:
        ai_list = still_failing.get(row_idx, [])
        if not ai_list:
            qa_status = "FIXED" if row_idx in failing_issues else "PASS"
        else:
            qa_status = json.dumps(ai_list, ensure_ascii=False)
            for i in ai_list:
                by_type[i.get("error_type") or i.get("Error Type", "AI")] += 1
            fail_rows.append(row_idx)

        sheet.cell(row=row_idx, column=qa_status_col).value = qa_status
        if row_idx in repaired and repaired[row_idx] != pe:
            sheet.cell(row=row_idx, column=qa_fixed_col).value = \
                parse_bold_markup(repaired[row_idx], original=pe)

    pass_count = total - len(fail_rows)
    print(f"\n    [QA Done] {pass_count}/{total} PASS, {len(fail_rows)} still failing.")
    return {"pass": pass_count, "total": total, "by_type": by_type, "fail_rows": fail_rows}
