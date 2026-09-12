"""Manuel prøve med produktionsprompts og AI-kontrol. Kun til Torbens Gmail."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nyhedsbrev as n

RECIPIENT = "soemandtorben@gmail.com"


def source_for_test(config):
    # Prøven skal teste samme levende kilde som den daglige udsendelse.
    return max(n.fetch_feed(config["feed"]), key=lambda item: n.instant(item["dato"]))


def generate(source, config, folder, ai=n.ai_call):
    if len(source["tekst"].split()) < 450 or "diamandis" not in source["forfatter"].lower():
        raise ValueError("Seneste brev mangler fuld kilde eller korrekt forfatter")
    writer = (n.ROOT / "opsaetning/nyhedsbrev-prompt.md").read_text()
    reviewer = (n.ROOT / "opsaetning/nyhedsbrev-kontrol-prompt.md").read_text()
    errors = ""
    previous = None
    next_step = "skrivning"
    for attempt in range(1, min(config["maks_forsog"], 3) + 1):
        def save_attempt(result):
            (folder / f"forsog-{attempt}.json").write_text(json.dumps(
                {"forsog": attempt, **result}, ensure_ascii=False, indent=2))
        evidence = n.editorial_attempt(source, writer, reviewer, previous, errors, ai,
                                       review_only=next_step == "kontrol", checkpoint=save_attempt)
        previous = evidence.get("udkast", previous)
        errors = evidence.get("fejl", "")
        next_step = evidence.get("naeste_trin", "skrivning")
        save_attempt(evidence)
        if not errors:
            return evidence["udkast"]
    raise ValueError("Testbrevet blev ikke godkendt: " + errors)


def send_test(api, draft, source, run_id, folder, config=None):
    entry = {'url': source['url'], 'draft': draft}
    def save_images():
        (folder / 'billeder-status.json').write_text(json.dumps(entry.get('billeder', {}), ensure_ascii=False, indent=2))
    images = n.nyhedsbrev_billeder.prepare(entry, config or {}, api, save_images)
    body = n.render(draft, images)
    (folder / "brev.html").write_text(body)
    (folder / "brev.md").write_text(draft["brev_markdown"])
    key = "newsletter-test-" + run_id
    remote = api.call("POST", "", {"subject": draft["emne"], "body": body, "status": "draft"}, key + "-create")
    email_id = remote.get("id")
    if not isinstance(email_id, str) or remote.get("status") != "draft":
        raise ValueError("Buttondown bekræftede ikke en kladde")
    status = {"email_id": email_id, "recipient": RECIPIENT, "source_url": source["url"],
              "subject": draft["emne"], "status": "kladde", "run_id": run_id}
    def save():
        (folder / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2))
    save()
    check = api.get(email_id)
    if not n.unchanged_draft(check, draft["emne"], body):
        # Kun den relevante kladde; ingen kontooplysninger, headers eller nøgler.
        (folder / "buttondown-kladde.json").write_text(json.dumps(
            {k: check.get(k) for k in ("status", "subject", "body")}, ensure_ascii=False, indent=2))
        raise ValueError("Kladden er ændret efter kontrollen")
    status["status"] = "testafsendelse_påbegyndt"
    save()
    # Dokumenteret test-endpoint. Aldrig PATCH about_to_send eller abonnentudsendelse.
    api.call("POST", "/" + email_id + "/send-draft", {"recipients": [RECIPIENT]}, key + "-send")
    status.update(status="test_accepteret", tidspunkt=n.now())
    save()
    print("Buttondown har accepteret test til " + RECIPIENT + ": " + draft["emne"])


def main():
    # Genkørsel efter et uklart send-resultat skal undersøges, ikke automatisk gentages.
    if os.getenv("GITHUB_EVENT_NAME") != "workflow_dispatch" or os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise ValueError("Kun en ny, manuel GitHub-testkørsel er tilladt")
    folder = Path("newsletter-test-output")
    folder.mkdir(exist_ok=False)
    config = json.loads((n.ROOT / "opsaetning/nyhedsbrev.json").read_text())
    source = source_for_test(config)
    print("Seneste original: " + source["titel"] + " — " + source["dato"])
    draft = generate(source, config, folder)
    send_test(n.Buttondown(os.getenv("BUTTONDOWN_API_KEY", "")), draft, source,
              os.environ["GITHUB_RUN_ID"], folder, config)


if __name__ == "__main__":
    main()
