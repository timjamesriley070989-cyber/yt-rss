from datetime import datetime
from ytrss.models import Video


def relative_time(published: datetime, now: datetime) -> str:
    seconds = (now - published).total_seconds()
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    return f"{days}d ago"


def day_label(published: datetime, now: datetime) -> str:
    delta_days = (now.date() - published.date()).days
    if delta_days <= 0:
        return "Today"
    if delta_days == 1:
        return "Yesterday"
    return published.strftime("%b %-d, %Y")


def group_by_day(videos: list[Video], now: datetime) -> list[tuple[str, list[Video]]]:
    groups: list[tuple[str, list[Video]]] = []
    for video in sorted(videos, key=lambda v: v.published, reverse=True):
        label = day_label(video.published, now)
        if groups and groups[-1][0] == label:
            groups[-1][1].append(video)
        else:
            groups.append((label, [video]))
    return groups
