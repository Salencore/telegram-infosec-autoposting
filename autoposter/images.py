from __future__ import annotations

import textwrap
from pathlib import Path

from autoposter.content_plan import CalendarEntry


def build_post_image(entry: CalendarEntry, output_dir: Path) -> Path | None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{entry.publish_date:%Y-%m-%d}.png"

    width, height = 1280, 720
    image = Image.new("RGB", (width, height), "#101010")
    draw = ImageDraw.Draw(image)

    palette = _palette(entry.day)
    top_text, left_text, right_text, bottom_text = _meme_text(entry)

    draw.rectangle((0, 0, width, height), fill=palette["bg"])
    draw.rectangle((0, 0, width, 96), fill=palette["top"])
    draw.rectangle((0, height - 118, width, height), fill=palette["bottom"])

    _draw_centered_text(draw, top_text, (0, 12, width, 90), _font(42, bold=True), "#ffffff", stroke=3)

    panel_top = 118
    panel_bottom = height - 140
    gap = 28
    panel_width = (width - 96 - gap) // 2
    left_box = (48, panel_top, 48 + panel_width, panel_bottom)
    right_box = (48 + panel_width + gap, panel_top, width - 48, panel_bottom)

    draw.rounded_rectangle(left_box, radius=18, fill=palette["left"], outline="#ffffff", width=4)
    draw.rounded_rectangle(right_box, radius=18, fill=palette["right"], outline="#ffffff", width=4)

    _draw_meme_face(draw, left_box, mood="calm")
    _draw_meme_face(draw, right_box, mood="panic")

    _draw_centered_multiline(draw, left_text, left_box, _font(44, bold=True), "#ffffff", stroke=3, y_offset=280)
    _draw_centered_multiline(draw, right_text, right_box, _font(44, bold=True), "#ffffff", stroke=3, y_offset=280)
    _draw_centered_text(draw, bottom_text, (28, height - 106, width - 28, height - 18), _font(40, bold=True), "#ffffff", stroke=3)

    image.save(path)
    return path


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, width: int, max_lines: int) -> list[str]:
    lines = textwrap.wrap(text, width=width, break_long_words=False, replace_whitespace=False)
    if len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    kept[-1] = kept[-1].rstrip(".") + "..."
    return kept


def _meme_text(entry: CalendarEntry) -> tuple[str, str, str, str]:
    title = entry.title.lower()
    if "интересны" in title:
        return (
            "ДА КОМУ Я НУЖЕН?",
            "Я: ничего важного нет",
            "СКАНЕР: уже проверяю",
            "ТЕБЯ ЛОМАЮТ НЕ ЗА СЛАВУ, А ЗА СЛАБУЮ ДВЕРЬ",
        )
    if "30 минут" in title:
        return (
            "ПРОВЕРЮ ПОТОМ",
            "Я: 30 минут нет",
            "ИНЦИДЕНТ: время нашлось?",
            "БЫСТРАЯ ПРОВЕРКА ДЕШЕВЛЕ БЫСТРОЙ ПАНИКИ",
        )
    if "антивирус" in title:
        return (
            "У МЕНЯ ЕСТЬ АНТИВИРУС",
            "Я: защищен",
            "ФИШИНГ: держи ссылку",
            "АНТИВИРУС НЕ ЧИТАЕТ МЫСЛИ ЗА БУХГАЛТЕРА",
        )
    if "фишинг" in title or "email" in title:
        return (
            "ОДНА ССЫЛКА",
            "Письмо: срочно открой",
            "Бизнес: неделя простоя",
            "ФИШИНГ БЬЕТ НЕ ПО ГЛУПОСТИ, А ПО СПЕШКЕ",
        )
    if "парол" in title:
        return (
            "ПАРОЛЬ СЛОЖНЫЙ",
            "Пароль: X7!qP...",
            "Заметки: я его храню",
            "СЛОЖНЫЙ ПАРОЛЬ В ЧАТЕ — ЭТО ПРОСТО ДЕКОР",
        )
    if "директора" in title or "сч" in title:
        return (
            "СРОЧНО ОПЛАТИ",
            "Аккаунт: похож на директора",
            "Бухгалтерия: уже бегу",
            "ДЕНЬГИ УВОДЯТ НЕ ВЗЛОМОМ, А ДОВЕРИЕМ",
        )
    if "уволенн" in title or "доступ" in title:
        return (
            "ОН УЖЕ НЕ РАБОТАЕТ",
            "HR: все оформили",
            "CRM: он все еще админ",
            "УВОЛЬНЕНИЕ БЕЗ ОТКЛЮЧЕНИЯ ДОСТУПОВ — ЛОТЕРЕЯ",
        )
    if "бэкап" in title or "резерв" in title:
        return (
            "БЭКАП ЕСТЬ",
            "Мы: спокойно",
            "Восстановление: не найдено",
            "БЭКАП БЕЗ ПРОВЕРКИ — ЭТО СКРИНШОТ СПОКОЙСТВИЯ",
        )
    return (
        "ВСЕ РАБОТАЕТ",
        "Бизнес: не трогай",
        "Безопасность: уже риск",
        "ЕСЛИ ДВЕРЬ НЕ ПРОВЕРЯТЬ, ЕЕ ПРОВЕРЯТ ЗА ТЕБЯ",
    )


def _palette(day: int) -> dict[str, str]:
    palettes = [
        {"bg": "#111827", "top": "#ef4444", "bottom": "#ef4444", "left": "#2563eb", "right": "#dc2626"},
        {"bg": "#0f172a", "top": "#22c55e", "bottom": "#a855f7", "left": "#475569", "right": "#7c3aed"},
        {"bg": "#18181b", "top": "#f97316", "bottom": "#0891b2", "left": "#334155", "right": "#ea580c"},
    ]
    return palettes[(day - 1) % len(palettes)]


def _draw_meme_face(draw, box: tuple[int, int, int, int], mood: str) -> None:
    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = y1 + 142
    face = "#fde68a" if mood == "calm" else "#fecaca"
    draw.ellipse((cx - 84, cy - 84, cx + 84, cy + 84), fill=face, outline="#111111", width=5)
    draw.ellipse((cx - 42, cy - 24, cx - 18, cy), fill="#111111")
    draw.ellipse((cx + 18, cy - 24, cx + 42, cy), fill="#111111")
    if mood == "panic":
        draw.arc((cx - 48, cy + 20, cx + 48, cy + 82), 190, 350, fill="#111111", width=6)
        draw.line((cx - 100, cy - 120, cx - 52, cy - 70), fill="#ffffff", width=6)
        draw.line((cx + 100, cy - 120, cx + 52, cy - 70), fill="#ffffff", width=6)
    else:
        draw.arc((cx - 46, cy + 6, cx + 46, cy + 68), 20, 160, fill="#111111", width=6)


def _draw_centered_text(draw, text: str, box: tuple[int, int, int, int], font, fill: str, stroke: int = 0) -> None:
    x1, y1, x2, y2 = box
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    x = x1 + ((x2 - x1) - (bbox[2] - bbox[0])) // 2
    y = y1 + ((y2 - y1) - (bbox[3] - bbox[1])) // 2
    draw.text((x, y), text, fill=fill, font=font, stroke_width=stroke, stroke_fill="#000000")


def _draw_centered_multiline(
    draw,
    text: str,
    box: tuple[int, int, int, int],
    font,
    fill: str,
    stroke: int,
    y_offset: int,
) -> None:
    x1, y1, x2, _ = box
    lines = _wrap(text.upper(), 18, max_lines=3)
    y = y1 + y_offset
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=stroke)
        x = x1 + ((x2 - x1) - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill=fill, font=font, stroke_width=stroke, stroke_fill="#000000")
        y += 58
