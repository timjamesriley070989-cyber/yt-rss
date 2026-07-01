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


# An entry with an empty <title></title> yields title text None; it must not crash
# parsing (and must not later crash html.escape). Empty title becomes "".
_FEED_EMPTY_TITLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns="http://www.w3.org/2005/Atom">
  <title>Some Channel</title>
  <entry>
    <yt:videoId>vid123</yt:videoId>
    <title></title>
    <published>2026-06-29T10:00:00+00:00</published>
    <media:group>
      <media:thumbnail url="https://i3.ytimg.com/vi/vid123/hq.jpg"/>
    </media:group>
  </entry>
</feed>
"""


def test_empty_title_does_not_crash_and_becomes_empty_string():
    videos = parse_feed(_FEED_EMPTY_TITLE)
    assert len(videos) == 1
    assert videos[0].title == ""
    assert videos[0].video_id == "vid123"
