from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from autoposter.config import Settings
from autoposter.content_plan import find_entry, parse_plan, parse_target_date
from autoposter.gemini import generate_gemini_post
from autoposter.generator import generate_post
from autoposter.images import build_post_image
from autoposter.openrouter import generate_openrouter_post
from autoposter.prompt import extract_system_prompt
from autoposter.static_posts import load_static_post, render_static_post

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main(args) -> None:
    settings = Settings.from_env()
    if args.once:
        run_once(settings, dry_run=args.dry_run, date_override=args.date)
        return

    logger.info("Autoposter started")
    if settings.autopublish_interval_hours > 0:
        interval_seconds = settings.autopublish_interval_hours * 60 * 60
        while True:
            run_once(settings, dry_run=args.dry_run, date_override=None)
            logger.info("Next run in %s hour(s)", settings.autopublish_interval_hours)
            time.sleep(interval_seconds)

    while True:
        now = datetime.now(ZoneInfo(settings.default_timezone))
        target = now.replace(
            hour=settings.autopublish_hour,
            minute=settings.autopublish_minute,
            second=0,
            microsecond=0,
        )
        if target <= now:
            target += timedelta(days=1)
        sleep_seconds = max(1, int((target - now).total_seconds()))
        logger.info("Next run at %s", target.isoformat())
        time.sleep(sleep_seconds)
        run_once(settings, dry_run=args.dry_run, date_override=None)


def run_once(settings: Settings, dry_run: bool, date_override: str | None) -> None:
    if dry_run:
        settings.validate_for_generation()
    else:
        settings.validate_for_publish()

    timezone = ZoneInfo(settings.default_timezone)

    state = load_state(settings.state_path)

    entries = parse_plan(settings.content_plan_path)
    if date_override:
        target_date = parse_target_date(date_override, datetime.now(timezone).date())
        if not dry_run and str(target_date) in state.get("published", {}):
            logger.info("Post for %s already published", target_date)
            return
        entry = find_entry(entries, target_date)
    elif settings.autopublish_interval_hours > 0:
        entry = find_next_unpublished_entry(entries, state)
        target_date = entry.publish_date if entry else None
    else:
        target_date = parse_target_date(None, datetime.now(timezone).date())
        if not dry_run and str(target_date) in state.get("published", {}):
            logger.info("Post for %s already published", target_date)
            return
        entry = find_entry(entries, target_date)

    if not entry:
        logger.info("No content-plan entry to publish")
        return

    logger.info("Preparing post for day %s: %s", entry.day, entry.title)
    result = None
    if settings.content_source == "openai":
        full_plan = settings.content_plan_path.read_text(encoding="utf-8")
        system_prompt = extract_system_prompt(settings.prompt_path)
        result = generate_post(
            settings.openai_api_key,
            settings.openai_model,
            system_prompt,
            entry,
            full_plan,
        )
        validate_result(result)
        post_text = build_telegram_text(result)
    elif settings.content_source == "gemini":
        full_plan = settings.content_plan_path.read_text(encoding="utf-8")
        system_prompt = extract_system_prompt(settings.prompt_path)
        result = generate_gemini_post(
            settings.gemini_api_key,
            settings.gemini_model,
            system_prompt,
            entry,
            full_plan,
        )
        validate_result(result)
        post_text = build_telegram_text(result)
    elif settings.content_source == "openrouter":
        full_plan = settings.content_plan_path.read_text(encoding="utf-8")
        system_prompt = extract_system_prompt(settings.prompt_path)
        result = generate_openrouter_post(
            settings.openrouter_api_key,
            settings.openrouter_model,
            system_prompt,
            entry,
            full_plan,
        )
        validate_result(result)
        post_text = build_telegram_text(result)
    else:
        post_text = load_static_post(entry, settings.posts_path) or render_static_post(entry)

    if dry_run:
        print(post_text)
        image_path = build_post_image(entry, settings.image_output_dir)
        if image_path:
            print(f"\n[image] {image_path}")
        return

    image_path = build_post_image(entry, settings.image_output_dir)
    image_message_id = None
    if image_path:
        image_message_id = send_telegram_photo(
            settings.telegram_bot_token,
            settings.telegram_channel_id,
            image_path,
            caption=entry.title,
        )

    message_ids = send_telegram_messages(
        settings.telegram_bot_token,
        settings.telegram_channel_id,
        split_telegram_text(post_text),
        disable_web_page_preview=bool(result and result.get("telegram_post", {}).get("disable_web_page_preview", False)),
    )
    state.setdefault("published", {})[str(target_date)] = {
        "day": entry.day,
        "title": entry.title,
        "image_message_id": image_message_id,
        "message_ids": message_ids,
        "published_at": datetime.now(timezone).isoformat(),
    }
    save_state(settings.state_path, state)
    logger.info("Published %s message(s) for %s", len(message_ids), target_date)


def validate_result(result: dict) -> None:
    if result.get("status") != "ready":
        raise RuntimeError(f"Generated post is not ready: {result.get('review_notes')}")
    quality = result.get("quality_check", {})
    if not quality.get("ready_for_autoposting"):
        raise RuntimeError("Generated post failed ready_for_autoposting check")
    if quality.get("dangerous_attack_instructions_found"):
        raise RuntimeError("Generated post contains dangerous attack instructions")
    telegram_post = result.get("telegram_post") or {}
    if not telegram_post.get("text_markdown"):
        raise RuntimeError("Generated post does not include telegram_post.text_markdown")


def build_telegram_text(result: dict) -> str:
    post = result["telegram_post"]
    title = post.get("title") or result.get("article", {}).get("title") or result.get("topic", "")
    text = post["text_markdown"].strip()
    hashtags = " ".join(post.get("hashtags") or [])
    parts = [title.strip(), "", text]
    if hashtags:
        parts.extend(["", hashtags])
    return "\n".join(part for part in parts if part is not None).strip()


def split_telegram_text(text: str, limit: int = 3900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    return chunks


def find_next_unpublished_entry(entries, state: dict):
    published = set(state.get("published", {}).keys())
    for entry in sorted(entries, key=lambda item: item.day):
        if f"{entry.publish_date:%Y-%m-%d}" not in published:
            return entry
    return None


def send_telegram_photo(
    bot_token: str,
    chat_id: str,
    photo_path: Path,
    caption: str,
) -> int:
    boundary = "----autoposter-boundary"
    fields = {
        "chat_id": chat_id,
        "caption": caption[:1024],
    }
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (
            f'Content-Disposition: form-data; name="photo"; filename="{photo_path.name}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode("utf-8")
    )
    body.extend(photo_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendPhoto",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram photo API error {exc.code}: {detail}") from exc
    if not data.get("ok"):
        raise RuntimeError(f"Telegram photo API error: {data}")
    return int(data["result"]["message_id"])


def send_telegram_messages(
    bot_token: str,
    chat_id: str,
    messages: list[str],
    disable_web_page_preview: bool,
) -> list[int]:
    message_ids: list[int] = []
    for text in messages:
        payload = urllib.parse.urlencode(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": str(disable_web_page_preview).lower(),
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data=payload,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Telegram API error {exc.code}: {detail}") from exc
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error: {data}")
        message_ids.append(int(data["result"]["message_id"]))
    return message_ids


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"published": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
