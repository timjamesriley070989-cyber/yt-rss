import html as _html
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
       max-width: 1200px; margin-inline: auto; }}
header {{ position: sticky; top: 0; background: Canvas; padding: 16px 0; border-bottom: 1px solid #8884; z-index: 1; }}
h1 {{ font-size: 1.2rem; margin: 0 0 8px; }}
#filter {{ width: 100%; padding: 8px 10px; font-size: 1rem; border: 1px solid #8886; border-radius: 8px; }}
#feed {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
         gap: 20px 14px; margin-top: 20px; }}
.card {{ text-decoration: none; color: inherit; display: flex; flex-direction: column; }}
.card:hover h2 {{ text-decoration: underline; }}
.thumb {{ width: 100%; aspect-ratio: 16 / 9; object-fit: cover; border-radius: 10px; background: #8883; }}
.card h2 {{ font-size: 0.95rem; margin: 8px 0 2px; line-height: 1.25; }}
.sub {{ font-size: 0.8rem; opacity: .7; }}
.card.new .thumb {{ outline: 2px solid #e11; outline-offset: 2px; }}
.card.new h2::after {{ content: " NEW"; color: #e11; font-size: .65rem; vertical-align: super; }}
.empty, footer {{ opacity: .6; font-size: .85rem; margin-top: 24px; }}
</style>
</head>
<body>
<header>
  <h1>Subscriptions &middot; last 24 hours</h1>
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
  document.querySelectorAll(".card").forEach(function (card) {{
    if (parseInt(card.dataset.ts, 10) * 1000 > last) card.classList.add("new");
  }});
  localStorage.setItem(KEY, Date.now().toString());

  var input = document.getElementById("filter");
  input.addEventListener("input", function () {{
    var q = input.value.trim().toLowerCase();
    document.querySelectorAll(".card").forEach(function (card) {{
      card.style.display = !q || card.dataset.channel.indexOf(q) !== -1 ? "" : "none";
    }});
  }});
}})();
</script>
</body>
</html>
"""


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
                f'<img class="thumb" loading="lazy" src="{_html.escape(v.thumbnail)}" alt="">'
                f'<h2>{_html.escape(v.title)}</h2>'
                f'<div class="sub">{_html.escape(v.channel_title)} &middot; '
                f'{relative_time(v.published, now)}</div></a>'
            )
        body = "\n".join(cards)
    failed = f" &middot; {failed_count} channels failed to fetch" if failed_count else ""
    return _PAGE.format(
        body=body,
        updated=now.strftime("%Y-%m-%d %H:%M"),
        failed=failed,
    )
