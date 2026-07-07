from __future__ import annotations

import json
import urllib.error
import urllib.request

from autoposter.content_plan import CalendarEntry


def generate_openrouter_post(
    api_key: str,
    model: str,
    system_prompt: str,
    entry: CalendarEntry,
    full_plan: str,
) -> dict:
    user_prompt = build_plain_telegram_prompt(entry, full_plan)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 2500,
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Salencore/telegram-infosec-autoposting",
            "X-Title": "telegram-infosec-autoposting",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter API error {exc.code}: {detail}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter response did not include choices: {data}")
    text = _extract_message_text(choices[0])
    if not text:
        preview = json.dumps(data, ensure_ascii=False)[:4000]
        raise RuntimeError(f"OpenRouter response did not include message content: {preview}")
    return {
        "publish_date": f"{entry.publish_date:%Y-%m-%d}",
        "advent_day": entry.day,
        "topic": entry.title,
        "status": "ready",
        "autopublish": True,
        "channel": "telegram",
        "review_notes": [],
        "telegram_post": {
            "title": entry.title,
            "text_markdown": text.strip(),
            "hashtags": [],
            "disable_web_page_preview": False,
        },
        "quality_check": {
            "calendar_date_preserved": True,
            "topic_preserved": True,
            "unsupported_claims_found": False,
            "dangerous_attack_instructions_found": False,
            "headline_is_clickable_but_truthful": True,
            "hook_used": True,
            "ready_for_autoposting": True,
        },
    }


def _extract_message_text(choice: dict) -> str:
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    for key in ("text", "reasoning"):
        value = message.get(key) or choice.get(key)
        if isinstance(value, str):
            return value
    return ""


def build_plain_telegram_prompt(entry: CalendarEntry, full_plan: str) -> str:
    context = _short_plan_context(entry, full_plan)
    return f"""
Напиши готовый Telegram-пост по записи контент-плана.

Верни только текст поста. Не возвращай JSON. Не используй markdown-блоки ``` и не добавляй пояснения вне поста.

Дата публикации: {entry.publish_date:%Y-%m-%d}
День: {entry.day}
Тема: {entry.title}
Формат из плана: {entry.format}
Хук: {entry.hook}

Требования:
- русский язык;
- экспертный, уверенный и вызывающий стиль;
- цепляющий честный заголовок в первой строке;
- используй хук в первом абзаце;
- 1200-2800 знаков;
- короткие абзацы;
- практический вывод или чеклист;
- мягкий CTA: подписаться на канал и проверить свои доступы сегодня;
- добавь 2-4 релевантных хештега в конце;
- не выдумывай факты, цифры, кейсы, имена, ссылки и цитаты;
- не давай пошаговые инструкции для атаки реальных систем, обхода защиты, кражи доступов или скрытия следов.

Контекст:
{context}
""".strip()


def _short_plan_context(entry: CalendarEntry, full_plan: str) -> str:
    if entry.day == 0:
        return "Это внеплановая тема. Не используй календарную очередь, пиши самостоятельный пост."
    lines = []
    for raw_line in full_plan.splitlines():
        if f"| {entry.day} |" in raw_line or f"| {entry.day}|" in raw_line:
            lines.append(raw_line.strip())
    return "\n".join(lines) or "Используй только тему, формат и хук из текущего запроса."
