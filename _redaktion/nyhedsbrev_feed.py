"""Læs offentligt RSS, direkte eller via RSS2JSON; ingen manuelle kildefiler."""
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlencode

FEED_URL = "https://metatrends.substack.com/feed"
READER_URL = "https://api.rss2json.com/v1/api.json?" + urlencode({"rss_url": FEED_URL})
MAX_BYTES = 8_000_000


class FeedUnavailable(ValueError):
    """Direkte netværks-/adgangsfejl; en almindelig RSS-læser kan bruges."""


def fetch_xml(url):
    if url != FEED_URL:
        raise ValueError("Kun den verificerede Metatrends-kilde er tilladt")
    return _download(url, {"application/rss+xml", "application/xml", "text/xml"}, "RSS")


def fetch_reader(url):
    if url != FEED_URL:
        raise ValueError("Kun den verificerede Metatrends-kilde er tilladt")
    raw = _download(READER_URL, {"application/json"}, "RSS-læser")
    return json.loads(raw)


def _download(url, content_types, label):
    if url not in (FEED_URL, READER_URL):
        raise ValueError("Ukendt adresse til feed-hentning")
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
            "--header", "Accept: " + ", ".join(sorted(content_types)),
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
            raise FeedUnavailable("RSS-hentningen overskred 100 sekunder; ingen mail er startet") from None
        try:
            meta = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise ValueError("RSS-hentningen gav ingen gyldig HTTP-status") from None
        status = meta.get("http_code", 0)
        content_type = meta.get("content_type") or ""
        # Kun ufølsom transportstatus i Actions; ingen cookies eller brevtekst.
        print(f"{label}: HTTP {status}, protokol {meta.get('http_version', '?')}, curl-status {result.returncode}", flush=True)
        if status in (401, 403):
            challenge = headers.exists() and "cf-mitigated: challenge" in headers.read_text().lower()
            detail = " (Cloudflare-browserkontrol)" if challenge else ""
            raise FeedUnavailable(f"{label} afviste hentning med HTTP {status}{detail}.")
        if status in (0, 408, 429, 500, 502, 503, 504, 522, 524):
            raise FeedUnavailable(f"{label} utilgængeligt: HTTP {status}, curl-status {result.returncode}")
        if status != 200 or result.returncode != 0:
            raise ValueError(f"RSS-hentningen fejlede: HTTP {status}, curl-status {result.returncode}")
        if meta.get("url_effective") != url:
            raise ValueError("RSS-hentningen endte på en ukendt adresse")
        if content_type.split(";", 1)[0].strip().lower() not in content_types:
            raise ValueError("RSS-svaret har forkert format; login- og fejlsider må ikke behandles som breve")
        if not body.exists() or body.stat().st_size > MAX_BYTES:
            raise ValueError("RSS-svaret mangler eller er for stort")
        return body.read_bytes()
