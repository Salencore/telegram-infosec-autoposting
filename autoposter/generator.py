from __future__ import annotations

import json
import urllib.error
import urllib.request

from autoposter.content_plan import CalendarEntry


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": True,
    "required": ["publish_date", "status", "telegram_post", "quality_check"],
    "properties": {
        "publish_date": {"type": "string"},
        "status": {"type": "string"},
        "telegram_post": {
            "type": "object",
            "additionalProperties": True,
            "required": ["title", "text_markdown"],
            "properties": {
                "title": {"type": "string"},
                "text_markdown": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
            },
        },
        "quality_check": {
            "type": "object",
            "additionalProperties": True,
            "required": ["ready_for_autoposting"],
            "properties": {
                "ready_for_autoposting": {"type": "boolean"},
                "dangerous_attack_instructions_found": {"type": "boolean"},
            },
        },
    },
}


def build_user_prompt(entry: CalendarEntry, full_plan: str) -> str:
    length = "до 3900 знаков, чтобы пост помещался в одно сообщение Telegram"
    return f"""
Подготовь материал для немедленного автопостинга в Telegram-канал.

Дата публикации:
{entry.publish_date:%Y-%m-%d}

Номер публикации / день контент-плана:
{entry.day}

Тема:
{entry.title}

Исходный заголовок из таблицы:
{entry.title}

Исходный формат из таблицы:
{entry.format}

Хук из таблицы:
{entry.hook}

Цель публикации:
дать экспертный, вызывающий и полезный материал по информационной безопасности

Целевая аудитория:
малый и средний бизнес, руководители, маркетологи, администраторы каналов, специалисты, которые отвечают за доступы и цифровую гигиену

Тональность:
экспертная, вызывающая, уверенная, с честным кликбейтом в заголовке

Ограничения:
не давай опасные пошаговые инструкции для атаки реальных систем; не выдумывай факты, цифры и источники

Продукт, услуга или CTA:
подписаться на канал и проверить свои доступы сегодня

Площадка публикации:
Telegram-канал

Требования к длине:
{length}

Контент-план полностью:
{full_plan}
""".strip()


def generate_post(api_key: str, model: str, system_prompt: str, entry: CalendarEntry, full_plan: str) -> dict:
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(entry, full_plan)},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "telegram_infosec_post",
                "schema": RESPONSE_SCHEMA,
                "strict": False,
            }
        },
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API error {exc.code}: {detail}") from exc

    text = data.get("output_text")
    if not text:
        text = _extract_output_text(data)
    if not text:
        raise RuntimeError("OpenAI response did not include output text")
    return json.loads(text)


def _extract_output_text(data: dict) -> str:
    parts: list[str] = []
    for item in data.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts)
