from datetime import datetime, timedelta
from ytrss.models import Video


def filter_recent(videos: list[Video], *, now: datetime, window_days: int) -> list[Video]:
    cutoff = now - timedelta(days=window_days)
    kept = [v for v in videos if v.published >= cutoff]
    kept.sort(key=lambda v: v.published, reverse=True)
    return kept
