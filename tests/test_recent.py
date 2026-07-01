from datetime import datetime, timedelta, timezone
from ytrss.models import Video
from ytrss.recent import filter_recent


def _video(days_ago: float, now: datetime) -> Video:
    return Video(
        video_id="x",
        title="t",
        channel_title="c",
        published=now - timedelta(days=days_ago),
        thumbnail="",
    )


def test_keeps_inside_window_and_drops_outside():
    now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    videos = [_video(1, now), _video(13.9, now), _video(14.1, now), _video(40, now)]
    kept = filter_recent(videos, now=now, window_days=14)
    assert len(kept) == 2


def test_result_sorted_newest_first():
    now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    videos = [_video(5, now), _video(1, now), _video(3, now)]
    kept = filter_recent(videos, now=now, window_days=14)
    assert [v.published for v in kept] == sorted(
        (v.published for v in kept), reverse=True
    )
