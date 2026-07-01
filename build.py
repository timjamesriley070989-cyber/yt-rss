import argparse
from datetime import datetime, timezone
from pathlib import Path
from ytrss.opml import parse_opml
from ytrss.fetch import fetch_all
from ytrss.recent import filter_recent
from ytrss.shorts import filter_out_shorts
from ytrss.render import render_html

WINDOW_HOURS = 24
CONCURRENCY = 12
SHORTS_CONCURRENCY = 24


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the subscriptions dashboard.")
    parser.add_argument("--opml", default="subscriptions.opml")
    parser.add_argument("--output", default="dist/index.html")
    parser.add_argument("--window-hours", type=int, default=WINDOW_HOURS)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    parser.add_argument("--shorts-concurrency", type=int, default=SHORTS_CONCURRENCY)
    parser.add_argument("--keep-shorts", action="store_true",
                        help="skip Shorts filtering (keep Shorts in the feed)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    channels = parse_opml(Path(args.opml).read_text())
    print(f"Fetching {len(channels)} channels...")
    videos, failed = fetch_all(channels, concurrency=args.concurrency)
    recent = filter_recent(videos, now=now, window_hours=args.window_hours)

    if args.keep_shorts:
        kept = recent
    else:
        kept = filter_out_shorts(recent, concurrency=args.shorts_concurrency)
    print(f"{len(recent)} videos in last {args.window_hours}h; "
          f"{len(recent) - len(kept)} Shorts removed; {len(failed)} channels failed.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(kept, now=now, failed_count=len(failed)))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
