"""Lokal kontrol af genererede nyhedsfiler. Ingen AI-, netværks- eller skrivekald."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import redaktion
import redaktoer_agent


def kontroller(root):
    root = Path(root)
    data = json.loads((root / "data/articles.json").read_text(encoding="utf-8"))
    artikler = data.get("artikler")
    nu = redaktion.dato({"dato": data.get("opdateret")})
    if not nu or not isinstance(artikler, list) or not artikler or data.get("antal") != len(artikler):
        raise ValueError("Nyhedslisten er tom, har forkert antal eller mangler et gyldigt tidspunkt")
    links = [a.get("link") for a in artikler]
    if any(not isinstance(k, str) or not k.startswith(("https://", "http://")) for k in links) or len(set(links)) != len(links):
        raise ValueError("Nyhedslisten har ugyldige eller gentagne kildelinks")
    for a in artikler:
        for felt, moenster in (("side", r"artikel/[a-zA-Z0-9_-]+\.html"),
                               ("billede", r"data/img/[a-zA-Z0-9_.-]+")):
            sti = a.get(felt)
            if sti and (not isinstance(sti, str) or not re.fullmatch(moenster, sti)
                        or not (root / sti).is_file()):
                raise ValueError(f"En artikel henviser til en ugyldig eller manglende {felt}")
        if not a.get("kun_aktuel") and a.get("rubrik") and (a.get("sektioner") or a.get("detaljer") or a.get("betydning")) and not a.get("side"):
            raise ValueError("En færdig artikel mangler sin permanente side")
    forside = data.get("forside")
    if not isinstance(forside, dict):
        raise ValueError("Udgaven mangler en forsideplan")
    for felt in ("udvalgte", "raekkefoelge"):
        valg = forside.get(felt)
        if not isinstance(valg, list) or any(not isinstance(k, str) or k not in links for k in valg) or len(set(valg)) != len(valg):
            raise ValueError(f"Forsidens {felt} har ukendte eller gentagne historier")
    if forside.get("metode") == "agent" and (
            not redaktoer_agent.gyldig_forside(forside, artikler, nu)
            or forside.get("data_opdateret") != data["opdateret"]):
        raise ValueError("Agentens forsideplan er ugyldig eller tilhører en anden udgave")
    for navn in ("feed.xml", "sitemap-artikler.xml"):
        ET.parse(root / navn)
    # Et uafsluttet Git-merge må aldrig ende i de udgivne tekstfiler.
    filer = [root / "data/articles.json", root / "data/kommando-data.js"]
    filer += list((root / "artikel").glob("*.html"))
    for fil in filer:
        if fil.exists() and re.search(r"^(?:<{7}|={7}|>{7})(?:\s|$)", fil.read_text(encoding="utf-8"), re.M):
            raise ValueError("Uafsluttet mergekonflikt i " + str(fil.relative_to(root)))
    return len(artikler)


if __name__ == "__main__":
    antal = kontroller(Path(__file__).resolve().parent.parent)
    print(f"Udgaven er kontrolleret: {antal} artikler, forsideplan, filer og XML.")
