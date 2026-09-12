"""Læs det offentlige RSS med curl; ingen login, kopier eller gamle cachefiler."""
import json
from pathlib import Path
import subprocess
import tempfile

FEED_URL = "https://metatrends.substack.com/feed"
MAX_BYTES = 8_000_000


def fetch_xml(url):
    if url != FEED_URL:
        raise ValueError("Kun den verificerede Metatrends-kilde er tilladt")
    # curl forhandler HTTP/2 og komprimering med serveren. Vi identificerer
    # stadig læseren som AI-nyheder; ingen browser-efterligning eller cookies.
    with tempfile.TemporaryDirectory(prefix="nyhedsbrev-feed-") as folder:
        body = Path(folder) / "feed.xml"
        headers = Path(folder) / "headers.txt"
        command = [
            "curl", "--disable", "--silent", "--show-error", "--compressed",
            "--proto", "=https", "--connect-timeout", "10", "--max-time", "30",
            "--max-filesize", str(MAX_BYTES), "--retry", "2", "--retry-max-time", "65",
            "--fail-with-body", "--user-agent", "AI-nyheder/1.0 (+https://ainyheder.com)",
            "--header", "Accept: application/rss+xml, application/xml;q=0.9, text/xml;q=0.8",
            "--output", str(body), "--dump-header", str(headers),
            "--write-out", "%{json}", url,
        ]
        # Ingen --location: en omdirigering må ikke sende os til login, en
        # anden vært eller en uofficiel kopi af originalen.
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=100)
        except FileNotFoundError:
            raise ValueError("RSS-hentning kræver curl (findes på GitHubs Ubuntu-runner)") from None
        except subprocess.TimeoutExpired:
            raise ValueError("RSS-hentningen overskred 100 sekunder; ingen mail er startet") from None
        try:
            meta = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise ValueError("RSS-hentningen gav ingen gyldig HTTP-status") from None
        status = meta.get("http_code", 0)
        content_type = meta.get("content_type") or ""
        # Kun ufølsom transportstatus i Actions; ingen cookies eller brevtekst.
        print(f"RSS: HTTP {status}, protokol {meta.get('http_version', '?')}, curl-status {result.returncode}", flush=True)
        if status in (401, 403):
            challenge = headers.exists() and "cf-mitigated: challenge" in headers.read_text().lower()
            detail = " (Cloudflare-browserkontrol)" if challenge else ""
            raise ValueError(f"Metatrends afviste RSS-hentning med HTTP {status}{detail}. "
                             "Feedadgangen skal løses; manuel tekst eller et gammelt brev bruges ikke som reserve.")
        if status != 200 or result.returncode != 0:
            raise ValueError(f"RSS-hentningen fejlede: HTTP {status}, curl-status {result.returncode}")
        if meta.get("url_effective") != FEED_URL:
            raise ValueError("RSS-hentningen endte på en ukendt adresse")
        if content_type.split(";", 1)[0].strip().lower() not in {
            "application/rss+xml", "application/xml", "text/xml",
        }:
            raise ValueError("RSS-svaret er ikke XML; login- og fejlsider må ikke behandles som breve")
        if not body.exists() or body.stat().st_size > MAX_BYTES:
            raise ValueError("RSS-svaret mangler eller er for stort")
        return body.read_bytes()
