import os
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent.parent
GLOSSARY_PATH = BASE_DIR / "glossary.json"
DB_PATH       = BASE_DIR / "data" / "progress.duckdb"
STATIC_DIR    = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
OLLAMA_MODEL  = "mistral"
# Optional sub-path when running behind a reverse proxy, e.g. "/comlab"
ROOT_PATH     = os.environ.get("ROOT_PATH", "").rstrip("/")
