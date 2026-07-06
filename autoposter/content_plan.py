from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class CalendarEntry:
    day: int
    publish_date: date
    title: str
    format: str
    hook: str


def parse_plan(path: Path) -> list[CalendarEntry]:
    rows: list[CalendarEntry] = []
    table_started = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("| День | Дата | Заголовок | Формат | Хук |"):
            table_started = True
            continue
        if not table_started:
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        if re.match(r"^\|\s*-+", line):
            continue

        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        day_raw, date_raw, title, content_format, hook = parts[:5]
        try:
            publish_date = datetime.strptime(date_raw, "%d.%m.%Y").date()
            rows.append(
                CalendarEntry(
                    day=int(day_raw),
                    publish_date=publish_date,
                    title=title,
                    format=content_format,
                    hook=hook,
                )
            )
        except ValueError:
            continue

    return rows


def find_entry(entries: list[CalendarEntry], target_date: date) -> CalendarEntry | None:
    for entry in entries:
        if entry.publish_date == target_date:
            return entry
    return None


def parse_target_date(value: str | None, timezone_today: date) -> date:
    if not value:
        return timezone_today
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError("Date must be YYYY-MM-DD or DD.MM.YYYY")
