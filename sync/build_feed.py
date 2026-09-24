#!/usr/bin/env python3
"""Rebuild feed.xml from the live muse.ai source feed.

The muse.ai feed template does not emit <itunes:author> (Apple Podcasts
Connect's required "Artist" field), <itunes:owner>/<itunes:email>
(required by Spotify for Creators and YouTube RSS ingestion), or
<itunes:category> (Apple Podcasts Connect's required primary category).
This script fetches the source feed and writes a byte-faithful copy with
those tags added at the channel level. Episodes, GUIDs, enclosure URLs,
artwork, and descriptions are copied verbatim.

Run by .github/workflows/sync-feed.yml every morning after the episode
publish, or manually with:  python3 sync/build_feed.py
"""

import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

# ---- config (public values; they appear in the published feed XML) ----
SOURCE_FEED = (
    "https://muse.ai/podcasts/feed/623945677472634/"
    "5941e1ba-fe34-4a40-a245-8da3262dc015"
)
SELF_URL = "https://srjain04.github.io/daily-ai-download-feed/feed.xml"
AUTHOR = "Saurabh Jain"
OWNER_NAME = "Saurabh Jain"
OWNER_EMAIL = "srjain@gmail.com"
CATEGORY = "Technology"  # Apple Podcasts primary category
# ------------------------------------------------------------------------

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
OUT = Path(__file__).resolve().parent.parent / "feed.xml"


def fetch_source_feed() -> str:
    req = urllib.request.Request(SOURCE_FEED, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def build_proxy(xml: str) -> str:
    if "<itunes:author>" in xml or "<itunes:owner>" in xml:
        raise SystemExit("source feed already has the iTunes tags; refusing to double-tag")

    tags = (
        f"  <itunes:author>{escape(AUTHOR)}</itunes:author>\n"
        f"  <itunes:owner>\n"
        f"    <itunes:name>{escape(OWNER_NAME)}</itunes:name>\n"
        f"    <itunes:email>{escape(OWNER_EMAIL)}</itunes:email>\n"
        f"  </itunes:owner>\n"
        f"  <itunes:category text=\"{escape(CATEGORY)}\"/>\n"
    )
    m = re.search(r"(<channel>\s*<title>.*?</title>\s*\n)", xml, re.DOTALL)
    if not m:
        raise SystemExit("could not locate channel title in source feed")
    xml = xml[: m.end()] + tags + xml[m.end():]

    xml = re.sub(
        r'(<atom:link\s+href=")[^"]*(")',
        lambda mo: mo.group(1) + escape(SELF_URL) + mo.group(2),
        xml,
        count=1,
    )
    return xml


def main() -> None:
    proxy = build_proxy(fetch_source_feed())
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if proxy == old:
        print("feed.xml unchanged")
        return
    OUT.write_text(proxy, encoding="utf-8")
    n = len(re.findall(r"<item>", proxy))
    print(f"wrote {OUT} ({len(proxy)} bytes, {n} episodes)")


if __name__ == "__main__":
    main()
