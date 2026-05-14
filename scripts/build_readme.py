#!/usr/bin/env python3
"""
build_readme.py
================
Assembles README.md for the CyberTechSea GitHub profile.

Pipeline:
  1. Reads the header template (header.md).
  2. Reads every content/NN-*.md in order and concatenates them.
  3. Replaces the DYNAMIC_BLOCK between BEGIN_DYNAMIC_BLOCK / END_DYNAMIC_BLOCK
     markers with live data:
       - latest 3 YouTube videos (RSS feed of channel UCUAcxD2NEJdY4MGNpvPpWQA)
       - latest 3 Zenodo releases (via ORCID 0000-0002-7975-2947)
       - GitHub stats card and top languages (via github-readme-stats)
  4. Writes the final README.md at the repository root.

The script is meant to run unattended via GitHub Actions, but it is fully
runnable locally:

    python scripts/build_readme.py

No third-party dependencies are required: only the Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────
ROOT             = Path(__file__).resolve().parent.parent
CONTENT_DIR      = ROOT / "content"
HEADER_TEMPLATE  = ROOT / "scripts" / "header.md"
OUTPUT_FILE      = ROOT / "README.md"

GITHUB_USER      = "CyberTechSea"
YT_CHANNEL_ID    = "UCUAcxD2NEJdY4MGNpvPpWQA"
YT_HANDLE        = "@CyberTechSea"
ORCID            = "0000-0002-7975-2947"

YT_RSS_URL       = f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}"
ZENODO_API       = (
    "https://zenodo.org/api/records"
    f"?q=creators.orcid:{ORCID}&sort=mostrecent&size=5"
)

DYN_BEGIN = "<!-- BEGIN_DYNAMIC_BLOCK -->"
DYN_END   = "<!-- END_DYNAMIC_BLOCK -->"

PETSCII_BEGIN = "<!-- BEGIN_PETSCII -->"
PETSCII_END   = "<!-- END_PETSCII -->"
PETSCII_FILE  = ROOT / "assets" / "easter-egg" / "dispersal-petscii.txt"

USER_AGENT = "CyberTechSea-profile-readme-builder/1.0 (+https://github.com/CyberTechSea)"

# ──────────────────────────────────────────────────────────────────────────────
# Networking helper — graceful: if the network or the API fails we keep going
# and emit a "(data unavailable at build time)" notice. The README must build.
# ──────────────────────────────────────────────────────────────────────────────
def _http_get(url: str, timeout: int = 15) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"[warn] fetch failed for {url}: {exc}", file=sys.stderr)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# YouTube — parse the public RSS feed (no API key required)
# ──────────────────────────────────────────────────────────────────────────────
def fetch_youtube_latest(n: int = 3) -> list[dict]:
    raw = _http_get(YT_RSS_URL)
    if not raw:
        return []
    try:
        # The RSS feed uses Atom namespacing.
        ns = {
            "atom":  "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
            "yt":    "http://www.youtube.com/xml/schemas/2015",
        }
        root = ET.fromstring(raw)
        entries = root.findall("atom:entry", ns)[:n]
        out = []
        for e in entries:
            vid = e.findtext("yt:videoId", default="", namespaces=ns)
            title = e.findtext("atom:title", default="(untitled)", namespaces=ns)
            published = e.findtext("atom:published", default="", namespaces=ns)
            thumb_el = e.find("media:group/media:thumbnail", ns)
            thumb = thumb_el.get("url") if thumb_el is not None else ""
            out.append({
                "id": vid,
                "title": title.strip(),
                "published": published[:10],
                "thumb": thumb,
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        return out
    except ET.ParseError as exc:
        print(f"[warn] YouTube RSS parse error: {exc}", file=sys.stderr)
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Zenodo — query the public REST API filtered by the user's ORCID
# ──────────────────────────────────────────────────────────────────────────────
def fetch_zenodo_latest(n: int = 3) -> list[dict]:
    raw = _http_get(ZENODO_API)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        hits = data.get("hits", {}).get("hits", [])[:n]
        out = []
        for h in hits:
            md = h.get("metadata", {})
            out.append({
                "title":   md.get("title", "(untitled)"),
                "doi":     md.get("doi", ""),
                "doi_url": h.get("doi_url", f"https://doi.org/{md.get('doi','')}"),
                "version": md.get("version", ""),
                "date":    md.get("publication_date", "")[:10],
            })
        return out
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"[warn] Zenodo parse error: {exc}", file=sys.stderr)
        return []


# ──────────────────────────────────────────────────────────────────────────────
# Render helpers
# ──────────────────────────────────────────────────────────────────────────────
def render_youtube(videos: list[dict]) -> str:
    if not videos:
        return (
            "### 📺 Latest from YouTube\n\n"
            f"_Latest videos unavailable at build time — visit the channel: "
            f"[{YT_HANDLE}](https://youtube.com/{YT_HANDLE.lower()})_\n"
        )
    cells = []
    for v in videos:
        cells.append(
            f"<td align='center' width='33%'>"
            f"<a href='{v['url']}'><img src='{v['thumb']}' width='220' alt='{v['title']}'/></a>"
            f"<br/><sub><b>{v['title']}</b><br/><i>{v['published']}</i></sub>"
            f"</td>"
        )
    return (
        "### 📺 Latest from YouTube — "
        f"[{YT_HANDLE}](https://youtube.com/{YT_HANDLE.lower()})\n\n"
        f"<table><tr>{''.join(cells)}</tr></table>\n"
    )


def render_zenodo(records: list[dict]) -> str:
    if not records:
        return (
            "### 🧪 Latest Zenodo releases\n\n"
            f"_Live list unavailable at build time — see all releases under "
            f"[ORCID {ORCID}](https://orcid.org/{ORCID})_\n"
        )
    lines = ["### 🧪 Latest Zenodo releases\n"]
    for r in records:
        lines.append(
            f"- **[{r['title']}]({r['doi_url']})** "
            f"— v{r['version'] or '–'} · {r['date']} · "
            f"`{r['doi']}`"
        )
    return "\n".join(lines) + "\n"


def render_github_stats() -> str:
    """github-readme-stats by anuraghazra renders dynamic SVG cards. No build needed."""
    stats = (
        f"https://github-readme-stats.vercel.app/api?username={GITHUB_USER}"
        "&show_icons=true&hide_border=true&count_private=true&include_all_commits=true"
        "&theme=transparent"
    )
    langs = (
        f"https://github-readme-stats.vercel.app/api/top-langs/?username={GITHUB_USER}"
        "&layout=compact&hide_border=true&theme=transparent"
    )
    streak = (
        f"https://streak-stats.demolab.com?user={GITHUB_USER}"
        "&hide_border=true&theme=transparent"
    )
    return (
        "### 📊 GitHub at a glance\n\n"
        f"<p align='center'>"
        f"<img src='{stats}' height='150' alt='GitHub stats'/>"
        f"<img src='{langs}' height='150' alt='Top languages'/>"
        "</p>\n"
        f"<p align='center'><img src='{streak}' height='150' alt='Contribution streak'/></p>\n"
    )


def render_footer_timestamp() -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"\n<sub>🔄 Dynamic block last refreshed: {now}</sub>\n"


# ──────────────────────────────────────────────────────────────────────────────
# Main assembly
# ──────────────────────────────────────────────────────────────────────────────
def _ordered_content_files() -> list[Path]:
    return sorted(p for p in CONTENT_DIR.glob("*.md") if re.match(r"^\d{2}-", p.name))


def _concat_sections(files: Iterable[Path]) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in files)


def _inject_dynamic_block(text: str, dynamic_md: str) -> str:
    pattern = re.compile(
        re.escape(DYN_BEGIN) + r".*?" + re.escape(DYN_END),
        re.DOTALL,
    )
    replacement = (
        f"{DYN_BEGIN}\n"
        f"<!-- This block is auto-generated. Edits will be overwritten. -->\n\n"
        f"{dynamic_md}\n"
        f"{DYN_END}"
    )
    if not pattern.search(text):
        print("[warn] dynamic-block markers not found — appending block at end",
              file=sys.stderr)
        return text + "\n\n" + replacement
    return pattern.sub(replacement, text)


def _inject_petscii(text: str) -> str:
    """Inline the PETSCII mosaic between the BEGIN_PETSCII / END_PETSCII markers."""
    if not PETSCII_FILE.exists():
        return text
    pattern = re.compile(
        re.escape(PETSCII_BEGIN) + r".*?" + re.escape(PETSCII_END),
        re.DOTALL,
    )
    mosaic = PETSCII_FILE.read_text(encoding="utf-8").rstrip()
    replacement = (
        f"{PETSCII_BEGIN}\n"
        f"```text\n{mosaic}\n```\n"
        f"{PETSCII_END}"
    )
    return pattern.sub(replacement, text) if pattern.search(text) else text


def main() -> int:
    if not HEADER_TEMPLATE.exists():
        print(f"[error] missing header template: {HEADER_TEMPLATE}", file=sys.stderr)
        return 1

    header = HEADER_TEMPLATE.read_text(encoding="utf-8")
    body   = _concat_sections(_ordered_content_files())

    # Build the live block
    yt = fetch_youtube_latest(3)
    zn = fetch_zenodo_latest(3)
    dynamic = "\n\n".join([
        render_youtube(yt),
        render_zenodo(zn),
        render_github_stats(),
        render_footer_timestamp(),
    ])

    body = _inject_dynamic_block(body, dynamic)
    body = _inject_petscii(body)
    final = header + "\n" + body

    OUTPUT_FILE.write_text(final, encoding="utf-8")
    print(f"[ok] wrote {OUTPUT_FILE} ({len(final):,} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
