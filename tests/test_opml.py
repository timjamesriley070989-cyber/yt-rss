from pathlib import Path
from ytrss.opml import parse_opml

FIXTURE = Path(__file__).parent / "fixtures" / "sample.opml"


def test_parses_all_channels():
    channels = parse_opml(FIXTURE.read_text())
    assert len(channels) == 2


def test_extracts_fields():
    channels = parse_opml(FIXTURE.read_text())
    first = channels[0]
    assert first.channel_id == "UC-9uQ57m8AVd2Q1MCaZgutA"
    assert first.title == "Gael Breton"
    assert first.url == "http://www.youtube.com/channel/UC-9uQ57m8AVd2Q1MCaZgutA"
