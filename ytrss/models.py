from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Channel:
    channel_id: str
    title: str
    url: str


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    channel_title: str
    published: datetime  # timezone-aware (UTC)
    thumbnail: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"
