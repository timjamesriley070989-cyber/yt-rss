import argparse
from datetime import datetime, timezone
from pathlib import Path
from ytrss.opml import parse_opml
from ytrss.fetch import fetch_all
from ytrss.recent import filter_recent
from ytrss.render import render_html

WINDOW_DAYS = 14
CONCURRENCY = 12


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the subscriptions dashboard.")
    parser.add_argument("--opml", default="subscriptions.opml")
    parser.add_argument("--output", default="dist/index.html")
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    channels = parse_opml(Path(args.opml).read_text())
    print(f"Fetching {len(channels)} channels...")
    videos, failed = fetch_all(channels, concurrency=args.concurrency)
    recent = filter_recent(videos, now=now, window_days=args.window_days)
    print(f"{len(recent)} videos in last {args.window_days} days; {len(failed)} channels failed.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(recent, now=now, failed_count=len(failed)))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
