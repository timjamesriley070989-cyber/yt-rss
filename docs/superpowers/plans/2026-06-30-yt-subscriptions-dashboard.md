# YouTube Subscriptions Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static dashboard that shows a merged, newest-first timeline of the last 14 days of uploads across 939 YouTube subscriptions, auto-refreshed every 3 hours and published to public GitHub Pages.

**Architecture:** One Python entry point (`build.py`) orchestrates a small package (`ytrss/`): parse OPML → fetch all channel RSS feeds in parallel → filter to the last 14 days → render one self-contained `dist/index.html`. A GitHub Actions cron workflow runs the script and deploys the output. The same script with `--output` produces a local file (phase-2 "mode A").

**Tech Stack:** Python 3.11+ (standard library only — `urllib`, `xml.etree.ElementTree`, `concurrent.futures`, `dataclasses`, `datetime`, `html`), `pytest` for tests, GitHub Actions + GitHub Pages for hosting. No runtime third-party dependencies (keeps the Action trivial).

---

## File Structure

| File | Responsibility |
|---|---|
| `subscriptions.opml` | Input: the 939-channel subscription list (copied into the repo) |
| `ytrss/__init__.py` | Package marker |
| `ytrss/models.py` | `Channel` and `Video` dataclasses (shared data model) |
| `ytrss/opml.py` | Parse OPML text → `list[Channel]` |
| `ytrss/feed.py` | Parse one feed's XML → `list[Video]`; feed URL template |
| `ytrss/fetch.py` | Network fetch of one feed + parallel fetch of all channels (failures skipped) |
| `ytrss/recent.py` | Filter videos to a rolling time window |
| `ytrss/render.py` | Time/day formatting, day grouping, and HTML rendering |
| `build.py` | CLI: wire everything together and write the output file |
| `tests/fixtures/sample.opml` | Small OPML fixture |
| `tests/fixtures/sample_feed.xml` | Captured real YouTube feed fixture |
| `tests/test_opml.py` | OPML parser tests |
| `tests/test_feed.py` | Feed parser tests |
| `tests/test_recent.py` | Window filter tests |
| `tests/test_render.py` | Formatting / grouping / render tests |
| `tests/test_fetch.py` | Parallel fetch tests (injected fake fetcher) |
| `.github/workflows/build.yml` | Cron + push workflow that builds and deploys to Pages |
| `.gitignore` | Ignore `dist/`, `__pycache__/`, `.superpowers/` |
| `README.md` | What it is, how to run locally, how deploy works |

---

## Task 1: Project scaffold

**Files:**
- Create: `.gitignore`, `ytrss/__init__.py`, `subscriptions.opml` (copied from Desktop)

- [ ] **Step 1: Initialize the repo and package layout**

```bash
cd /Users/timriley/yt-rss
git init
mkdir -p ytrss tests/fixtures .github/workflows dist
touch ytrss/__init__.py
cp /Users/timriley/Desktop/subscriptions.opml ./subscriptions.opml
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.pyc
dist/
.superpowers/
.pytest_cache/
.venv/
```

- [ ] **Step 3: Verify pytest is available**

Run: `python3 -m pytest --version`
Expected: prints a pytest version. If missing, run `python3 -m pip install pytest`.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: scaffold yt-rss project"
```

---

## Task 2: Data model

**Files:**
- Create: `ytrss/models.py`

- [ ] **Step 1: Write the dataclasses**

```python
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
```

- [ ] **Step 2: Sanity check import**

Run: `python3 -c "from ytrss.models import Channel, Video; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add ytrss/models.py
git commit -m "feat: add Channel and Video data model"
```

---

## Task 3: OPML parser

**Files:**
- Create: `tests/fixtures/sample.opml`, `tests/test_opml.py`, `ytrss/opml.py`

- [ ] **Step 1: Write the fixture `tests/fixtures/sample.opml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
<head><title>Converted CSV Data</title></head>
<body>
<outline text="UC-9uQ57m8AVd2Q1MCaZgutA" Channel Url="http://www.youtube.com/channel/UC-9uQ57m8AVd2Q1MCaZgutA" Channel Title="Gael Breton"></outline>
<outline text="UC-LEvHJ39VBW6s5lsKDs8Tw" Channel Url="http://www.youtube.com/channel/UC-LEvHJ39VBW6s5lsKDs8Tw" Channel Title="Money Untold"></outline>
</body>
</opml>
```

- [ ] **Step 2: Write the failing test `tests/test_opml.py`**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_opml.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ytrss.opml'`

- [ ] **Step 4: Write `ytrss/opml.py`**

```python
import xml.etree.ElementTree as ET
from ytrss.models import Channel


def parse_opml(text: str) -> list[Channel]:
    root = ET.fromstring(text)
    channels: list[Channel] = []
    for outline in root.iter("outline"):
        channel_id = outline.get("text")
        url = outline.get("Channel Url")
        title = outline.get("Channel Title")
        if not channel_id or not url:
            continue
        channels.append(Channel(channel_id=channel_id, title=title or channel_id, url=url))
    return channels
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_opml.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/sample.opml tests/test_opml.py ytrss/opml.py
git commit -m "feat: parse OPML into Channel list"
```

---

## Task 4: Feed parser

**Files:**
- Create: `tests/fixtures/sample_feed.xml`, `tests/test_feed.py`, `ytrss/feed.py`

- [ ] **Step 1: Capture a real feed as the fixture**

Run:
```bash
curl -s "https://www.youtube.com/feeds/videos.xml?channel_id=UC-9uQ57m8AVd2Q1MCaZgutA" -o tests/fixtures/sample_feed.xml
```
Expected: file exists and contains `<entry>` elements. Verify: `grep -c "<entry>" tests/fixtures/sample_feed.xml` prints a number ≥ 1.

- [ ] **Step 2: Write the failing test `tests/test_feed.py`**

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_feed.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ytrss.feed'`

- [ ] **Step 4: Write `ytrss/feed.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_feed.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/sample_feed.xml tests/test_feed.py ytrss/feed.py
git commit -m "feat: parse YouTube RSS feed into Video list"
```

---

## Task 5: Recent-window filter

**Files:**
- Create: `tests/test_recent.py`, `ytrss/recent.py`

- [ ] **Step 1: Write the failing test `tests/test_recent.py`**

```python
from datetime import datetime, timedelta, timezone
from ytrss.models import Video
from ytrss.recent import filter_recent


def _video(days_ago: float, now: datetime) -> Video:
    return Video(
        video_id="x",
        title="t",
        channel_title="c",
        published=now - timedelta(days=days_ago),
        thumbnail="",
    )


def test_keeps_inside_window_and_drops_outside():
    now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    videos = [_video(1, now), _video(13.9, now), _video(14.1, now), _video(40, now)]
    kept = filter_recent(videos, now=now, window_days=14)
    assert len(kept) == 2


def test_result_sorted_newest_first():
    now = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)
    videos = [_video(5, now), _video(1, now), _video(3, now)]
    kept = filter_recent(videos, now=now, window_days=14)
    assert [v.published for v in kept] == sorted(
        (v.published for v in kept), reverse=True
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_recent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ytrss.recent'`

- [ ] **Step 3: Write `ytrss/recent.py`**

```python
from datetime import datetime, timedelta
from ytrss.models import Video


def filter_recent(videos: list[Video], *, now: datetime, window_days: int) -> list[Video]:
    cutoff = now - timedelta(days=window_days)
    kept = [v for v in videos if v.published >= cutoff]
    kept.sort(key=lambda v: v.published, reverse=True)
    return kept
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_recent.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_recent.py ytrss/recent.py
git commit -m "feat: filter videos to rolling time window"
```

---

## Task 6: Formatting and day grouping

**Files:**
- Create: `tests/test_render.py`, `ytrss/render.py`

- [ ] **Step 1: Write the failing test `tests/test_render.py` (formatting portion)**

```python
from datetime import datetime, timedelta, timezone
from ytrss.models import Video
from ytrss.render import relative_time, day_label, group_by_day

NOW = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


def _video(when: datetime, title="t", channel="c") -> Video:
    return Video(video_id="x", title=title, channel_title=channel,
                 published=when, thumbnail="")


def test_relative_time():
    assert relative_time(NOW - timedelta(minutes=30), NOW) == "30m ago"
    assert relative_time(NOW - timedelta(hours=2), NOW) == "2h ago"
    assert relative_time(NOW - timedelta(days=3), NOW) == "3d ago"


def test_day_label():
    assert day_label(NOW, NOW) == "Today"
    assert day_label(NOW - timedelta(days=1), NOW) == "Yesterday"
    assert day_label(datetime(2026, 6, 20, 9, 0, tzinfo=timezone.utc), NOW) == "Jun 20, 2026"


def test_group_by_day_orders_groups_newest_first():
    videos = [
        _video(NOW - timedelta(hours=1)),
        _video(NOW - timedelta(days=1, hours=1)),
        _video(NOW - timedelta(hours=2)),
    ]
    groups = group_by_day(videos, NOW)
    assert [label for label, _ in groups] == ["Today", "Yesterday"]
    assert len(groups[0][1]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ytrss.render'`

- [ ] **Step 3: Write the formatting functions in `ytrss/render.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_render.py ytrss/render.py
git commit -m "feat: add time formatting and day grouping"
```

---

## Task 7: HTML rendering

**Files:**
- Modify: `tests/test_render.py`, `ytrss/render.py`

- [ ] **Step 1: Add the failing render test to `tests/test_render.py`**

```python
from ytrss.render import render_html


def test_render_html_contains_video_and_is_self_contained():
    videos = [_video(NOW - timedelta(hours=1), title="My Video", channel="Chan")]
    html = render_html(videos, now=NOW, failed_count=0)
    assert "My Video" in html
    assert "Chan" in html
    assert "Today" in html
    assert "https://www.youtube.com/watch?v=x" in html
    # self-contained: no external CSS/JS files referenced
    assert "<link rel=\"stylesheet\"" not in html
    assert "src=\"http" not in html.replace("https://i.ytimg.com", "")  # only thumbnails are remote


def test_render_html_reports_failures():
    html = render_html([], now=NOW, failed_count=7)
    assert "7" in html
    assert "no recent uploads" in html.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_render.py -v`
Expected: FAIL with `ImportError: cannot import name 'render_html'`

- [ ] **Step 3: Append `render_html` to `ytrss/render.py`**

```python
import html as _html

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subscriptions</title>
<style>
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{ font-family: -apple-system, system-ui, sans-serif; margin: 0; padding: 0 16px 48px;
       max-width: 820px; margin-inline: auto; }}
header {{ position: sticky; top: 0; background: Canvas; padding: 16px 0; border-bottom: 1px solid #8884; }}
h1 {{ font-size: 1.2rem; margin: 0 0 8px; }}
#filter {{ width: 100%; padding: 8px 10px; font-size: 1rem; border: 1px solid #8886; border-radius: 8px; }}
.day {{ font-size: 0.8rem; text-transform: uppercase; letter-spacing: .05em; opacity: .6;
        margin: 24px 0 8px; }}
.row {{ display: flex; gap: 12px; padding: 8px 0; text-decoration: none; color: inherit;
        align-items: flex-start; }}
.row:hover {{ background: #8881; border-radius: 8px; }}
.thumb {{ width: 168px; height: 94px; flex: none; object-fit: cover; border-radius: 8px; background: #8883; }}
.meta h2 {{ font-size: 1rem; margin: 0 0 4px; }}
.sub {{ font-size: 0.85rem; opacity: .7; }}
.row.new .meta h2::after {{ content: " NEW"; color: #e11; font-size: .7rem; vertical-align: super; }}
.empty, footer {{ opacity: .6; font-size: .85rem; margin-top: 24px; }}
@media (max-width: 520px) {{ .thumb {{ width: 120px; height: 68px; }} }}
</style>
</head>
<body>
<header>
  <h1>Subscriptions &middot; last 14 days</h1>
  <input id="filter" type="search" placeholder="Filter by channel…" autocomplete="off">
</header>
<main id="feed">
{body}
</main>
<footer>Updated {updated} UTC{failed}</footer>
<script>
(function () {{
  var KEY = "yt-rss-last-visit";
  var last = parseInt(localStorage.getItem(KEY) || "0", 10);
  document.querySelectorAll(".row").forEach(function (row) {{
    if (parseInt(row.dataset.ts, 10) * 1000 > last) row.classList.add("new");
  }});
  localStorage.setItem(KEY, Date.now().toString());

  var input = document.getElementById("filter");
  input.addEventListener("input", function () {{
    var q = input.value.trim().toLowerCase();
    document.querySelectorAll(".row").forEach(function (row) {{
      row.style.display = !q || row.dataset.channel.indexOf(q) !== -1 ? "" : "none";
    }});
    document.querySelectorAll(".day").forEach(function (day) {{
      var n = day.nextElementSibling, any = false;
      while (n && !n.classList.contains("day")) {{
        if (n.classList.contains("row") && n.style.display !== "none") any = true;
        n = n.nextElementSibling;
      }}
      day.style.display = any ? "" : "none";
    }});
  }});
}})();
</script>
</body>
</html>
"""


def render_html(videos: list[Video], *, now: datetime, failed_count: int) -> str:
    parts: list[str] = []
    groups = group_by_day(videos, now)
    if not groups:
        parts.append('<p class="empty">No recent uploads in the last 14 days.</p>')
    for label, items in groups:
        parts.append(f'<div class="day">{_html.escape(label)}</div>')
        for v in items:
            parts.append(
                f'<a class="row" href="{_html.escape(v.url)}" target="_blank" rel="noopener" '
                f'data-channel="{_html.escape(v.channel_title.lower())}" '
                f'data-ts="{int(v.published.timestamp())}">'
                f'<img class="thumb" loading="lazy" src="{_html.escape(v.thumbnail)}" alt="">'
                f'<div class="meta"><h2>{_html.escape(v.title)}</h2>'
                f'<div class="sub">{_html.escape(v.channel_title)} &middot; '
                f'{relative_time(v.published, now)}</div></div></a>'
            )
    failed = f" &middot; {failed_count} channels failed to fetch" if failed_count else ""
    return _PAGE.format(
        body="\n".join(parts),
        updated=now.strftime("%Y-%m-%d %H:%M"),
        failed=failed,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_render.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_render.py ytrss/render.py
git commit -m "feat: render self-contained dashboard HTML"
```

---

## Task 8: Parallel fetcher

**Files:**
- Create: `tests/test_fetch.py`, `ytrss/fetch.py`

- [ ] **Step 1: Write the failing test `tests/test_fetch.py`**

```python
from ytrss.models import Channel
from ytrss.fetch import fetch_all
from pathlib import Path

SAMPLE = (Path(__file__).parent / "fixtures" / "sample_feed.xml").read_text()


def _channels(n):
    return [Channel(channel_id=f"c{i}", title=f"t{i}", url="u") for i in range(n)]


def test_fetch_all_collects_videos_and_skips_failures():
    def fake_fetcher(channel_id):
        if channel_id == "c1":
            raise TimeoutError("boom")
        return SAMPLE

    videos, failed = fetch_all(_channels(3), fetcher=fake_fetcher, concurrency=3)
    assert len(failed) == 1
    assert failed == ["t1"]
    assert len(videos) > 0  # two channels' worth of entries parsed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_fetch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ytrss.fetch'`

- [ ] **Step 3: Write `ytrss/fetch.py`**

```python
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Callable
from ytrss.models import Channel, Video
from ytrss.feed import feed_url, parse_feed

USER_AGENT = "yt-rss-dashboard/1.0 (+https://github.com)"


def fetch_feed(channel_id: str, *, timeout: float = 15.0, retries: int = 1) -> str:
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
                time.sleep(1.0 * (attempt + 1))
    raise last_err


def fetch_all(
    channels: list[Channel],
    *,
    fetcher: Callable[[str], str] = fetch_feed,
    concurrency: int = 12,
) -> tuple[list[Video], list[str]]:
    videos: list[Video] = []
    failed: list[str] = []

    def work(channel: Channel):
        return channel, fetcher(channel.channel_id)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for channel, result in _imap(pool, work, channels):
            if result is None:
                failed.append(channel.title)
            else:
                try:
                    videos.extend(parse_feed(result))
                except Exception:  # noqa: BLE001 - malformed feed = skip channel
                    failed.append(channel.title)
    return videos, failed


def _imap(pool, work, channels):
    futures = {pool.submit(work, c): c for c in channels}
    from concurrent.futures import as_completed

    for future in as_completed(futures):
        channel = futures[future]
        try:
            _, result = future.result()
            yield channel, result
        except Exception:  # noqa: BLE001 - fetch failed
            yield channel, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_fetch.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add tests/test_fetch.py ytrss/fetch.py
git commit -m "feat: parallel feed fetch with graceful per-channel skips"
```

---

## Task 9: CLI entry point

**Files:**
- Create: `build.py`

- [ ] **Step 1: Write `build.py`**

```python
import argparse
from datetime import datetime, timezone
from pathlib import Path
from ytrss.opml import parse_opml
from ytrss.fetch import fetch_all
from ytrss.recent import filter_recent
from ytrss.render import render_html

WINDOW_DAYS = 14
CONCURRENCY = 12


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the subscriptions dashboard.")
    parser.add_argument("--opml", default="subscriptions.opml")
    parser.add_argument("--output", default="dist/index.html")
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    channels = parse_opml(Path(args.opml).read_text())
    print(f"Fetching {len(channels)} channels...")
    videos, failed = fetch_all(channels, concurrency=args.concurrency)
    recent = filter_recent(videos, now=now, window_days=args.window_days)
    print(f"{len(recent)} videos in last {args.window_days} days; {len(failed)} channels failed.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(recent, now=now, failed_count=len(failed)))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test with a 2-channel OPML (live network)**

Run: `python3 build.py --opml tests/fixtures/sample.opml --output dist/index.html`
Expected: prints `Fetching 2 channels...`, a video count, and `Wrote dist/index.html`. The file exists and opens in a browser showing rows.

- [ ] **Step 3: Commit**

```bash
git add build.py
git commit -m "feat: add build CLI entry point"
```

---

## Task 10: Full local run + GitHub Pages deploy

**Files:**
- Create: `.github/workflows/build.yml`, `README.md`

- [ ] **Step 1: Run the full build against all 939 channels (verify feasibility/timing)**

Run: `time python3 build.py`
Expected: completes (likely 1–4 min), prints video count and failed count, writes `dist/index.html`. Open it to confirm the timeline, day groups, and channel filter look right. If many channels fail, lower `--concurrency` (e.g. 8) and re-run — this validates the throttling risk noted in the spec.

- [ ] **Step 2: Write `.github/workflows/build.yml`**

```yaml
name: Build and deploy dashboard

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 */3 * * *"  # every 3 hours (UTC); GitHub may delay under load
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Build dashboard
        run: python3 build.py
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Write `README.md`**

```markdown
# yt-rss

A static dashboard of recent uploads from my YouTube subscriptions.

- Merged, newest-first timeline of the **last 14 days** across all subscribed channels.
- Grouped by day, filterable by channel, with "new since last visit" highlighting.
- Data comes from YouTube's public per-channel RSS feeds (no API key).

## Run locally

```bash
python3 build.py                 # builds dist/index.html for all channels
python3 build.py --output out.html --window-days 7
open dist/index.html
```

## How it deploys

A GitHub Action (`.github/workflows/build.yml`) runs every 3 hours, builds
`dist/index.html`, and deploys it to GitHub Pages. The published page is **public**.
```

- [ ] **Step 4: Run the full test suite**

Run: `python3 -m pytest -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/build.yml README.md
git commit -m "ci: build and deploy dashboard to GitHub Pages"
```

- [ ] **Step 6: Create the GitHub repo, push, and enable Pages (manual — needs the user's GitHub account)**

```bash
gh repo create yt-rss --public --source=. --remote=origin --push
```
Then in the repo: **Settings → Pages → Build and deployment → Source: "GitHub Actions"**.
Trigger the first run with **Actions → Build and deploy dashboard → Run workflow**
(or it runs on the next push/cron). The site URL appears in the deploy step output
and under Settings → Pages.

---

## Notes for the implementer

- **Python version:** `datetime.fromisoformat` must parse `+00:00` offsets — fine on 3.11/3.12. The Action pins 3.12.
- **No runtime dependencies:** keep `build.py` and `ytrss/` standard-library only so the Action needs no `pip install`. `pytest` is dev-only.
- **Throttling:** if the full run in Task 10 Step 1 shows a high failure count, reduce concurrency before relying on the cron. This is the one feasibility risk called out in the spec.
- **Privacy reminder:** the Pages site is public; the subscription list is visible to anyone with the URL (an accepted decision).
