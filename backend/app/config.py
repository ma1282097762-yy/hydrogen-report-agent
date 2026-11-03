import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except Exception:
    pass


def _env(name, default=""):
    v = os.environ.get(name)
    return v if v not in (None, "") else default


def _int(name, default):
    try:
        return int(_env(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name, default):
    try:
        return float(_env(name, str(default)))
    except (TypeError, ValueError):
        return default


class Settings:
    def __init__(self):
        self.model_api_key = _env("MODEL_API_KEY", "")
        self.model_base_url = _env("MODEL_BASE_URL", "https://api.deepseek.com")
        self.model_name = _env("MODEL_NAME", "deepseek-chat")
        self.model_timeout = _float("MODEL_TIMEOUT", 120.0)
        self.model_max_retries = _int("MODEL_MAX_RETRIES", 3)
        self.data_dir = Path(_env("DATA_DIR", str(BACKEND_DIR / "data")))
        if not self.data_dir.is_absolute():
            self.data_dir = BACKEND_DIR / self.data_dir
        self.upload_max_bytes = _int("UPLOAD_MAX_BYTES", 100 * 1024 * 1024)
        self.chunk_size = _int("CHUNK_SIZE", 800)
        self.chunk_overlap = _int("CHUNK_OVERLAP", 100)
        self.max_target_words = _int("MAX_TARGET_WORDS", 18000)
        self.default_target_words = _int("DEFAULT_TARGET_WORDS", 12000)
        self.uploads_dir = self.data_dir / "uploads"
        self.db_url = _env("DATABASE_URL", f"sqlite:///{self.data_dir / 'app.db'}")

    def ensure_dirs(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
