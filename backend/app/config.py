from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
STORE_PATH = DATA_DIR / "store.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI 招聘初筛 Agent"
    app_version: str = "1.0.0"
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    database_url: str = f"sqlite:///{DATA_DIR / 'hiremind.db'}"
    max_batch_files: int = 200
    max_file_size_mb: int = 20
    worker_lease_seconds: int = 300

    # Optional LLM — empty = rule-based mock scoring
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # Later: Feishu webhook
    feishu_webhook_url: str = ""


settings = Settings()
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
