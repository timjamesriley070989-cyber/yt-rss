# YouTube Subscriptions Dashboard ("yt-rss") — Design

**Date:** 2026-06-30
**Status:** Approved design, pending spec review

## Purpose

A personal dashboard that answers one question: **what have my YouTube subscriptions
uploaded recently, and when?** The user follows 939 channels and wants a single
newest-first timeline of recent uploads, viewable from a phone anywhere. Subscriber
counts, view counts, and other analytics are explicitly out of scope.

## Core decisions (settled during brainstorming)

| Decision | Choice |
|---|---|
| Organizing principle | Merged newest-first timeline + channel filter |
| Feed scope | Rolling window: videos uploaded in the **last 14 days** (constant, easy to change) |
| Shorts | Mixed in (RSS does not label Shorts; filtering would cost an extra request per video) |
| Hosting | Public GitHub Pages |
| Refresh | GitHub Action, cron every 3 hours + on push |
| Privacy | Public is acceptable (subscription list will be visible to anyone with the URL) |
| Phasing | Build publishing pipeline (C) first; local on-demand static file (A) comes nearly free from the same generator |

## Data source

Per-channel YouTube RSS feed:
`https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>`

- No API key, no quota.
- Returns the latest ~15 videos per channel as Atom XML.
- Each `<entry>` provides: `yt:videoId`, `title`, `published` (ISO 8601),
  `media:thumbnail` URL, and channel title.
- Channel list is parsed from `subscriptions.opml` (939 `<outline>` elements with
  `Channel Url` / `Channel Title` attributes; the channel ID is the `text` attribute,
  e.g. `UC-9uQ57m8AVd2Q1MCaZgutA`).

## Architecture

A single Python 3 script (`build.py`) with minimal or no external dependencies
(stdlib `urllib`, `xml.etree.ElementTree`, `concurrent.futures`; a small templating
helper is acceptable but not required). The script is the only moving part; GitHub
Actions just runs it and deploys the output.

### Components / data flow

1. **OPML parser** — read `subscriptions.opml` → list of
   `{channel_id, title, url}`. One clear function, testable in isolation.
2. **Feed fetcher** — given a channel ID, GET the RSS feed and return parsed entries.
   - Parallel fetch across all channels with a thread pool, concurrency ≈ 12.
   - Per-request timeout + a single retry with backoff.
   - **A failed channel is logged and skipped — it never fails the whole build.**
   - Returns a flat list of video entries plus a list of failed channel titles.
3. **Filter** — keep only entries with `published` within the last
   `WINDOW_DAYS = 14`.
4. **Builder** — sort entries newest-first, group by calendar day, render a single
   self-contained `dist/index.html`:
   - Inline CSS and JS (no external assets except thumbnail images).
   - Thumbnails loaded directly from YouTube's CDN (`i.ytimg.com`).
   - Each row links to `https://www.youtube.com/watch?v=<id>` (opens in new tab).
5. **Output** — `dist/index.html`. An `--output <path>` flag lets the same script
   write the file anywhere (supports the later local "mode A").

### The page (client-side behavior)

- **Day headers:** Today / Yesterday / explicit dates.
- **Row:** thumbnail + title + channel name + relative upload time ("2h ago").
- **Channel filter:** a client-side search/select to narrow the timeline to a single
  channel. All filtering happens in the browser over the already-rendered data.
- **"New since last visit":** on load, compare each video's publish time against a
  `lastVisit` timestamp stored in `localStorage`; visually highlight newer items, then
  update `lastVisit`. Per-device, no server state — works on the phone.
- **Footer:** last-refresh timestamp (UTC) and a note like "N channels failed to
  fetch this run" when applicable.

### Publishing

- A GitHub repository with GitHub Pages enabled (public).
- A GitHub Actions workflow:
  - Triggers: `schedule` (cron every 3 hours) and `push` to the default branch.
  - Steps: checkout → set up Python → run `build.py` → deploy `dist/` to Pages.
- Note: GitHub's scheduled crons can be delayed under load; acceptable here.

### Local mode (phase 2, "A")

Run `python build.py --output ./index.html` on the Mac to produce a fresh
self-contained file and open it directly. No additional code beyond the output flag.

## Error handling

- **Per-channel fetch failure** (timeout, 404 for deleted channels, malformed XML):
  log, skip, count it, continue. The build always produces a page.
- **Total fetch failure / empty result:** still emit a valid page stating no recent
  uploads were found, so Pages never serves a broken site.
- **Throttling risk (flagged):** GitHub's shared IPs fetching ~939 feeds could
  occasionally be throttled by YouTube. Mitigations: low concurrency, retry/backoff,
  read-only public RSS. Fallback if it becomes chronic: run the fetch from the Mac
  (mode A) and push the generated HTML.

## Testing

- **OPML parser:** parse a small fixture, assert channel count and field extraction.
- **Feed parser:** parse a saved sample feed (we already captured one), assert entry
  fields (id, title, published, thumbnail).
- **Filter:** entries straddling the 14-day boundary are correctly included/excluded
  (use fixed "now" for determinism).
- **Builder:** given known entries, the rendered HTML contains the expected day groups,
  titles, and watch links; verify it is self-contained (no missing local assets).
- Network fetching itself is integration-tested against one live channel, kept separate
  from the deterministic unit tests.

## Out of scope (YAGNI)

- Subscriber/view/engagement analytics.
- Authentication / private hosting (chosen public).
- Server-side read tracking, mark-as-watched, or cross-device sync.
- Reliable Shorts detection/filtering.
- In-page video playback (links out to YouTube instead).
