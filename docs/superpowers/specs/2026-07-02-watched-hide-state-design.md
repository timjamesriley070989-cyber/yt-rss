# Watched / Hide State — Design

**Date:** 2026-07-02
**Status:** Approved design, pending spec review

## Purpose

Turn the dashboard from a passive feed into an "inbox you clear": videos you've
opened or dismissed disappear, so the grid shows only what you haven't dealt with.
Per-device, no server state — consistent with the existing "new since last visit"
highlight.

## Decisions (from brainstorming)

- **Marking watched:** both triggers — clicking a card to open it on YouTube marks it
  watched, AND an explicit dismiss control marks it watched without opening.
- **Recovery:** a "Show watched" toggle reveals hidden videos (dimmed) with an unhide
  control (chosen over hide-forever).

## Storage

- `localStorage` key `yt-rss-watched` = JSON array of watched `video_id` strings.
- On load, **prune to only ids present on the current page**, then persist the pruned
  set. Keeps storage bounded (videos age out of the 24h window; their ids stop
  appearing and get pruned).
- Independent of the existing `yt-rss-last-visit` key ("new" highlight), which is
  unchanged.

## Interactions

- **Click card → watched.** The card is an `<a target="_blank">`; a click handler adds
  its `video_id` to the watched set and hides the card. Navigation to YouTube still
  proceeds (new tab).
- **Dismiss control.** A small "✕" button at the top-right of each thumbnail, **always
  visible** (tappable on mobile). Its handler calls `preventDefault()` +
  `stopPropagation()` so it does NOT open YouTube, then marks watched and hides.
- **Show-watched toggle.** A header control (default OFF). OFF: only unwatched cards
  show. ON: watched cards also show, visually dimmed, each exposing an **"↩ unhide"**
  control that removes the id from the watched set and un-dims it.
- **Live count.** The header count element shows the current **unwatched** count and
  updates immediately on watch / dismiss / unhide.
- **All-caught-up.** When zero cards are visible in the default (unwatched-only) view
  because everything is watched, show a "You're all caught up" message. (Distinct from
  the server-rendered "No uploads in the last 24 hours" empty state, which appears when
  there were no videos at all.)
- **Combine with channel filter.** A single `applyVisibility()` function decides each
  card's visibility from: matches the channel-filter query AND (not watched OR
  show-watched is ON). Both the filter input and the toggle call it.

## Code changes (all in `ytrss/render.py`)

- **Card markup:** add `data-vid="<video_id>"`; add a `<button class="dismiss">` inside
  the card. (The existing `data-channel` and `data-ts` attributes stay.)
- **Header:** add the show-watched toggle control and give the count element a stable id
  so JS can update it live; add a hidden "all caught up" element.
- **CSS:** dismiss button (small, top-right of `.thumb-wrap`, always visible, subtle);
  `.card.watched` dimmed style; unhide control; all-caught-up message.
- **JS:** load + prune + save the watched set; `applyVisibility()` combining filter +
  watched + toggle; click-to-watch handler; dismiss handler (prevent navigation);
  unhide handler; show-watched toggle handler; live unwatched-count update. The existing
  "new since last visit" logic is preserved.

## Testing

- **Python (render hooks):** assert `render_html` output contains, per card, a
  `data-vid="..."` attribute and a dismiss button; and contains the show-watched toggle
  element and the count element with its stable id. These guarantee the JS has the DOM
  hooks it needs.
- **JS behavior:** this project has no JS test harness, so the interactive behavior
  (click-to-watch, dismiss, unhide, toggle, live count, prune) is **verified manually**
  in the browser as part of implementation — explicitly called out, not claimed as
  automated coverage.

## Out of scope (YAGNI)

- Cross-device sync (localStorage is per-device, matching the "new" highlight).
- "Mark all as watched" bulk action.
- Watch history / analytics / counts beyond the live unwatched number.
- Server-side persistence of watched state.
