from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    gemini_api_key: str
    openrouter_api_key: str
    telegram_bot_token: str
    telegram_channel_id: str
    default_timezone: str
    content_plan_path: Path
    prompt_path: Path
    posts_path: Path
    state_path: Path
    autopublish_hour: int
    autopublish_minute: int
    openai_model: str
    gemini_model: str
    openrouter_model: str
    content_source: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_channel_id=os.getenv("TELEGRAM_CHANNEL_ID", ""),
            default_timezone=os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow"),
            content_plan_path=Path(os.getenv("CONTENT_PLAN_PATH", "content-plan-infosec.md")),
            prompt_path=Path(os.getenv("PROMPT_PATH", "docs/autoposting-prompt.md")),
            posts_path=Path(os.getenv("POSTS_PATH", "posts")),
            state_path=Path(os.getenv("STATE_PATH", "state/published.json")),
            autopublish_hour=int(os.getenv("AUTOPUBLISH_HOUR", "9")),
            autopublish_minute=int(os.getenv("AUTOPUBLISH_MINUTE", "0")),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "tencent/hy3:free"),
            content_source=os.getenv("CONTENT_SOURCE", "static"),
        )

    def validate_for_generation(self) -> None:
        missing = []
        if self.content_source == "openai" and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if self.content_source == "gemini" and not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if self.content_source == "openrouter" and not self.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")
        if not self.content_plan_path.exists():
            missing.append(f"CONTENT_PLAN_PATH ({self.content_plan_path})")
        if self.content_source in {"openai", "gemini", "openrouter"} and not self.prompt_path.exists():
            missing.append(f"PROMPT_PATH ({self.prompt_path})")
        if missing:
            raise RuntimeError("Missing required settings: " + ", ".join(missing))

    def validate_for_publish(self) -> None:
        self.validate_for_generation()
        missing = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_channel_id:
            missing.append("TELEGRAM_CHANNEL_ID")
        if missing:
            raise RuntimeError("Missing required settings: " + ", ".join(missing))
