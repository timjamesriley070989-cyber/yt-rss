import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from ytrss.models import Video

USER_AGENT = "yt-rss-dashboard/1.0 (+https://github.com)"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Suppress redirects so we can observe the raw status of /shorts/<id>."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)


def is_short(video_id: str, *, timeout: float = 10.0) -> bool:
    """A real Short serves HTTP 200 at youtube.com/shorts/<id>; a regular video
    redirects (303) to /watch. Any error is treated as 'not a Short' so we never
    drop a real upload on a transient failure."""
    url = f"https://www.youtube.com/shorts/{video_id}"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        resp = _opener.open(req, timeout=timeout)
        return resp.status == 200
    except urllib.error.HTTPError:
        return False  # 3xx redirect (or 4xx) => not a Short
    except Exception:  # noqa: BLE001 - network error => keep the video
        return False


def filter_out_shorts(
    videos: list[Video],
    *,
    checker: Callable[[str], bool] = is_short,
    concurrency: int = 24,
) -> list[Video]:
    """Return videos that are NOT Shorts, preserving input order."""
    if not videos:
        return []
    is_short_by_id: dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(checker, v.video_id): v for v in videos}
        for future in as_completed(futures):
            video = futures[future]
            try:
                is_short_by_id[video.video_id] = future.result()
            except Exception:  # noqa: BLE001 - keep on failure
                is_short_by_id[video.video_id] = False
    return [v for v in videos if not is_short_by_id.get(v.video_id, False)]
