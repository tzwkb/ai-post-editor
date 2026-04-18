import os
from pathlib import Path

# ============================================================
# Directory Layout
# ============================================================
BASE_DIR   = Path(__file__).parent
INPUT_DIR  = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
TM_DIR     = BASE_DIR / "TM"
TB_DIR     = BASE_DIR / "TB"

# ============================================================
# API Configuration
# ============================================================
API_BASE_URL = "https://api.vectorengine.ai/v1"
API_KEY = os.getenv("OPENAI_API_KEY", "")

if not API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not set. "
        "Copy .env.example to .env and fill in your key, or export the env var."
    )
MODEL = "gemini-3.1-pro-preview"
MAX_TOKENS = 4096
TEMPERATURE = 0.3
REQUEST_TIMEOUT = 180  # seconds per request
MAX_RETRIES = 3
RETRY_DELAY = 2        # base delay (doubles each retry)
MAX_WORKERS = 100      # concurrent API requests

# ============================================================
# Output Settings
# ============================================================
OUTPUT_COLUMN_HEADER = "Post Edit EN"
OUTPUT_SUFFIX = "_postedit"

# ============================================================
# Prompt Settings
# ============================================================
# Change MTPE_PROJECT_FILE to switch projects.
# The file must exist in the prompts/ directory alongside mtpe_base.md.
MTPE_PROJECT_FILE = "mtpe_project_neoepoch.md"

# ============================================================
# Batch MTPE Settings
# ============================================================
# Number of rows to pack into a single MTPE API request.
# Higher = fewer API calls (lower cost), but risk of partial parse failures.
# Recommended: 10-20. Set to 1 to disable batching (one row per request).
MTPE_BATCH_SIZE = 15
