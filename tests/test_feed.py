from pathlib import Path
from datetime import timezone
from ytrss.feed import parse_feed, feed_url

FIXTURE = Path(__file__).parent / "fixtures" / "sample_feed.xml"


def test_feed_url_template():
    assert feed_url("ABC123") == "https://www.youtube.com/feeds/videos.xml?channel_id=ABC123"


def test_parses_entries():
    videos = parse_feed(FIXTURE.read_text())
    assert len(videos) >= 1


def test_entry_fields():
    video = parse_feed(FIXTURE.read_text())[0]
    assert video.video_id
    assert video.title
    assert video.channel_title == "Gael Breton"
    assert video.published.tzinfo is not None  # timezone-aware
    assert video.thumbnail.startswith("https://")
    assert video.url == f"https://www.youtube.com/watch?v={video.video_id}"
