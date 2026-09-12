"""Manuel prøve med produktionsprompts og AI-kontrol. Kun til Torbens Gmail."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nyhedsbrev as n

RECIPIENT = "soemandtorben@gmail.com"


def source_for_test(config, raw=""):
    if not raw.strip():
        return max(n.fetch_feed(config["feed"]), key=lambda item: n.instant(item["dato"]))
    if len(raw) > 60000:
        raise ValueError("Testkilden er for stor")
    source = json.loads(raw)
    for field in ("url", "titel", "dato", "forfatter", "tekst"):
        if not isinstance(source.get(field), str) or not source[field].strip():
            raise ValueError("Testkilden mangler " + field)
    if n.public_url(source["url"]) != source["url"] or not source["url"].startswith("https://metatrends.substack.com/p/"):
        raise ValueError("Testkilden skal være et offentligt Metatrends-brev")
    n.instant(source["dato"])
    return source


def generate(source, config, folder, ai=n.ai_call):
    if len(source["tekst"].split()) < 450 or "diamandis" not in source["forfatter"].lower():
        raise ValueError("Seneste brev mangler fuld kilde eller korrekt forfatter")
    writer = (n.ROOT / "opsaetning/nyhedsbrev-prompt.md").read_text()
    reviewer = (n.ROOT / "opsaetning/nyhedsbrev-kontrol-prompt.md").read_text()
    errors = ""
    for attempt in range(1, min(config["maks_forsog"], 3) + 1):
        evidence = {"forsog": attempt}
        try:
            draft = ai("nyhedsbrev", writer, {"original": source, "tidligere_fejl": errors})
            evidence["udkast"] = draft
            n.validate_draft(draft, source)
            review = ai("nyhedsbrev_kontrol", reviewer,
                        {"original": source, "skriveinstruks": writer, "udkast": draft})
            evidence["kontrol"] = review
            n.validate_review(review)
        except (ValueError, RuntimeError) as exc:
            problems = evidence.get("kontrol", {}).get("problemer", [])
            errors = str(exc) + ": " + json.dumps(problems, ensure_ascii=False)
            evidence["fejl"] = errors
        else:
            errors = ""
        (folder / f"forsog-{attempt}.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2))
        if not errors:
            return draft
    raise ValueError("Testbrevet blev ikke godkendt: " + errors)


def send_test(api, draft, source, run_id, folder):
    body = n.render(draft)
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
    if check.get("status") != "draft" or check.get("body") != body or check.get("subject") != draft["emne"]:
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
    source = source_for_test(config, os.getenv("NEWSLETTER_TEST_SOURCE_JSON", ""))
    print("Seneste original: " + source["titel"] + " — " + source["dato"])
    draft = generate(source, config, folder)
    send_test(n.Buttondown(os.getenv("BUTTONDOWN_API_KEY", "")), draft, source,
              os.environ["GITHUB_RUN_ID"], folder)


if __name__ == "__main__":
    main()
