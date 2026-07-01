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
