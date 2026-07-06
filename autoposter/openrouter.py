from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from autoposter.content_plan import CalendarEntry
from autoposter.generator import RESPONSE_SCHEMA, build_user_prompt


def generate_openrouter_post(
    api_key: str,
    model: str,
    system_prompt: str,
    entry: CalendarEntry,
    full_plan: str,
) -> dict:
    user_prompt = (
        f"{build_user_prompt(entry, full_plan)}\n\n"
        "Верни только валидный JSON без markdown-блока, без пояснений и без текста вне JSON."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.9,
        "max_tokens": 2500,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "telegram_infosec_post",
                "strict": False,
                "schema": RESPONSE_SCHEMA,
            },
        },
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
    text = choices[0].get("message", {}).get("content", "")
    if not text:
        raise RuntimeError("OpenRouter response did not include message content")
    return json.loads(_strip_json_fence(text))


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.S)
    if match:
        return match.group(1).strip()
    return stripped
