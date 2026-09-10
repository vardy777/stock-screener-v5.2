"""Retired Phase 1B-1 publisher retained as an explicit fail-closed entrypoint."""


def main() -> int:
    raise RuntimeError(
        "daily-bar-d-close-v1 is superseded; use publish_daily_bar_availability.py"
    )


if __name__ == "__main__":
    raise SystemExit(main())
