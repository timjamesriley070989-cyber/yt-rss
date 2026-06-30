import re
import xml.etree.ElementTree as ET
from ytrss.models import Channel

# The OPML format uses attribute names with spaces ("Channel Url", "Channel Title")
# which is invalid XML. Pre-process the text to rename them before parsing.
_ATTR_MAP = {
    "Channel Url": "channel_url",
    "Channel Title": "channel_title",
}


def _sanitize(text: str) -> str:
    for old, new in _ATTR_MAP.items():
        text = text.replace(old + "=", new + "=")
    return text


def parse_opml(text: str) -> list[Channel]:
    root = ET.fromstring(_sanitize(text))
    channels: list[Channel] = []
    for outline in root.iter("outline"):
        channel_id = outline.get("text")
        url = outline.get("channel_url")
        title = outline.get("channel_title")
        if not channel_id or not url:
            continue
        channels.append(Channel(channel_id=channel_id, title=title or channel_id, url=url))
    return channels
