import re
from datetime import datetime, timedelta, timezone
from ytrss.models import Video
from ytrss.render import relative_time, render_html

NOW = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)


def test_relative_time():
    assert relative_time(NOW - timedelta(minutes=30), NOW) == "30m ago"
    assert relative_time(NOW - timedelta(hours=2), NOW) == "2h ago"
    assert relative_time(NOW - timedelta(days=3), NOW) == "3d ago"


def test_render_html_renders_cards_and_is_self_contained():
    video = Video(
        video_id="x",
        title="My Video",
        channel_title="Chan",
        published=NOW - timedelta(hours=1),
        thumbnail="https://i3.ytimg.com/vi/x/hqdefault.jpg",
    )
    html = render_html([video], now=NOW, failed_count=0)
    assert 'class="card"' in html
    assert "My Video" in html
    assert "Chan" in html
    assert "https://www.youtube.com/watch?v=x" in html
    # grid layout, not the old list
    assert "grid-template-columns" in html
    # self-contained: no external CSS/JS files referenced
    assert '<link rel="stylesheet"' not in html
    # the only remote resource is the thumbnail, on a ytimg.com CDN host
    stripped = re.sub(r"https://i\d*\.ytimg\.com", "", html)
    assert 'src="http' not in stripped


def test_render_html_reports_failures_and_empty_state():
    html = render_html([], now=NOW, failed_count=7)
    assert "7" in html
    assert "no uploads in the last 24 hours" in html.lower()


def test_render_html_has_watched_state_hooks():
    video = Video(video_id="abc", title="T", channel_title="C",
                  published=NOW - timedelta(hours=1),
                  thumbnail="https://i3.ytimg.com/x.jpg")
    html = render_html([video], now=NOW, failed_count=0)
    assert 'data-vid="abc"' in html
    assert 'class="dismiss"' in html
    assert 'class="unhide"' in html
    assert 'id="show-watched"' in html
    assert 'id="count"' in html
    assert 'id="caught-up"' in html
