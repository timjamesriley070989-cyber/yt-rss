import xml.etree.ElementTree as ET
from datetime import datetime
from ytrss.models import Video

ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
MEDIA = "{http://search.yahoo.com/mrss/}"


def feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def parse_feed(xml_text: str) -> list[Video]:
    root = ET.fromstring(xml_text)
    channel_title_el = root.find(f"{ATOM}title")
    channel_title = channel_title_el.text if channel_title_el is not None else ""

    videos: list[Video] = []
    for entry in root.findall(f"{ATOM}entry"):
        video_id_el = entry.find(f"{YT}videoId")
        title_el = entry.find(f"{ATOM}title")
        published_el = entry.find(f"{ATOM}published")
        thumb_el = entry.find(f"{MEDIA}group/{MEDIA}thumbnail")
        if video_id_el is None or published_el is None:
            continue
        videos.append(
            Video(
                video_id=video_id_el.text,
                title=title_el.text if title_el is not None else "",
                channel_title=channel_title,
                published=datetime.fromisoformat(published_el.text),
                thumbnail=thumb_el.get("url") if thumb_el is not None else "",
            )
        )
    return videos
