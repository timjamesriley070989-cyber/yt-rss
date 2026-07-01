from ytrss.models import Channel
from ytrss.fetch import fetch_all
from pathlib import Path

SAMPLE = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text()


def _channels(n):
    return [Channel(channel_id=f"c{i}", title=f"t{i}", url="u") for i in range(n)]


def test_fetch_all_returns_per_channel_success_and_failures():
    def fake_fetcher(channel_id):
        if channel_id == "c1":
            raise TimeoutError("boom")
        return SAMPLE

    fetched, failed = fetch_all(_channels(3), fetcher=fake_fetcher, concurrency=3)
    assert set(fetched.keys()) == {"c0", "c2"}
    assert all(len(v) > 0 for v in fetched.values())          # entries parsed
    assert [c.channel_id for c in failed] == ["c1"]           # Channel objects
