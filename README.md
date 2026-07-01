# yt-rss

A static dashboard of recent uploads from my YouTube subscriptions.

- Merged, newest-first timeline of the **last 14 days** across all subscribed channels.
- Grouped by day, filterable by channel, with "new since last visit" highlighting.
- Data comes from YouTube's public per-channel RSS feeds (no API key).

## Run locally

```bash
python3 build.py                 # builds dist/index.html for all channels
python3 build.py --output out.html --window-days 7
open dist/index.html
```

### macOS note
If local runs fail with CERTIFICATE_VERIFY_FAILED, your Python can't find a CA bundle. Fix once by running the Python installer's "Install Certificates.command", or set SSL_CERT_FILE to a PEM bundle. (GitHub Actions is unaffected.)

## How it deploys

A GitHub Action (.github/workflows/build.yml) runs every 3 hours, builds dist/index.html, and deploys it to GitHub Pages. The published page is **public**.
