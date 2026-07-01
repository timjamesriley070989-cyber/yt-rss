from datetime import datetime, timedelta, timezone
from ytrss.models import Video
from ytrss.recent import filter_recent


def _video(hours_ago: float, now: datetime) -> Video:
    return Video(
        video_id="x",
        title="t",
        channel_title="c",
        published=now - timedelta(hours=hours_ago),
        thumbnail="",
    )


def test_keeps_inside_window_and_drops_outside():
    now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    videos = [_video(1, now), _video(23.9, now), _video(24.1, now), _video(72, now)]
    kept = filter_recent(videos, now=now, window_hours=24)
    assert len(kept) == 2


def test_result_sorted_newest_first():
    now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    videos = [_video(20, now), _video(1, now), _video(10, now)]
    kept = filter_recent(videos, now=now, window_hours=24)
    assert [v.published for v in kept] == sorted(
        (v.published for v in kept), reverse=True
    )
