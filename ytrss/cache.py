import json
import sys
from datetime import datetime
from pathlib import Path
from ytrss.models import Channel, Video


def video_to_dict(v: Video) -> dict:
    return {
        "video_id": v.video_id,
        "title": v.title,
        "channel_title": v.channel_title,
        "published": v.published.isoformat(),
        "thumbnail": v.thumbnail,
    }


def video_from_dict(d: dict) -> Video:
    return Video(
        video_id=d["video_id"],
        title=d["title"],
        channel_title=d["channel_title"],
        published=datetime.fromisoformat(d["published"]),
        thumbnail=d["thumbnail"],
    )


def load_cache(path: str) -> dict[str, list[Video]]:
    """Read the feeds cache. Missing/corrupt file -> {}. Bad records are skipped."""
    try:
        raw = json.loads(Path(path).read_text())
        feeds = raw.get("feeds", {})
    except (OSError, ValueError, AttributeError):
        return {}
    result: dict[str, list[Video]] = {}
    for channel_id, records in feeds.items():
        videos: list[Video] = []
        for rec in records:
            try:
                videos.append(video_from_dict(rec))
            except (KeyError, ValueError, TypeError):
                continue
        result[channel_id] = videos
    return result


def save_cache(path: str, feeds_by_channel: dict[str, list[Video]]) -> None:
    """Write the feeds cache. A save failure is logged, never raised."""
    try:
        data = {"feeds": {
            channel_id: [video_to_dict(v) for v in videos]
            for channel_id, videos in feeds_by_channel.items()
        }}
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
    except OSError as err:  # noqa: BLE001 - cache save must not fail the build
        print(f"warning: could not save cache to {path}: {err}", file=sys.stderr)


def merge_feeds(
    channels: list[Channel],
    fetched: dict[str, list[Video]],
    cache: dict[str, list[Video]],
) -> tuple[dict[str, list[Video]], int, int]:
    """Combine fresh fetches with cached data for the current channel set.

    Fresh entries win; a channel absent from `fetched` falls back to `cache`;
    a channel in neither yields []. Returns (new_cache, fell_back, missing) where
    new_cache is keyed only by current-OPML channel ids.
    """
    new_cache: dict[str, list[Video]] = {}
    fell_back = 0
    missing = 0
    for channel in channels:
        cid = channel.channel_id
        if cid in fetched:
            new_cache[cid] = fetched[cid]
        elif cache.get(cid):
            new_cache[cid] = cache[cid]
            fell_back += 1
        else:
            new_cache[cid] = []
            missing += 1
    return new_cache, fell_back, missing
