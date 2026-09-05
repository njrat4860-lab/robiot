import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

ROOT = Path(__file__).resolve().parent.parent
ADMIN_IDS = [8740848665]

if load_dotenv is not None:
    load_dotenv(ROOT / ".env")


@dataclass
class BotConfig:
    token: str
    admin_ids: list = field(default_factory=list)
    db_path: str = str(ROOT / "data" / "bot.db")
    models_dir: str = str(ROOT / "models")


def load_config():
    token = _clean_token(os.getenv("BOT_TOKEN", ""))
    data_dir = os.getenv("DATA_DIR", str(ROOT / "data")).strip()
    db_path = os.getenv("DB_PATH", str(Path(data_dir) / "bot.db")).strip()
    models_dir = os.getenv("MODELS_DIR", str(ROOT / "models")).strip()
    return BotConfig(token=token, admin_ids=ADMIN_IDS, db_path=db_path, models_dir=models_dir)


def _clean_token(value):
    ignored = {"\u200b", "\u200c", "\u200d", "\ufeff"}
    return "".join(char for char in value if not char.isspace() and char not in ignored)
