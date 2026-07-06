# Watched / Hide State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user clear watched/dismissed videos from the grid (per-device via localStorage), with a "Show watched" toggle to reveal and unhide them.

**Architecture:** Entirely client-side, in the generated page produced by `ytrss/render.py`. Each card carries a `data-vid` and a dismiss button; inline JS keeps a watched-id set in `localStorage`, and a single `applyVisibility()` combines the channel filter with watched-state and the show-watched toggle. No changes to the data pipeline.

**Tech Stack:** Python 3 stdlib (`string.Template`, `html`), `pytest` (for DOM-hook assertions), vanilla browser JS + `localStorage`.

---

## File Structure

| File | Responsibility |
|---|---|
| `ytrss/render.py` | Card markup (valid `<div>`+`<a>`+buttons), header controls, CSS, and the watched-state JS |
| `tests/test_render.py` | Assert the DOM hooks the JS needs are present in rendered HTML |

**Note on card structure:** the card changes from a single `<a>` to a `<div class="card">` containing two `<a>` links (thumbnail + body) and the dismiss/unhide `<button>`s as siblings. This avoids nesting `<button>` inside `<a>` (invalid HTML the parser can restructure).

---

## Task 1: Watched-state UI (markup + CSS + JS)

**Files:**
- Modify: `ytrss/render.py`
- Modify: `tests/test_render.py`

- [ ] **Step 1: Add the failing hook test to `tests/test_render.py`**

Append this test (the file already imports `re`, `datetime`, `timedelta`, `timezone`,
`Video`, `render_html`, and defines `NOW`):

```python
def test_render_html_has_watched_state_hooks():
    video = Video(video_id="abc", title="T", channel_title="C",
                  published=NOW - timedelta(hours=1),
                  thumbnail="https://i3.ytimg.com/x.jpg")
    html = render_html([video], now=NOW, failed_count=0)
    assert 'data-vid="abc"' in html          # per-card id for watched tracking
    assert 'class="dismiss"' in html          # explicit dismiss control
    assert 'class="unhide"' in html           # unhide control (shown when watched)
    assert 'id="show-watched"' in html        # header toggle
    assert 'id="count"' in html               # live count element
    assert 'id="caught-up"' in html           # all-caught-up message
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_render.py::test_render_html_has_watched_state_hooks -v`
Expected: FAIL (`data-vid` etc. not in current output).

- [ ] **Step 3: Replace the entire contents of `ytrss/render.py`**

```python
import html as _html
from datetime import datetime
from string import Template
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


_PAGE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Subscriptions</title>
<style>
:root {
  --bg: #f6f7f9; --text: #10121a; --muted: #5b6472; --border: #e6e8ee;
  --chip: #eef0f4; --accent: #4c6ef5; --accent-contrast: #ffffff;
  --shadow: 0 1px 2px rgba(16,18,26,.06), 0 6px 16px rgba(16,18,26,.06);
  --shadow-hover: 0 6px 14px rgba(16,18,26,.10), 0 18px 40px rgba(16,18,26,.14);
  --skeleton: #e9ebf0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0d0f14; --text: #eef0f4; --muted: #9aa3b2; --border: #23262f;
    --chip: #1c1f27; --accent: #748ffc; --accent-contrast: #0d0f14;
    --shadow: none; --shadow-hover: 0 10px 30px rgba(0,0,0,.55);
    --skeleton: #1a1d24;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg); color: var(--text); margin: 0;
  padding: 0 20px 64px; max-width: 1280px; margin-inline: auto;
  -webkit-font-smoothing: antialiased;
}
header {
  position: sticky; top: 0; z-index: 5; background: var(--bg);
  padding: 18px 0 14px; border-bottom: 1px solid var(--border);
}
.titles { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -.02em; margin: 0; }
.count { font-size: .8rem; font-weight: 600; color: var(--muted);
  background: var(--chip); padding: 3px 10px; border-radius: 999px; }
.tagline { color: var(--muted); font-size: .85rem; margin: 2px 0 14px; }
.controls { display: flex; gap: 12px; align-items: center; }
.controls .search { position: relative; flex: 1; }
.search svg { position: absolute; left: 13px; top: 50%; transform: translateY(-50%);
  width: 17px; height: 17px; color: var(--muted); pointer-events: none; }
#filter {
  width: 100%; padding: 11px 14px 11px 40px; font-size: .95rem; color: var(--text);
  background: var(--chip); border: 1px solid transparent; border-radius: 12px; outline: none;
  transition: border-color .15s, background .15s;
}
#filter:focus { border-color: var(--accent); background: var(--bg); }
#filter::placeholder { color: var(--muted); }
.show-watched { display: flex; align-items: center; gap: 6px; white-space: nowrap;
  font-size: .82rem; color: var(--muted); cursor: pointer; user-select: none; }
.show-watched input { accent-color: var(--accent); }
#feed {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 28px 18px; margin-top: 24px;
}
.card { display: flex; flex-direction: column; }
.card a { text-decoration: none; color: inherit; }
.thumb-wrap {
  position: relative; border-radius: 14px; overflow: hidden; background: var(--skeleton);
  box-shadow: var(--shadow); transition: transform .18s ease, box-shadow .18s ease;
}
.card:hover .thumb-wrap { transform: translateY(-3px); box-shadow: var(--shadow-hover); }
.thumb-link { display: block; }
.thumb { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }
.dismiss, .unhide {
  position: absolute; top: 8px; right: 8px; width: 26px; height: 26px; padding: 0;
  border: none; border-radius: 50%; cursor: pointer; z-index: 2;
  background: rgba(0,0,0,.62); color: #fff; font-size: 14px; line-height: 1;
  display: flex; align-items: center; justify-content: center;
}
.dismiss:hover, .unhide:hover { background: rgba(0,0,0,.85); }
.unhide { display: none; }
.card.watched .dismiss { display: none; }
.card.watched .unhide { display: flex; }
.card.watched { opacity: .45; }
.card.new .thumb-wrap::after {
  content: "NEW"; position: absolute; top: 9px; left: 9px;
  background: var(--accent); color: var(--accent-contrast);
  font-size: .6rem; font-weight: 800; letter-spacing: .06em; padding: 3px 8px; border-radius: 7px;
}
.body { padding: 11px 2px 0; }
.card h2 {
  font-size: .93rem; font-weight: 600; line-height: 1.32; margin: 0 0 5px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card:hover h2 { color: var(--accent); }
.sub { font-size: .8rem; color: var(--muted); }
.empty {
  grid-column: 1 / -1; text-align: center; color: var(--muted);
  padding: 80px 20px; font-size: .95rem;
}
#caught-up { text-align: center; color: var(--muted); padding: 80px 20px; font-size: .95rem; }
footer { color: var(--muted); font-size: .78rem; text-align: center; margin-top: 44px; }
@media (max-width: 560px) {
  body { padding: 0 14px 48px; }
  #feed { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 20px 12px; }
  h1 { font-size: 1.2rem; }
}
</style>
</head>
<body>
<header>
  <div class="titles"><h1>Subscriptions</h1><span class="count" id="count">$count</span></div>
  <p class="tagline">New uploads from the last 24 hours &middot; Shorts hidden</p>
  <div class="controls">
    <div class="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
      <input id="filter" type="search" placeholder="Filter by channel…" autocomplete="off">
    </div>
    <label class="show-watched"><input type="checkbox" id="show-watched"> Show watched</label>
  </div>
</header>
<main id="feed">
$body
</main>
<p id="caught-up" hidden>You're all caught up &#127881;</p>
<footer>Updated $updated UTC$failed</footer>
<script>
(function () {
  var VKEY = "yt-rss-last-visit";
  var WKEY = "yt-rss-watched";
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var present = {};
  cards.forEach(function (c) { present[c.dataset.vid] = true; });

  // "new since last visit" highlight (unchanged behavior)
  var last = parseInt(localStorage.getItem(VKEY) || "0", 10);
  cards.forEach(function (c) {
    if (parseInt(c.dataset.ts, 10) * 1000 > last) c.classList.add("new");
  });
  localStorage.setItem(VKEY, Date.now().toString());

  // watched set, pruned to ids present on this page
  var watched = {};
  try {
    JSON.parse(localStorage.getItem(WKEY) || "[]").forEach(function (id) {
      if (present[id]) watched[id] = true;
    });
  } catch (e) {}
  function saveWatched() { localStorage.setItem(WKEY, JSON.stringify(Object.keys(watched))); }
  saveWatched();  // persist the pruned set

  var input = document.getElementById("filter");
  var toggle = document.getElementById("show-watched");
  var countEl = document.getElementById("count");
  var caughtUp = document.getElementById("caught-up");

  function applyVisibility() {
    var q = input.value.trim().toLowerCase();
    var showWatched = toggle.checked;
    var unwatched = 0, visible = 0;
    cards.forEach(function (c) {
      var w = !!watched[c.dataset.vid];
      c.classList.toggle("watched", w);
      if (!w) unwatched++;
      var matches = !q || c.dataset.channel.indexOf(q) !== -1;
      var show = matches && (!w || showWatched);
      c.style.display = show ? "" : "none";
      if (show) visible++;
    });
    countEl.textContent = unwatched + " unwatched";
    caughtUp.hidden = !(cards.length > 0 && visible === 0 && !q && !showWatched);
  }

  function setWatched(id, val) {
    if (val) { watched[id] = true; } else { delete watched[id]; }
    saveWatched();
    applyVisibility();
  }

  cards.forEach(function (c) {
    var id = c.dataset.vid;
    c.querySelectorAll("a[href]").forEach(function (a) {
      a.addEventListener("click", function () { setWatched(id, true); });
    });
    var d = c.querySelector(".dismiss");
    if (d) d.addEventListener("click", function (e) {
      e.preventDefault(); e.stopPropagation(); setWatched(id, true);
    });
    var u = c.querySelector(".unhide");
    if (u) u.addEventListener("click", function (e) {
      e.preventDefault(); e.stopPropagation(); setWatched(id, false);
    });
  });

  input.addEventListener("input", applyVisibility);
  toggle.addEventListener("change", applyVisibility);
  applyVisibility();
})();
</script>
</body>
</html>
""")


def render_html(videos: list[Video], *, now: datetime, failed_count: int) -> str:
    if not videos:
        body = '<p class="empty">No uploads in the last 24 hours.</p>'
    else:
        cards: list[str] = []
        for v in videos:
            url = _html.escape(v.url)
            cards.append(
                f'<div class="card" data-vid="{_html.escape(v.video_id)}" '
                f'data-channel="{_html.escape(v.channel_title.lower())}" '
                f'data-ts="{int(v.published.timestamp())}">'
                f'<div class="thumb-wrap">'
                f'<a class="thumb-link" href="{url}" target="_blank" rel="noopener">'
                f'<img class="thumb" loading="lazy" src="{_html.escape(v.thumbnail)}" alt=""></a>'
                f'<button class="dismiss" type="button" aria-label="Mark watched">&times;</button>'
                f'<button class="unhide" type="button" aria-label="Unhide">&#8617;</button>'
                f'</div>'
                f'<a class="body" href="{url}" target="_blank" rel="noopener">'
                f'<h2>{_html.escape(v.title)}</h2>'
                f'<div class="sub">{_html.escape(v.channel_title)} &middot; '
                f'{relative_time(v.published, now)}</div></a></div>'
            )
        body = "\n".join(cards)
    failed = f" &middot; {failed_count} channels failed to fetch" if failed_count else ""
    return _PAGE.substitute(
        body=body,
        count=f"{len(videos)} videos",
        updated=now.strftime("%Y-%m-%d %H:%M"),
        failed=failed,
    )
```

- [ ] **Step 4: Run the render tests + full suite**

Run: `python3 -m pytest tests/test_render.py -v && python3 -m pytest -q`
Expected: the new hook test passes; the existing render tests still pass
(`test_relative_time`, `test_render_html_renders_cards_and_is_self_contained`,
`test_render_html_reports_failures_and_empty_state`); full suite green (23 tests).

Note: `test_render_html_renders_cards_and_is_self_contained` asserts `class="card"`,
`grid-template-columns`, the video title/channel/watch URL, no external stylesheet,
and that the only remote `src` is on a `ytimg.com` host — all still true with the new
markup (the buttons and links carry no `src`; the SVG uses `stroke`, not a URL).

- [ ] **Step 5: Commit**

```bash
git add ytrss/render.py tests/test_render.py
git commit -m "feat: watched/hide state — click or dismiss to clear, toggle to unhide"
```

---

## Task 2: Manual browser verification + deploy

**Files:** none (verification + deploy). No code changes unless a bug is found; if so,
fix in `ytrss/render.py`, re-run `python3 -m pytest -q`, and amend/commit before deploying.

- [ ] **Step 1: Build a preview page with real cards**

Run:
```bash
export SSL_CERT_FILE=/tmp/ytrss-cacerts.pem
[ -f "$SSL_CERT_FILE" ] || security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain > "$SSL_CERT_FILE"
python3 build.py --opml tests/fixtures/sample.opml --window-hours 100000 --keep-shorts --output dist/preview.html
grep -c 'class="card"' dist/preview.html   # expect >= 1
open dist/preview.html
```

- [ ] **Step 2: Verify each behavior in the browser (record pass/fail for each)**

1. **Dismiss:** click a card's ✕ — the card disappears and does NOT open YouTube; the
   header count decreases by one.
2. **Click-to-watch:** click a card's thumbnail/title — YouTube opens in a new tab AND
   the card leaves the grid (count decreases).
3. **Show watched:** tick "Show watched" — dismissed/watched cards reappear dimmed, each
   with the ↩ control; count still reflects unwatched.
4. **Unhide:** with the toggle on, click ↩ on a watched card — it un-dims; untick the
   toggle and confirm it stays in the grid.
5. **Persistence:** dismiss a card, reload the page — it stays hidden (localStorage).
6. **Channel filter still works** and combines with watched (type a channel name; only
   matching, unwatched cards show unless "Show watched" is on).
7. **All caught up:** dismiss every visible card (toggle off, no filter) — the "You're
   all caught up" message shows.

Inspect the console for errors (there should be none). If any check fails, fix
`ytrss/render.py`, re-run the suite, rebuild the preview, re-verify.

- [ ] **Step 3: Clean up the preview and commit nothing (dist is gitignored)**

```bash
rm -f dist/preview.html
```

- [ ] **Step 4: Deploy**

```bash
git push origin main
```
This triggers the GitHub Pages deploy (render-only change; no new fetch load beyond the
normal build). Watch:
```bash
gh run watch $(gh run list -R timjamesriley070989-cyber/yt-rss --limit 1 --json databaseId --jq '.[0].databaseId') -R timjamesriley070989-cyber/yt-rss --exit-status
```
Then confirm the live page: `curl -s https://timjamesriley070989-cyber.github.io/yt-rss/ | grep -c 'id="show-watched"'` (expect 1).

---

## Notes for the implementer

- **All behavior is in `ytrss/render.py`** — no pipeline/model/fetch changes.
- **Valid nesting:** buttons are siblings of the `<a>` links inside `.card`, never nested
  inside an anchor.
- **Two localStorage keys, independent:** `yt-rss-last-visit` (existing "new" highlight)
  and `yt-rss-watched` (this feature). Don't merge them.
- **Pruning:** the watched set is filtered to ids present on the page on every load and
  re-saved, so it can't grow without bound.
- **No JS unit tests exist in this project** — Task 1 covers DOM hooks in Python; Task 2's
  manual checks are the real behavioral verification. Do not skip Task 2.
- **macOS SSL:** local builds need `SSL_CERT_FILE` (see README / project memory).
