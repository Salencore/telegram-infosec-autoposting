from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from autoposter.content_plan import CalendarEntry
from autoposter.generator import build_user_prompt


def generate_gemini_post(api_key: str, model: str, system_prompt: str, entry: CalendarEntry, full_plan: str) -> dict:
    input_text = build_user_prompt(entry, full_plan)
    payload = {
        "model": model,
        "system_instruction": system_prompt,
        "input": (
            f"{input_text}\n\n"
            "Верни только валидный JSON без markdown-блока, без пояснений и без текста вне JSON."
        ),
        "generation_config": {
            "temperature": 0.9,
        },
    }
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API error {exc.code}: {detail}") from exc

    text = data.get("output_text") or _extract_output_text(data)
    if not text:
        raise RuntimeError("Gemini response did not include output text")
    return json.loads(_strip_json_fence(text))


def _extract_output_text(data: dict) -> str:
    parts: list[str] = []
    for step in data.get("steps", []):
        for content in step.get("content", []):
            text = content.get("text")
            if text:
                parts.append(text)
    return "\n".join(parts)


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.S)
    if match:
        return match.group(1).strip()
    return stripped
