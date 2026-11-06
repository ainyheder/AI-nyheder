"""Undgå gentagne bot-udfordringer på offentlige artikelsider i samme kørsel."""
from threading import Lock
from urllib.parse import urlsplit

_lock = Lock()
_blokerede = set()


class KildeBlokeret(OSError):
    code = 403


def kontroller(url):
    host = urlsplit(url).hostname
    with _lock:
        if host in _blokerede:
            raise KildeBlokeret('Kildens artikelsider kræver en browserudfordring (HTTP 403)')


def registrer(url, fejl):
    # En enkelt normal 403 må ikke få os til at opgive alle øvrige artikler.
    headers = getattr(fejl, 'headers', None)
    if getattr(fejl, 'code', None) == 403 and headers and headers.get('Cf-Mitigated', '').lower() == 'challenge':
        host = urlsplit(url).hostname
        with _lock:
            ny = host not in _blokerede
            _blokerede.add(host)
        if ny:
            print(f'  ⏳ {host}: artikelsider blokeret af browserudfordring; prøves igen ved næste kørsel')
        return True
    return False
