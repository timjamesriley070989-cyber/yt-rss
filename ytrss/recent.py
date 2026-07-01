from datetime import datetime, timedelta
from ytrss.models import Video


def filter_recent(videos: list[Video], *, now: datetime, window_hours: int) -> list[Video]:
    cutoff = now - timedelta(hours=window_hours)
    kept = [v for v in videos if v.published >= cutoff]
    kept.sort(key=lambda v: v.published, reverse=True)
    return kept
