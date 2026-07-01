from datetime import datetime, timezone
from pathlib import Path
from ytrss.models import Video
from ytrss.cache import load_cache, save_cache

NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _v(vid, cid_title="Chan"):
    return Video(video_id=vid, title="t", channel_title=cid_title,
                 published=NOW, thumbnail="https://i.ytimg.com/x.jpg")


def test_round_trip_preserves_videos(tmp_path):
    path = tmp_path / "feeds.json"
    data = {"c1": [_v("a"), _v("b")], "c2": [_v("c")]}
    save_cache(str(path), data)
    loaded = load_cache(str(path))
    assert set(loaded.keys()) == {"c1", "c2"}
    assert [v.video_id for v in loaded["c1"]] == ["a", "b"]
    assert loaded["c1"][0].published == NOW  # tz-aware datetime intact
    assert loaded["c1"][0].published.tzinfo is not None


def test_missing_file_returns_empty(tmp_path):
    assert load_cache(str(tmp_path / "nope.json")) == {}


def test_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    assert load_cache(str(path)) == {}


def test_bad_record_is_skipped(tmp_path):
    path = tmp_path / "feeds.json"
    path.write_text('{"feeds": {"c1": [{"video_id": "a"}, {"bogus": 1}]}}')
    loaded = load_cache(str(path))
    assert "c1" in loaded
    assert all(hasattr(v, "video_id") for v in loaded["c1"])


from ytrss.models import Channel
from ytrss.cache import merge_feeds


def _chan(cid):
    return Channel(channel_id=cid, title=cid, url="u")


def test_merge_fresh_wins_failed_falls_back_missing_counted():
    channels = [_chan("c1"), _chan("c2"), _chan("c3")]
    fetched = {"c1": [_v("fresh1")]}                 # c1 fetched OK
    cache = {"c2": [_v("cached2")]}                  # c2 failed but cached
    # c3 failed and has no cache -> missing
    new_cache, fell_back, missing = merge_feeds(channels, fetched, cache)
    assert [v.video_id for v in new_cache["c1"]] == ["fresh1"]
    assert [v.video_id for v in new_cache["c2"]] == ["cached2"]
    assert new_cache["c3"] == []
    assert fell_back == 1
    assert missing == 1


def test_merge_drops_channels_not_in_current_opml():
    channels = [_chan("c1")]
    fetched = {"c1": [_v("a")]}
    cache = {"old": [_v("z")]}       # "old" no longer subscribed
    new_cache, _, _ = merge_feeds(channels, fetched, cache)
    assert set(new_cache.keys()) == {"c1"}
