import random
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable
from ytrss.models import Channel, Video
from ytrss.feed import feed_url, parse_feed

USER_AGENT = "yt-rss-dashboard/1.0 (+https://github.com)"


def fetch_feed(channel_id: str, *, timeout: float = 15.0, retries: int = 2) -> str:
    url = feed_url(channel_id)
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as err:  # noqa: BLE001 - any network/parse error is retryable
            last_err = err
            if attempt < retries:
                # Short backoff + jitter: recovers quick blips without dragging out a
                # run when the IP is being sustained-throttled (better fast-and-partial).
                time.sleep(0.5 * (attempt + 1) + random.uniform(0, 0.3))
    raise last_err


def fetch_all(
    channels: list[Channel],
    *,
    fetcher: Callable[[str], str] = fetch_feed,
    concurrency: int = 12,
) -> tuple[dict[str, list[Video]], list[Channel]]:
    """Fetch every channel's feed in parallel. Returns (fetched, failed) where
    `fetched` maps channel_id -> parsed videos for channels that succeeded, and
    `failed` is the list of Channels whose fetch or parse failed."""
    fetched: dict[str, list[Video]] = {}
    failed: list[Channel] = []

    def work(channel: Channel):
        return channel, fetcher(channel.channel_id)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for channel, result in _imap(pool, work, channels):
            if result is None:
                failed.append(channel)
            else:
                try:
                    fetched[channel.channel_id] = parse_feed(result)
                except Exception:  # noqa: BLE001 - malformed feed = failed channel
                    failed.append(channel)
    return fetched, failed


def _imap(pool, work, channels):
    futures = {pool.submit(work, c): c for c in channels}
    for future in as_completed(futures):
        channel = futures[future]
        try:
            _, result = future.result()
            yield channel, result
        except Exception:  # noqa: BLE001 - fetch failed
            yield channel, None
