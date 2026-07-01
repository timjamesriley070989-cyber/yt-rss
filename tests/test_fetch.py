from ytrss.models import Channel
from ytrss.fetch import fetch_all
from pathlib import Path

SAMPLE = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text()


def _channels(n):
    return [Channel(channel_id=f"c{i}", title=f"t{i}", url="u") for i in range(n)]


def test_fetch_all_collects_videos_and_skips_failures():
    def fake_fetcher(channel_id):
        if channel_id == "c1":
            raise TimeoutError("boom")
        return SAMPLE

    videos, failed = fetch_all(_channels(3), fetcher=fake_fetcher, concurrency=3)
    assert len(failed) == 1
    assert failed == ["t1"]
    assert len(videos) > 0  # two channels' worth of entries parsed
