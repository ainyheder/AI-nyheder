"""Tidsbudget, målinger og privat genoptagelse af crawleren. Ingen API-kald."""
import json
import time
import re
import shutil
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


class TidOpbrugt(RuntimeError):
    pass


class Drift:
    def __init__(self, root, *, clock=time.monotonic):
        self.root = Path(root)
        self.clock = clock
        self.start = clock()
        self.slut = self.start + 75 * 60
        self.trin_slut = self.slut
        self.lock = Lock()
        self.trin = []
        self.kald = {}
        self.beskyttede = {}
        self.cache = self.root / '_redaktion/.crawl-cache/arbejde.json'
        self.billeder_foer = {p.name for p in (self.root / 'data/img').glob('*')}
        try:
            self.basis = json.loads((self.root / 'data/articles.json').read_text())['opdateret']
        except (OSError, ValueError, KeyError, TypeError):
            self.basis = None

    def tid(self, maksimum=180):
        rest = min(self.slut, self.trin_slut) - self.clock()
        if rest < 5:
            raise TidOpbrugt('AI-tidsbudget opbrugt; færdiggør udgaven på godkendt materiale')
        return min(maksimum, rest)

    def plads(self):
        return min(self.slut, self.trin_slut) - self.clock() >= 5

    @contextmanager
    def fase(self, navn, minutter):
        start = self.clock()
        gammel = self.trin_slut
        self.trin_slut = min(self.slut, start + minutter * 60)
        print(f'⏱️ {navn}: starter (budget {minutter} min)', flush=True)
        try:
            yield
        finally:
            sek = round(self.clock() - start, 2)
            self.trin.append({'trin': navn, 'sekunder': sek})
            self.trin_slut = gammel
            print(f'⏱️ {navn}: {sek:.1f} sek', flush=True)

    @contextmanager
    def modelkald(self, navn):
        self.tid()
        start, ok = self.clock(), False
        try:
            yield
            ok = True
        finally:
            with self.lock:
                tal = self.kald.setdefault(navn, {'antal': 0, 'fejl': 0, 'sekunder': 0})
                tal['antal'] += 1
                tal['fejl'] += int(not ok)
                tal['sekunder'] = round(tal['sekunder'] + self.clock() - start, 2)

    def laes(self, udgivet=None):
        try:
            data = json.loads(self.cache.read_text(encoding='utf-8'))
            stamp = datetime.fromisoformat(data['opdateret'])
            alder = (datetime.now(timezone.utc) - stamp).total_seconds()
            if data.get('version') != 1 or not 0 <= alder < 24 * 3600:
                return []
            if data.get('basis_opdateret') != udgivet:
                return []  # En nyere udgivet udgave vinder altid over mellemresultater.
            if udgivet and stamp <= datetime.fromisoformat(udgivet):
                return []
            rows = data['artikler']
            if not isinstance(rows, list):
                return []
            rows = [a for a in rows if isinstance(a, dict) and a.get('link')
                    and a.get('rubrik') and not a.get('kun_aktuel')]
            for a in rows:
                navn = self.billednavn(a.get('billede'))
                if navn:
                    for fil in (navn, Path(navn).with_suffix('.jpg').name):
                        source, target = self.cache.parent / 'img' / fil, self.root / 'data/img' / fil
                        if source.is_file() and not target.exists():
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(source, target)
            return rows
        except (OSError, ValueError, TypeError, KeyError):
            return []

    def gem(self, artikler):
        # Chefbestilte ændringer venter på udgavekontrollen. Andre artikler
        # har stadig deres egen kildekontrol; kladder er aldrig publicering.
        rows = [self.beskyttede.get(a['link'], a) for a in artikler
                if a.get('link') and a.get('rubrik') and not a.get('kun_aktuel')]
        for a in rows:
            navn = self.billednavn(a.get('billede'))
            if navn and navn not in self.billeder_foer:
                for fil in (navn, Path(navn).with_suffix('.jpg').name):
                    source, target = self.root / 'data/img' / fil, self.cache.parent / 'img' / fil
                    if source.is_file() and not target.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(source, target)
        self.skriv(self.cache, {'version': 1, 'basis_opdateret': self.basis,
                              'opdateret': datetime.now(timezone.utc).isoformat(),
                              'artikler': rows})

    @staticmethod
    def billednavn(sti):
        if isinstance(sti, str) and re.fullmatch(r'data/img/[0-9a-f]{16}\.(jpg|webp)', sti):
            return Path(sti).name
        return None

    @staticmethod
    def skriv(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, default=str) + '\n', encoding='utf-8')
        temp.replace(path)

    def rapport(self, ok):
        self.skriv(self.root / 'data/crawl-status.json', {
            'opdateret': datetime.now(timezone.utc).isoformat(), 'faerdig': ok,
            'sekunder': round(self.clock() - self.start, 2),
            'ai_budget_minutter': 75, 'trin': self.trin, 'modelkald': self.kald,
        })
