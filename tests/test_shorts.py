from datetime import datetime, timezone
from ytrss.models import Video
from ytrss.shorts import filter_out_shorts

NOW = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


def _video(vid: str) -> Video:
    return Video(video_id=vid, title="t", channel_title="c", published=NOW, thumbnail="")


def test_removes_shorts_keeps_longform_and_preserves_order():
    videos = [_video("a"), _video("b"), _video("c")]

    def checker(vid):  # "b" is a Short
        return vid == "b"

    kept = filter_out_shorts(videos, checker=checker, concurrency=3)
    assert [v.video_id for v in kept] == ["a", "c"]


def test_checker_error_keeps_the_video():
    videos = [_video("a")]

    def checker(vid):
        raise TimeoutError("boom")

    kept = filter_out_shorts(videos, checker=checker, concurrency=1)
    assert [v.video_id for v in kept] == ["a"]


def test_empty_input():
    assert filter_out_shorts([]) == []
