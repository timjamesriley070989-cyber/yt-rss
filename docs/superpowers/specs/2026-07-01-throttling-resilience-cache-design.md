# Resilience to Throttling — Per-Channel Last-Good Cache — Design

**Date:** 2026-07-01
**Status:** Approved design, pending spec review

## Problem

Each build fetches all 939 channel RSS feeds. When YouTube rate-limits the runner
(observed after rapid repeated builds: 700+/939 channels failing in one run), the
failed channels contribute no videos and the page collapses to a handful of items.
The graceful per-channel skip keeps the build from crashing, but the result is a
near-empty dashboard.

## Goal

A throttled or partially-failing run should still render a near-complete page by
falling back on each failed channel's most recent successful data, and self-heal
channel-by-channel as fetches recover.

## Approach (decided during brainstorming)

Per-channel last-good cache (chosen over a whole-page fallback), persisted between
runs via GitHub Actions cache (chosen over committing a cache file to the repo).

Shorts-status caching was considered and **explicitly cut** from this pass — Shorts
filtering continues to re-probe every recent video each run, unchanged.

## Cache contents & format

A single JSON file (default path `.cache/feeds.json`):

```json
{ "feeds": { "<channel_id>": [ {"video_id": "...", "title": "...",
  "channel_title": "...", "published": "<ISO 8601>", "thumbnail": "..."}, ... ] } }
```

- `feeds` maps a channel_id to that channel's most recent **successful** fetch
  (the parsed entries, ~15 per channel; `published` serialized as ISO 8601).
- Overwrite-per-channel on success, so the file stays naturally bounded
  (~1–2 MB for 939 channels).
- On save, keep only channels present in the current OPML (drop removed channels).
- A missing or corrupt cache file is treated as an empty cache — never a crash.

## Merge logic (core behavior)

On each build, for every channel in the OPML:

- **Fetch succeeded** → use the fresh entries AND refresh that channel's cache slot.
- **Fetch failed** → use the channel's cached entries (empty list if none cached yet).

The combined video list then flows through the **existing** pipeline unchanged:
`filter_recent` (24h window) → `filter_out_shorts` → `render_html`. Because the
window is 24 hours, cached videos older than 24h fall off automatically, so stale
data cannot accumulate. First run (empty cache) behaves exactly as today.

## Code shape

- **New `ytrss/cache.py`**
  - `video_to_dict(video) -> dict` / `video_from_dict(d) -> Video` — (de)serialize a
    `Video`, converting `published` to/from ISO 8601 (tz-aware).
  - `load_cache(path) -> dict[str, list[Video]]` — read `feeds`; missing/corrupt → `{}`.
  - `save_cache(path, feeds_by_channel) -> None` — write JSON, creating parent dir.
- **`ytrss/fetch.py`** — `fetch_all` returns per-channel success so callers know which
  channels to fall back for. New return shape:
  `(fetched: dict[str, list[Video]], failed: list[Channel])`, where `fetched` contains
  only channels whose fetch+parse succeeded (keyed by `channel_id`). This replaces the
  current `(videos, failed_titles)` shape; `build.py` is the only caller.
- **`build.py`** — orchestration:
  1. `cache = load_cache(args.cache)`
  2. `fetched, failed = fetch_all(channels, ...)`
  3. merge: for each channel, `entries = fetched.get(cid, cache.get(cid, []))`;
     build `new_cache[cid]` from `fetched` where present, else carry `cache[cid]`.
  4. `save_cache(args.cache, new_cache)` (only current OPML channels)
  5. flatten entries → `filter_recent` → `filter_out_shorts` → `render_html`
  6. print counts: fetched OK, fell back from cache, Shorts removed, total rendered.
  - New `--cache` flag (default `.cache/feeds.json`).

  **Footer count semantics:** `render_html`'s `failed_count` = channels that failed
  their live fetch AND had no cached entries to fall back on (i.e. genuinely
  contributed nothing). Channels that failed but were served from cache are NOT
  counted as failed — otherwise a full-looking page would nonsensically report
  hundreds of failures. Console output still logs the raw live-fetch failure count
  and the fall-back count separately for debugging.

## Workflow changes

In `.github/workflows/build.yml`, around the build step:

- `actions/cache/restore` before the build: `path: .cache`, `key: feeds-cache-${{ github.run_id }}`,
  `restore-keys: feeds-cache-`.
- `actions/cache/save` after the build: same `path` and `key`.

(Split restore/save because the same run both reads the prior cache and writes a new
immutable entry; the rolling key + prefix restore-keys gives "most recent wins".)

## Error handling

- Missing/corrupt/unparseable cache file → empty cache, build proceeds normally.
- A cache entry that fails to deserialize (bad record) → skip that record, keep the rest.
- Cache save failure → log and continue (a failed save must not fail the build/deploy).

## Testing

- **Round-trip:** `save_cache` then `load_cache` reproduces videos with tz-aware
  `published` intact.
- **Merge:** a failed channel falls back to its cached entries; a successful channel
  overrides (and refreshes) its cache; a channel in neither yields nothing.
- **Corrupt file:** `load_cache` on garbage/missing path returns `{}` without raising.
- **Bounded save:** channels absent from the current OPML are dropped on save.
- Existing tests updated for the new `fetch_all` return shape (fake-fetcher injection
  already supports this).

## Out of scope (YAGNI)

- No "abort deploy if the run is too incomplete" guard — the per-channel cache keeps
  the page full, making a guard unnecessary.
- No Shorts-status caching (cut by decision).
- No conditional requests (ETag/If-Modified-Since) — a separate optimization if ever needed.
