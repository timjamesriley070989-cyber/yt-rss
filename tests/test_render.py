from datetime import datetime, timedelta, timezone
from ytrss.models import Video
from ytrss.render import relative_time, day_label, group_by_day

NOW = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


def _video(when: datetime, title="t", channel="c") -> Video:
    return Video(video_id="x", title=title, channel_title=channel,
                 published=when, thumbnail="")


def test_relative_time():
    assert relative_time(NOW - timedelta(minutes=30), NOW) == "30m ago"
    assert relative_time(NOW - timedelta(hours=2), NOW) == "2h ago"
    assert relative_time(NOW - timedelta(days=3), NOW) == "3d ago"


def test_day_label():
    assert day_label(NOW, NOW) == "Today"
    assert day_label(NOW - timedelta(days=1), NOW) == "Yesterday"
    assert day_label(datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc), NOW) == "Jun 20, 2026"


def test_group_by_day_orders_groups_newest_first():
    videos = [
        _video(NOW - timedelta(hours=1)),
        _video(NOW - timedelta(days=1, hours=1)),
        _video(NOW - timedelta(hours=2)),
    ]
    groups = group_by_day(videos, NOW)
    assert [label for label, _ in groups] == ["Today", "Yesterday"]
    assert len(groups[0][1]) == 2
