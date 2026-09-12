#!/usr/bin/env python3
"""Nye Metatrends-breve → redaktør → kontrol → Buttondown.

--check læser kun det offentlige feed. --run kræver GitHub Actions samt en
separat git-checkout til varig status. Hvert checkpoint pushes FØR udsendelse.
Ingen abonnentdata eller API-nøgler gemmes. Standardbiblioteket er nok.
"""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
import uuid
import xml.etree.ElementTree as ET
from _redaktion import nyhedsbrev_billeder

ROOT = Path(__file__).resolve().parent
STATE_BRANCH = "codex/nyhedsbrev-status"
REMOTE_SENT = {"about_to_send", "in_flight", "sent", "resending", "scheduled", "paused", "throttled"}


def now():
    return datetime.now(timezone.utc).isoformat()


def instant(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if d.tzinfo is None:
        raise ValueError("Dato mangler tidszone")
    return d.astimezone(timezone.utc)


def public_url(value):
    u = urlsplit(value)
    if u.scheme != "https" or u.hostname != "metatrends.substack.com" or not u.path.startswith("/p/") or u.username or u.port:
        raise ValueError("Ukendt kildeadresse")
    return urlunsplit(("https", "metatrends.substack.com", u.path.rstrip("/"), "", ""))


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.skip += 1
        if tag in {"p", "div", "h1", "h2", "h3", "li", "br"} and not self.skip:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.skip = max(0, self.skip - 1)
        if tag in {"p", "div", "h1", "h2", "h3", "li"} and not self.skip:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def feed_items(raw):
    if len(raw) > 8_000_000 or b"<!ENTITY" in raw.upper() or b"<!DOCTYPE" in raw.upper():
        raise ValueError("Uventet feedformat")
    root = ET.fromstring(raw)
    items = {}
    for item in root.findall("./channel/item"):
        url = public_url(item.findtext("link", ""))
        date = parsedate_to_datetime(item.findtext("pubDate", ""))
        if date.tzinfo is None:
            raise ValueError("Kildedato mangler tidszone")
        source_html = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
        parser = TextOnly()
        parser.feed(source_html)
        body = "\n".join(s.strip() for s in "".join(parser.parts).splitlines() if s.strip())
        author = item.findtext("{http://purl.org/dc/elements/1.1/}creator", "")
        key = hashlib.sha256(url.encode()).hexdigest()[:24]
        items[key] = {"id": key, "url": url, "titel": item.findtext("title", ""),
                      "dato": date.astimezone(timezone.utc).isoformat(), "forfatter": author,
                      "tekst": body}
    if not items:
        raise ValueError("Feedet indeholder ingen breve")
    return sorted(items.values(), key=lambda p: p["dato"])


def fetch_feed(url):
    if url != "https://metatrends.substack.com/feed":
        raise ValueError("Kun den verificerede Metatrends-kilde er tilladt")
    with urlopen(Request(url, headers={"User-Agent": "AI-nyheder/1.0 (+https://ainyheder.com)"}), timeout=30) as response:
        if urlsplit(response.url).hostname != "metatrends.substack.com":
            raise ValueError("Feedet viderestiller til en ukendt vært")
        return feed_items(response.read(8_000_001))


def validate_draft(draft, source):
    if not isinstance(draft, dict) or draft.get("status") != "udkast":
        raise ValueError("Redaktøren kræver mere materiale eller afklaring")
    for field, limit in (("emne", 160), ("preheader", 240), ("brev_markdown", 25000)):
        if not isinstance(draft.get(field), str) or not draft[field].strip() or len(draft[field]) > limit:
            raise ValueError("Manglende eller for langt felt: " + field)
    body = draft["brev_markdown"]
    if r"\n" in body or r"\r" in body:
        raise ValueError("Brug rigtige linjeskift i brev_markdown, ikke dobbelt-escaped \\n eller \\r")
    words = len(body.split())
    if not 650 <= words <= 1600:
        raise ValueError("Brevet skal have substans uden at blive for langt (650–1600 ord)")
    credit = re.search(r"\[Peter Diamandis[’'] læserbrev\]\(" + re.escape(source['url']) + r"\)", body)
    mentions = len(re.findall("diamandis", body, re.I))
    if not credit or credit.start() > 1400 or mentions != 1:
        raise ValueError(f"Kreditering: navnet Diamandis står {mentions} gange; det må kun stå én gang, "
                         f"i linket [Peter Diamandis’ læserbrev]({source['url']}) inden for de første 1400 tegn. "
                         "Fjern alle andre navneforekomster, også i åbning og overskrifter.")
    if re.search(r"unsubscribe|afmeld|manage your subscription|<[^>]+>|\{\{|!\[", body, re.I):
        raise ValueError("HTML, billeder, skabelonkode eller ekstra afmelding er ikke tilladt")
    note = draft.get("redaktionsnote")
    if not isinstance(note, dict) or note.get("uafklaret") != []:
        raise ValueError("Uafklarede forhold i redaktionsnoten")
    original = note.get("original", {})
    if any(original.get(k) != source[k] for k in ("url", "titel", "dato", "forfatter")):
        raise ValueError("Kildens metadata er ændret")
    if not note.get("hovedide") or not note.get("bevarede_pointer") or not note.get("selvstaendige_greb"):
        raise ValueError("Redaktionsnoten mangler konkrete redaktionelle valg")
    nyhedsbrev_billeder.validate_plan(draft)
    return draft


def validate_review(review):
    fields = ("godkendt", "fuld_kilde", "faktuel_troskab", "selvstaendig", "laesevaerdi")
    if not isinstance(review, dict) or any(review.get(f) is not True for f in fields) or review.get("problemer") != []:
        raise ValueError("Kvalitetskontrollen afviste brevet")


def inline(text):
    # Ingen rå model-HTML. Kun sikre, eksplicitte HTTPS-links og fed tekst.
    escaped = html.escape(text)
    def link(m):
        address = html.unescape(m[2])
        u = urlsplit(address)
        if u.scheme != "https" or not u.hostname or u.username or any(c.isspace() for c in address):
            return m[1]
        return '<a href="' + html.escape(address, quote=True) + '" style="color:#d5ff5f!important;text-decoration:underline">' + m[1] + '</a>'
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, escaped)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)


def comparison(block):
    """En lille Markdown-tabel; rækkefølge og forbehold bevares ordret."""
    lines = block.splitlines()
    if len(lines) < 3 or not all(line.strip().startswith("|") and line.strip().endswith("|") for line in lines):
        return None
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if any(len(row) != 2 for row in rows) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in rows[1]):
        return None
    cells = []
    for col, color in enumerate(("#d5ff5f", "#87dcf0")):
        content = []
        for row in rows[2:]:
            # Forfatteren fremhæver selv det centrale tal; ingen tal gættes ud fra brødteksten.
            value = row[col]
            emphasis = re.fullmatch(r"\*\*(.+?)\*\*", value)
            if emphasis:
                content.append('<p class="comparison-value" style="font-size:30px;line-height:1.1;font-weight:750;color:' + color + '!important;margin:0 0 12px">' + inline(emphasis[1]) + '</p>')
            else:
                content.append('<p style="font-size:15px;line-height:1.5;color:#d8dde6!important;margin:0 0 10px">' + inline(value) + '</p>')
        cells.append('<td width="50%" valign="top" class="comparison-cell" style="width:50%;padding:18px 16px;background:#171d26;color:#f2f3f5!important;overflow-wrap:break-word;word-wrap:break-word;hyphens:auto">'
                     '<p style="font-size:12px;line-height:1.4;font-weight:700;letter-spacing:0.7px;text-transform:uppercase;color:' + color + '!important;margin:0 0 16px">'
                     + inline(rows[0][col]) + '</p>' + ''.join(content) + '</td>')
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;table-layout:fixed;margin:8px 0 18px;border:0;background:#171d26;border-radius:12px;overflow:hidden"><tr>'
            + ''.join(cells) + '</tr></table>')


def illustration(image, preview=False):
    url = image['url']
    if not (preview and re.fullmatch(r'illustrationer/[a-z0-9-]+\.png', url)):
        nyhedsbrev_billeder.public_image_url(url)
    # align giver en læsbar fallback i mailklienter uden moderne layout-CSS.
    return ('<img class="editorial-image" align="right" width="180" src="' + html.escape(url, quote=True)
            + '" alt="' + html.escape(image['alt'], quote=True)
            + '" style="float:right;width:30%;max-width:180px;height:auto;margin:0 0 12px 18px;border:0;background:transparent">')


def render(draft, images=None, *, preview=False):
    body = draft["brev_markdown"].strip()
    if r"\n" in body or r"\r" in body:
        raise ValueError("Brevets linjeskift er dobbelt-escaped; layoutet kan ikke bygges")
    blocks = []
    first_paragraph = True
    images = {item['placering']: item for item in (images or [])[:2]}
    pending_image = images.get('intro')
    for block in re.split(r"\n\s*\n", body):
        lines = block.splitlines()
        if block.startswith("# ") and len(lines) == 1:
            blocks.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;margin:20px 0 24px;background:#d5ff5f;border:0;border-radius:14px"><tr><td class="hero-pad" style="padding:26px 22px">'
                          '<h1 class="title" style="font-size:38px;line-height:1.1;letter-spacing:-1.2px;font-weight:800;color:#101609!important;margin:0">' + inline(block[2:]) + '</h1></td></tr></table>')
        elif block.startswith("## ") and len(lines) == 1:
            pending_image = images.get(block[3:])
            blocks.append('<h2 style="font-size:24px;line-height:1.25;letter-spacing:-0.4px;color:#f2f3f5!important;margin:30px 0 16px">'
                          '<span aria-hidden="true" style="color:#d5ff5f!important">/ </span>' + inline(block[3:]) + '</h2>')
        elif (panel := comparison(block)) is not None:
            blocks.append(panel)
        elif all(line.startswith("> ") for line in lines):
            # Egen redaktionel pointe, ikke et citat: ingen citationstegn eller blockquote-semantik.
            text = " ".join(line[2:] for line in lines)
            blocks.append('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;margin:22px 0;background:#162b32;border:0;border-radius:12px"><tr><td class="callout-pad" style="padding:20px">'
                          '<p style="font-size:19px;line-height:1.5;color:#c3f1fb!important;margin:0">' + inline(text) + '</p></td></tr></table>')
        elif all(line.startswith("- ") for line in lines):
            blocks.append('<ul style="margin:8px 0 22px;padding-left:23px;color:#d5ff5f!important">' + ''.join(
                '<li style="font-size:17px;line-height:1.6;margin:0 0 12px;padding-left:4px"><span style="color:#e1e5ec!important">' + inline(line[2:]) + '</span></li>' for line in lines) + '</ul>')
        else:
            lead = first_paragraph and len(block.split()) <= 80
            size = "20px" if lead else "17px"
            color = "#f2f3f5" if lead else "#d8dde6"
            picture = illustration(pending_image, preview) if pending_image else ''
            pending_image = None
            blocks.append('<p style="font-size:' + size + ';line-height:1.65;color:' + color + '!important;margin:0 0 18px">' + picture + inline(block.replace("\n", " ")) + '</p>')
            first_paragraph = False
    css = (ROOT / "opsaetning/nyhedsbrev-design.css").read_text()
    # Buttondown leverer den eneste afmeldingsfooter.
    return ('<style>' + css + '</style><div style="display:none;max-height:0;overflow:hidden;mso-hide:all">'
            + html.escape(draft["preheader"]) + '</div><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#0c0e12"><tr><td align="center" class="outer" style="padding:0">'
            '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:none;background:#0c0e12;border:0;font-family:Arial,sans-serif">'
            '<tr><td class="pad" style="padding:20px 16px"><div style="font-size:22px;letter-spacing:-0.7px;color:#f2f3f5!important"><b style="display:inline-block;padding:5px 7px;background:#d5ff5f;color:#0c0e12!important;border-radius:7px">AI</b> nyheder</div>'
            + "".join(blocks) + '<p style="padding-top:8px;margin:24px 0 8px"><a href="https://ainyheder.com" style="display:inline-block;padding:12px 16px;background:#202833;border-radius:8px;color:#d5ff5f!important;font-size:15px;font-weight:700;text-decoration:none">Besøg AI-nyheder</a></p></td></tr></table></td></tr></table>')


class Buttondown:
    def __init__(self, token):
        if not token:
            raise ValueError("BUTTONDOWN_API_KEY mangler")
        self.token = token

    def call(self, method, path, data=None, key=None):
        headers = {"Authorization": "Token " + self.token, "Content-Type": "application/json"}
        if key:
            headers["X-Idempotency-Key"] = str(uuid.uuid5(uuid.NAMESPACE_URL, key))
        req = Request("https://api.buttondown.com/v1/emails" + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      headers=headers, method=method)
        with urlopen(req, timeout=45) as response:
            return json.load(response)

    def create(self, entry):
        return self.call("POST", "", {"subject": entry["draft"]["emne"], "body": entry["html"],
                                      "status": "draft", "metadata": {"source_url": entry["url"]}}, entry["url"] + "#draft-v1")

    def upload_image(self, png, key):
        # Dokumenteret /v1/images: multipart-feltet hedder image, svaret image.
        if not png.startswith(b'\x89PNG\r\n\x1a\n') or len(png) > 3_000_000:
            raise ValueError('Nyhedsbrevsbilledet skal være en PNG under 3 MB')
        boundary = 'newsletter-' + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="illustration.png"\r\n'
                'Content-Type: image/png\r\n\r\n').encode() + png + f'\r\n--{boundary}--\r\n'.encode()
        request = Request('https://api.buttondown.com/v1/images', data=body, method='POST', headers={
            'Authorization': 'Token ' + self.token,
            'Content-Type': 'multipart/form-data; boundary=' + boundary,
            'X-Idempotency-Key': str(uuid.uuid5(uuid.NAMESPACE_URL, 'newsletter-image-' + key))})
        with urlopen(request, timeout=60) as response:
            return json.load(response)

    def get(self, email_id):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", email_id):
            raise ValueError("Ugyldigt Buttondown-id")
        return self.call("GET", "/" + email_id)

    def send(self, email_id, source_url):
        return self.call("PATCH", "/" + email_id, {"status": "about_to_send"}, source_url + "#send-v1")


class GitStore:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.path = self.folder / "state.json"
        branch = self.git("branch", "--show-current").strip()
        if branch != STATE_BRANCH or self.folder == ROOT:
            raise ValueError("Status skal have sin egen checkout og gren")
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            # Manglende status på en eksisterende gren må ikke nulstille historikken.
            head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=self.folder, capture_output=True)
            if head.returncode == 0:
                raise ValueError("Eksisterende statusgren mangler state.json")
            self.state = {"version": 1, "entries": {}}
        if self.state.get("version") != 1 or not isinstance(self.state.get("entries"), dict):
            raise ValueError("Ugyldig statusfil; udsendelse stoppet")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.folder, check=True, text=True, capture_output=True).stdout

    def save(self):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2) + "\n")
        temp.replace(self.path)
        self.git("add", "state.json")
        changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=self.folder).returncode
        if changed:
            self.git("commit", "-m", "Nyhedsbrev: gem redaktions- og udsendelsesstatus")
        # En mislykket push må ALDRIG efterfølges af et API-kald, der kan sende mail.
        self.git("push", "origin", "HEAD:refs/heads/" + STATE_BRANCH)


def ai_call(step, prompt, payload):
    import crawler
    config = json.loads((ROOT / "opsaetning/nyhedsbrev.json").read_text())
    print("AI-trin " + step + ": valgt model " + (crawler.hjerne_model(step) or config["model"]))
    return crawler.parse_json_objekt(crawler.hjerne_kald(step, prompt, json.dumps(payload, ensure_ascii=False),
                                                       6500 if step == "nyhedsbrev" else 2200, config["model"]))


def process(items, config, store, api, ai=ai_call):
    entries = store.state["entries"]
    start = instant(config["nye_fra"])
    writer_prompt = (ROOT / "opsaetning/nyhedsbrev-prompt.md").read_text()
    review_prompt = (ROOT / "opsaetning/nyhedsbrev-kontrol-prompt.md").read_text()
    sources = {s["id"]: s for s in items}
    for source in items:
        key = source["id"]
        if key not in entries:
            old = instant(source["dato"]) <= start
            entries[key] = {k: source[k] for k in ("id", "url", "titel", "dato", "forfatter")}
            entries[key].update(status="baseline" if old else "venter", forsog=0)
    store.save()
    attention = []
    # Genoptag også godkendte breve, selv hvis originalen er faldet ud af RSS.
    for key, entry in sorted(entries.items(), key=lambda pair: pair[1]["dato"]):
        status = entry["status"]
        if status in {"baseline", "sendt", "overdraget"}:
            continue
        if status in {"afventer", "opretter", "sender"}:
            # Uklart POST uden et gemt id kan have oprettet et udkast, men ikke sendt.
            # Uklart PATCH må kun afklares via GET, aldrig via en ny udsendelse.
            if entry.get("email_id"):
                remote = api.get(entry["email_id"])
                if remote.get("status") in REMOTE_SENT:
                    entry.update(status="sendt" if remote["status"] == "sent" else "overdraget",
                                 buttondown_status=remote["status"], opdateret=now())
                    store.save()
                    continue
            attention.append(entry["titel"])
            continue
        if status == "venter":
            if entry["forsog"] >= config["maks_forsog"]:
                attention.append(entry["titel"])
                continue
            source = sources.get(key)
            if not source:
                attention.append(entry["titel"])
                continue
            # Ingen erstatning med RSS-resumé, hvis fuld tekst mangler.
            if len(source["tekst"].split()) < 450 or "diamandis" not in source["forfatter"].lower():
                attention.append(entry["titel"])
                continue
            entry["forsog"] += 1
            entry.pop("kontrol", None)
            store.save()
            try:
                draft = validate_draft(ai("nyhedsbrev", writer_prompt,
                    {"original": source, "tidligere_fejl": entry.get("fejl", "")}), source)
                review = ai("nyhedsbrev_kontrol", review_prompt,
                            {"original": source, "skriveinstruks": writer_prompt, "udkast": draft})
                # Gem kontrollens konkrete rettelser til næste skriveforsøg.
                entry["kontrol"] = review
                validate_review(review)
                entry.update(draft=draft, status="illustrerer", fejl="")
            except (ValueError, RuntimeError) as exc:
                problems = entry.get("kontrol", {}).get("problemer", [])
                entry["fejl"] = str(exc)[:500] + (": " + "; ".join(str(p) for p in problems)[:1500] if problems else "")
                store.save()
                attention.append(entry["titel"])
                continue
            store.save()
        if entry['status'] == 'illustrerer':
            images = nyhedsbrev_billeder.prepare(entry, config, api, store.save)
            entry.update(html=render(entry['draft'], images), status='klar')
            store.save()
        if entry["status"] == "klar":
            entry.update(status="opretter", opdateret=now())
            store.save()
            remote = api.create(entry)
            if not isinstance(remote.get("id"), str) or remote.get("status") != "draft":
                raise ValueError("Buttondown returnerede ikke et kladde-id; stopper")
            entry.update(email_id=remote["id"], status="kladde")
            store.save()
        if entry["status"] == "kladde":
            remote = api.get(entry["email_id"])
            if remote.get("status") in REMOTE_SENT:
                entry.update(status="overdraget", buttondown_status=remote["status"])
                store.save()
                continue
            # Stop hvis et menneske har ændret kladden efter AI-kontrollen.
            if remote.get("status") != "draft" or remote.get("subject") != entry["draft"]["emne"] or remote.get("body") != entry["html"]:
                entry.update(status="afventer", fejl="Buttondown-kladden er ændret efter kontrollen")
                store.save()
                attention.append(entry["titel"])
                continue
            entry.update(status="sender", opdateret=now())
            store.save()
            remote = api.send(entry["email_id"], entry["url"])
            if remote.get("status") not in REMOTE_SENT:
                raise ValueError("Buttondown har ikke bekræftet køen; genudsender ikke automatisk")
            entry.update(status="sendt" if remote["status"] == "sent" else "overdraget",
                         buttondown_status=remote["status"], opdateret=now())
            store.save()
            print("Overdraget til Buttondown: " + entry["titel"])
    if attention:
        raise ValueError(f"{len(attention)} brev(e) tilbageholdt. Se redaktionsstatus på statusgrenen.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    config = json.loads((ROOT / "opsaetning/nyhedsbrev.json").read_text())
    if not config["aktiv"]:
        print("Nyhedsbrevet er pauset i opsaetning/nyhedsbrev.json")
        return
    items = fetch_feed(config["feed"])
    if args.check:
        eligible = [s for s in items if instant(s["dato"]) > instant(config["nye_fra"])]
        print(json.dumps({"breve_i_feed": len(items), "nye_efter_start": len(eligible),
                          "nyeste": [{k: s[k] for k in ("titel", "dato", "url", "forfatter")} for s in items[-3:]]}, ensure_ascii=False, indent=2))
        return
    if os.environ.get("GITHUB_ACTIONS") != "true" or not args.state_dir:
        raise ValueError("Automatisk udsendelse køres kun af GitHub Actions med varig status")
    if not (os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        raise ValueError("Redaktørens API-nøgle mangler")
    process(items, config, GitStore(args.state_dir), Buttondown(os.environ.get("BUTTONDOWN_API_KEY", "")))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # HTTP-fejltekst og request headers må ikke komme i Actions-loggen.
        print("Nyhedsbrev stoppet: " + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
