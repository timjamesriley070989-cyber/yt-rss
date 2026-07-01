# yt-rss

A static dashboard of recent uploads from my YouTube subscriptions.

- Newest-first **grid** of uploads from the **last 24 hours** across all subscribed channels.
- Filterable by channel, with "new since last visit" highlighting.
- **Shorts are filtered out** (detected via the youtube.com/shorts/<id> redirect heuristic).
- Data comes from YouTube's public per-channel RSS feeds (no API key).

## Run locally

```bash
python3 build.py                 # builds dist/index.html for all channels
python3 build.py --window-hours 48   # widen the time window
python3 build.py --keep-shorts       # skip Shorts filtering
open dist/index.html
```

### macOS note
If local runs fail with CERTIFICATE_VERIFY_FAILED, your Python can't find a CA bundle. Fix once by running the Python installer's "Install Certificates.command", or set SSL_CERT_FILE to a PEM bundle. (GitHub Actions is unaffected.)

## How it deploys

A GitHub Action (.github/workflows/build.yml) runs every 3 hours, builds dist/index.html, and deploys it to GitHub Pages. The published page is **public**.
