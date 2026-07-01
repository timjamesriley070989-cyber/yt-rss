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
.search { position: relative; }
.search svg { position: absolute; left: 13px; top: 50%; transform: translateY(-50%);
  width: 17px; height: 17px; color: var(--muted); pointer-events: none; }
#filter {
  width: 100%; padding: 11px 14px 11px 40px; font-size: .95rem; color: var(--text);
  background: var(--chip); border: 1px solid transparent; border-radius: 12px; outline: none;
  transition: border-color .15s, background .15s;
}
#filter:focus { border-color: var(--accent); background: var(--bg); }
#filter::placeholder { color: var(--muted); }
#feed {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 28px 18px; margin-top: 24px;
}
.card { text-decoration: none; color: inherit; display: flex; flex-direction: column; }
.thumb-wrap {
  position: relative; border-radius: 14px; overflow: hidden; background: var(--skeleton);
  box-shadow: var(--shadow); transition: transform .18s ease, box-shadow .18s ease;
}
.card:hover .thumb-wrap { transform: translateY(-3px); box-shadow: var(--shadow-hover); }
.thumb { display: block; width: 100%; aspect-ratio: 16 / 9; object-fit: cover; }
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
  <div class="titles"><h1>Subscriptions</h1><span class="count">$count</span></div>
  <p class="tagline">New uploads from the last 24 hours &middot; Shorts hidden</p>
  <div class="search">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
         stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
    <input id="filter" type="search" placeholder="Filter by channel…" autocomplete="off">
  </div>
</header>
<main id="feed">
$body
</main>
<footer>Updated $updated UTC$failed</footer>
<script>
(function () {
  var KEY = "yt-rss-last-visit";
  var last = parseInt(localStorage.getItem(KEY) || "0", 10);
  document.querySelectorAll(".card").forEach(function (card) {
    if (parseInt(card.dataset.ts, 10) * 1000 > last) card.classList.add("new");
  });
  localStorage.setItem(KEY, Date.now().toString());

  var input = document.getElementById("filter");
  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    document.querySelectorAll(".card").forEach(function (card) {
      card.style.display = !q || card.dataset.channel.indexOf(q) !== -1 ? "" : "none";
    });
  });
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
            cards.append(
                f'<a class="card" href="{_html.escape(v.url)}" target="_blank" rel="noopener" '
                f'data-channel="{_html.escape(v.channel_title.lower())}" '
                f'data-ts="{int(v.published.timestamp())}">'
                f'<div class="thumb-wrap">'
                f'<img class="thumb" loading="lazy" src="{_html.escape(v.thumbnail)}" alt=""></div>'
                f'<div class="body"><h2>{_html.escape(v.title)}</h2>'
                f'<div class="sub">{_html.escape(v.channel_title)} &middot; '
                f'{relative_time(v.published, now)}</div></div></a>'
            )
        body = "\n".join(cards)
    failed = f" &middot; {failed_count} channels failed to fetch" if failed_count else ""
    return _PAGE.substitute(
        body=body,
        count=f"{len(videos)} videos",
        updated=now.strftime("%Y-%m-%d %H:%M"),
        failed=failed,
    )
