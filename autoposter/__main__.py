from __future__ import annotations

import argparse

from autoposter.runner import main


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and publish infosec Telegram posts.")
    parser.add_argument("--once", action="store_true", help="Run one publishing attempt and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Generate and print without Telegram publish.")
    parser.add_argument("--date", help="Override date in YYYY-MM-DD or DD.MM.YYYY format.")
    parser.add_argument("--topic", help="Generate an ad-hoc post for this topic instead of using the calendar.")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
