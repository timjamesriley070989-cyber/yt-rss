# Throttling-Resilience Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the dashboard resilient to fetch throttling by falling back on each channel's last-good cached feed data, so a partially-failed run still renders a near-complete page.

**Architecture:** A new `ytrss/cache.py` (de)serializes `Video`s to a JSON file (`.cache/feeds.json`) and provides a pure `merge_feeds` that combines fresh fetches with cached entries (fresh wins; failed channels fall back to cache). `fetch_all` changes to report per-channel success. `build.py` wires load → fetch → merge → save → existing 24h/Shorts/render pipeline. The GitHub Actions workflow persists `.cache/` via `actions/cache` with a rolling key.

**Tech Stack:** Python 3 standard library only (`json`, `datetime`, `pathlib`), `pytest`, GitHub Actions `actions/cache@v4`.

---

## File Structure

| File | Responsibility |
|---|---|
| `ytrss/cache.py` | Video⇄dict serialization, `load_cache`/`save_cache`, pure `merge_feeds` |
| `ytrss/fetch.py` | `fetch_all` — CHANGED return shape: `(fetched: dict[channel_id, list[Video]], failed: list[Channel])` |
| `build.py` | Orchestration: load cache → fetch → merge → save cache → filter/shorts/render |
| `.gitignore` | Add `.cache/` |
| `.github/workflows/build.yml` | Add `actions/cache` restore/save around the build step |
| `tests/test_cache.py` | Round-trip, corrupt-file tolerance, bad-record skip, `merge_feeds` behavior |
| `tests/test_fetch.py` | UPDATED for the new `fetch_all` return shape |

---

## Task 1: Cache serialization + load/save

**Files:**
- Create: `ytrss/cache.py`, `tests/test_cache.py`

- [ ] **Step 1: Write the failing test `tests/test_cache.py`**

```python
from datetime import datetime, timezone
from pathlib import Path
from ytrss.models import Video
from ytrss.cache import load_cache, save_cache

NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def _v(vid, cid_title="Chan"):
    return Video(video_id=vid, title="t", channel_title=cid_title,
                 published=NOW, thumbnail="https://i.ytimg.com/x.jpg")


def test_round_trip_preserves_videos(tmp_path):
    path = tmp_path / "feeds.json"
    data = {"c1": [_v("a"), _v("b")], "c2": [_v("c")]}
    save_cache(str(path), data)
    loaded = load_cache(str(path))
    assert set(loaded.keys()) == {"c1", "c2"}
    assert [v.video_id for v in loaded["c1"]] == ["a", "b"]
    assert loaded["c1"][0].published == NOW  # tz-aware datetime intact
    assert loaded["c1"][0].published.tzinfo is not None


def test_missing_file_returns_empty(tmp_path):
    assert load_cache(str(tmp_path / "nope.json")) == {}


def test_corrupt_file_returns_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    assert load_cache(str(path)) == {}


def test_bad_record_is_skipped(tmp_path):
    path = tmp_path / "feeds.json"
    path.write_text('{"feeds": {"c1": [{"video_id": "a"}, {"bogus": 1}]}}')
    loaded = load_cache(str(path))
    # the malformed record is skipped, the channel key still present
    assert "c1" in loaded
    assert all(hasattr(v, "video_id") for v in loaded["c1"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cache.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ytrss.cache'`

- [ ] **Step 3: Write `ytrss/cache.py`**

```python
import json
import sys
from datetime import datetime
from pathlib import Path
from ytrss.models import Video


def video_to_dict(v: Video) -> dict:
    return {
        "video_id": v.video_id,
        "title": v.title,
        "channel_title": v.channel_title,
        "published": v.published.isoformat(),
        "thumbnail": v.thumbnail,
    }


def video_from_dict(d: dict) -> Video:
    return Video(
        video_id=d["video_id"],
        title=d["title"],
        channel_title=d["channel_title"],
        published=datetime.fromisoformat(d["published"]),
        thumbnail=d["thumbnail"],
    )


def load_cache(path: str) -> dict[str, list[Video]]:
    """Read the feeds cache. Missing/corrupt file -> {}. Bad records are skipped."""
    try:
        raw = json.loads(Path(path).read_text())
        feeds = raw.get("feeds", {})
    except (OSError, ValueError, AttributeError):
        return {}
    result: dict[str, list[Video]] = {}
    for channel_id, records in feeds.items():
        videos: list[Video] = []
        for rec in records:
            try:
                videos.append(video_from_dict(rec))
            except (KeyError, ValueError, TypeError):
                continue
        result[channel_id] = videos
    return result


def save_cache(path: str, feeds_by_channel: dict[str, list[Video]]) -> None:
    """Write the feeds cache. A save failure is logged, never raised."""
    try:
        data = {"feeds": {
            channel_id: [video_to_dict(v) for v in videos]
            for channel_id, videos in feeds_by_channel.items()
        }}
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))
    except OSError as err:  # noqa: BLE001 - cache save must not fail the build
        print(f"warning: could not save cache to {path}: {err}", file=sys.stderr)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cache.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add ytrss/cache.py tests/test_cache.py
git commit -m "feat: feed cache serialization (load/save with tolerance)"
```

---

## Task 2: `merge_feeds` (pure merge logic)

**Files:**
- Modify: `ytrss/cache.py`, `tests/test_cache.py`

- [ ] **Step 1: Append the failing test to `tests/test_cache.py`**

```python
from ytrss.models import Channel
from ytrss.cache import merge_feeds


def _chan(cid):
    return Channel(channel_id=cid, title=cid, url="u")


def test_merge_fresh_wins_failed_falls_back_missing_counted():
    channels = [_chan("c1"), _chan("c2"), _chan("c3")]
    fetched = {"c1": [_v("fresh1")]}                 # c1 fetched OK
    cache = {"c2": [_v("cached2")]}                  # c2 failed but cached
    # c3 failed and has no cache -> missing
    new_cache, fell_back, missing = merge_feeds(channels, fetched, cache)
    assert [v.video_id for v in new_cache["c1"]] == ["fresh1"]
    assert [v.video_id for v in new_cache["c2"]] == ["cached2"]
    assert new_cache["c3"] == []
    assert fell_back == 1
    assert missing == 1


def test_merge_drops_channels_not_in_current_opml():
    channels = [_chan("c1")]
    fetched = {"c1": [_v("a")]}
    cache = {"old": [_v("z")]}       # "old" no longer subscribed
    new_cache, _, _ = merge_feeds(channels, fetched, cache)
    assert set(new_cache.keys()) == {"c1"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_cache.py -k merge -v`
Expected: FAIL with `ImportError: cannot import name 'merge_feeds'`

- [ ] **Step 3: Append `merge_feeds` to `ytrss/cache.py`**

```python
from ytrss.models import Channel


def merge_feeds(
    channels: list[Channel],
    fetched: dict[str, list[Video]],
    cache: dict[str, list[Video]],
) -> tuple[dict[str, list[Video]], int, int]:
    """Combine fresh fetches with cached data for the current channel set.

    Fresh entries win; a channel absent from `fetched` falls back to `cache`;
    a channel in neither yields []. Returns (new_cache, fell_back, missing) where
    new_cache is keyed only by current-OPML channel ids.
    """
    new_cache: dict[str, list[Video]] = {}
    fell_back = 0
    missing = 0
    for channel in channels:
        cid = channel.channel_id
        if cid in fetched:
            new_cache[cid] = fetched[cid]
        elif cache.get(cid):
            new_cache[cid] = cache[cid]
            fell_back += 1
        else:
            new_cache[cid] = []
            missing += 1
    return new_cache, fell_back, missing
```

Add the `from ytrss.models import Channel` import next to the existing
`from ytrss.models import Video` line (or combine into
`from ytrss.models import Channel, Video`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_cache.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add ytrss/cache.py tests/test_cache.py
git commit -m "feat: merge_feeds — fresh wins, failed channels fall back to cache"
```

---

## Task 3: `fetch_all` reports per-channel success

**Files:**
- Modify: `ytrss/fetch.py`, `tests/test_fetch.py`

- [ ] **Step 1: Replace the test in `tests/test_fetch.py`**

Replace the entire body of `test_fetch_all_collects_videos_and_skips_failures`
(keep the imports and `_channels` helper) with a renamed test:

```python
def test_fetch_all_returns_per_channel_success_and_failures():
    def fake_fetcher(channel_id):
        if channel_id == "c1":
            raise TimeoutError("boom")
        return SAMPLE

    fetched, failed = fetch_all(_channels(3), fetcher=fake_fetcher, concurrency=3)
    assert set(fetched.keys()) == {"c0", "c2"}
    assert all(len(v) > 0 for v in fetched.values())          # entries parsed
    assert [c.channel_id for c in failed] == ["c1"]           # Channel objects
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_fetch.py -v`
Expected: FAIL — `fetch_all` still returns `(list, list_of_titles)`, so
`fetched.keys()` raises `AttributeError` (list has no `.keys`).

- [ ] **Step 3: Update `fetch_all` in `ytrss/fetch.py`**

Replace the existing `fetch_all` function (leave `fetch_feed` and `_imap` unchanged)
with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_fetch.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add ytrss/fetch.py tests/test_fetch.py
git commit -m "refactor: fetch_all reports per-channel success for cache fallback"
```

---

## Task 4: Wire caching into `build.py` + gitignore

**Files:**
- Modify: `build.py`, `.gitignore`

- [ ] **Step 1: Add `.cache/` to `.gitignore`**

Append a line `.cache/` to `.gitignore` (the file already contains `dist/`,
`.superpowers/`, etc.).

- [ ] **Step 2: Replace `build.py` with the cache-aware pipeline**

```python
import argparse
from datetime import datetime, timezone
from pathlib import Path
from ytrss.opml import parse_opml
from ytrss.fetch import fetch_all
from ytrss.cache import load_cache, save_cache, merge_feeds
from ytrss.recent import filter_recent
from ytrss.shorts import filter_out_shorts
from ytrss.render import render_html

WINDOW_HOURS = 24
CONCURRENCY = 12
SHORTS_CONCURRENCY = 24
CACHE_PATH = ".cache/feeds.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the subscriptions dashboard.")
    parser.add_argument("--opml", default="subscriptions.opml")
    parser.add_argument("--output", default="dist/index.html")
    parser.add_argument("--cache", default=CACHE_PATH)
    parser.add_argument("--window-hours", type=int, default=WINDOW_HOURS)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    parser.add_argument("--shorts-concurrency", type=int, default=SHORTS_CONCURRENCY)
    parser.add_argument("--keep-shorts", action="store_true",
                        help="skip Shorts filtering (keep Shorts in the feed)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    channels = parse_opml(Path(args.opml).read_text())
    cache = load_cache(args.cache)

    print(f"Fetching {len(channels)} channels...")
    fetched, failed = fetch_all(channels, concurrency=args.concurrency)

    new_cache, fell_back, missing = merge_feeds(channels, fetched, cache)
    save_cache(args.cache, new_cache)
    videos = [v for entries in new_cache.values() for v in entries]

    recent = filter_recent(videos, now=now, window_hours=args.window_hours)
    kept = recent if args.keep_shorts else filter_out_shorts(
        recent, concurrency=args.shorts_concurrency)

    print(f"{len(fetched)} fetched OK, {len(failed)} failed "
          f"({fell_back} recovered from cache, {missing} missing); "
          f"{len(recent)} in last {args.window_hours}h, "
          f"{len(recent) - len(kept)} Shorts removed; {len(kept)} rendered.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(kept, now=now, failed_count=missing))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the whole suite still passes**

Run: `python3 -m pytest -q`
Expected: PASS (all tests — 6 in test_cache, 1 in test_fetch, plus the existing
opml/feed/recent/render/shorts tests).

- [ ] **Step 4: Smoke-test the merge/fallback locally (no live network needed)**

Run:
```bash
python3 - <<'PY'
from datetime import datetime, timezone
from ytrss.models import Video, Channel
from ytrss.cache import save_cache, load_cache, merge_feeds
now = datetime.now(timezone.utc)
chans = [Channel("c1","c1","u"), Channel("c2","c2","u")]
save_cache(".cache/test.json", {"c2": [Video("z","cached","c2",now,"")]})
cache = load_cache(".cache/test.json")
new_cache, fb, miss = merge_feeds(chans, {"c1":[Video("a","fresh","c1",now,"")]}, cache)
print("c1", [v.title for v in new_cache["c1"]], "| c2", [v.title for v in new_cache["c2"]],
      "| fell_back", fb, "| missing", miss)
PY
rm -f .cache/test.json
```
Expected: `c1 ['fresh'] | c2 ['cached'] | fell_back 1 | missing 0`

- [ ] **Step 5: Commit**

```bash
git add build.py .gitignore
git commit -m "feat: cache-aware build — fall back to last-good feeds on failure"
```

---

## Task 5: Persist the cache in CI + full verification

**Files:**
- Modify: `.github/workflows/build.yml`

- [ ] **Step 1: Add cache restore/save around the build step**

In `.github/workflows/build.yml`, edit the `build-deploy` job's `steps` so the build
is wrapped by cache restore (before) and save (after). The steps become exactly:

```yaml
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Restore feed cache
        uses: actions/cache/restore@v4
        with:
          path: .cache
          key: feeds-cache-${{ github.run_id }}
          restore-keys: feeds-cache-
      - name: Build dashboard
        run: python3 build.py
      - name: Save feed cache
        if: always()
        uses: actions/cache/save@v4
        with:
          path: .cache
          key: feeds-cache-${{ github.run_id }}
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
      - id: deployment
        uses: actions/deploy-pages@v4
```

Leave the `name`, `on`, `permissions`, `concurrency`, and `jobs.build-deploy.runs-on`
sections unchanged.

- [ ] **Step 2: Full local build — confirm it still produces a valid page**

Run (macOS needs the cert env — see project memory / README):
```bash
export SSL_CERT_FILE=/tmp/ytrss-cacerts.pem
[ -f "$SSL_CERT_FILE" ] || security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > "$SSL_CERT_FILE"
python3 build.py
```
Expected: prints the new counts line (`N fetched OK, M failed (…recovered…, …missing); … rendered.`), writes `dist/index.html`, and `.cache/feeds.json` now exists (`ls -la .cache/feeds.json`). Run it a SECOND time and confirm it still works reading the now-populated cache.

- [ ] **Step 3: Confirm cache fallback actually fills gaps (offline simulation)**

Run:
```bash
# Build once to populate the cache, then build again forcing all fetches to fail
export SSL_CERT_FILE=/tmp/ytrss-cacerts.pem
python3 build.py >/dev/null
python3 - <<'PY'
# simulate a fully-throttled run: every fetch raises -> all channels fall back to cache
from datetime import datetime, timezone
from pathlib import Path
from ytrss.opml import parse_opml
from ytrss.fetch import fetch_all
from ytrss.cache import load_cache, merge_feeds
from ytrss.recent import filter_recent
def boom(cid): raise TimeoutError()
channels = parse_opml(Path("subscriptions.opml").read_text())
cache = load_cache(".cache/feeds.json")
fetched, failed = fetch_all(channels, fetcher=boom, concurrency=8)
new_cache, fb, miss = merge_feeds(channels, fetched, cache)
vids = [v for e in new_cache.values() for v in e]
recent = filter_recent(vids, now=datetime.now(timezone.utc), window_hours=24)
print(f"all fetches failed: {len(failed)} failed, {fb} recovered from cache, "
      f"{miss} missing, {len(recent)} videos still in window")
PY
```
Expected: `failed` ≈ 939, `fb` is large (most channels recovered from cache), and
`videos still in window` is substantial (NOT near zero) — proving the fallback works.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: persist feed cache between runs via actions/cache"
```

- [ ] **Step 5: Deploy (single push)**

```bash
git push origin main
```
This triggers one deploy that seeds the CI cache; subsequent scheduled runs benefit.
Note: if the IP is still cooling from prior throttling, this run may be partial — but
it will populate the cache so the *next* run recovers. Watch:
`gh run watch $(gh run list -R timjamesriley070989-cyber/yt-rss --limit 1 --json databaseId --jq '.[0].databaseId') -R timjamesriley070989-cyber/yt-rss --exit-status`

---

## Notes for the implementer

- **Only caller of `fetch_all` is `build.py`** — the signature change is safe; update
  both together (Tasks 3 and 4). No other module imports `fetch_all`.
- **`merge_feeds` uses `cache.get(cid)` truthiness** — an empty cached list counts as
  "missing", which is correct (nothing to show).
- **Footer semantics:** `render_html(failed_count=missing)` — only channels that failed
  AND had no cache are reported, per the spec.
- **Do not commit `.cache/`** — it's gitignored; CI persists it via `actions/cache`.
- **macOS SSL:** local live builds need `SSL_CERT_FILE` (see README / project memory).
