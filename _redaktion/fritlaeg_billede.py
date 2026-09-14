"""Fritlæg én ny illustration med BiRefNet General. Originalen ændres aldrig."""
from pathlib import Path
import argparse
import json

MODEL = 'birefnet-general'
# Samme fil og checksum som rembg 2.0.84. Cachen må ikke skjule en defekt download.
MODEL_URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-epoch_244.onnx'
MODEL_MD5 = '7a35a0141cbbc80de11d9c9a28f52697'


def klargoer_model(progress):
    import pooch
    from rembg.sessions.birefnet_general import BiRefNetSessionGeneral
    filename = MODEL + '.onnx'
    existing = BiRefNetSessionGeneral.resolve_existing(filename)
    # Genbrug også crawlerens ældre, flade cache uden en ny 973 MB-download.
    folder = Path(existing).parent if existing else Path(BiRefNetSessionGeneral.model_dir())
    candidate = folder / filename
    progress('modelkontrol')
    if candidate.is_file() and pooch.file_hash(candidate, alg='md5') == MODEL_MD5:
        return candidate
    progress('modeldownload')
    cache = pooch.create(path=folder, base_url='',
                         registry={filename: 'md5:' + MODEL_MD5},
                         urls={filename: MODEL_URL}, retry_if_failed=2)
    # Pooch downloader til en midlertidig fil og kontrollerer checksum før flytning.
    # Kun modeldownload genforsøges; aldrig et betalt billedkøb.
    return Path(cache.fetch(filename, downloader=pooch.HTTPDownloader(
        timeout=(15, 60), chunk_size=1024 * 1024, progressbar=False)))


def kontroller_maske(image):
    """Afvis grove maskefejl; dette er ikke en semantisk kontrol af motivet."""
    alpha = image.getchannel('A')
    counts = alpha.histogram()
    total = image.width * image.height
    solid = sum(counts[128:]) / total
    clear = sum(counts[:10]) / total
    if not 0.12 <= solid <= 0.85 or clear < 0.12:
        raise ValueError('Masken bevarer for lidt motiv eller for meget baggrund')


def fritlaeg(source, destination, session=None, progress=None):
    progress = progress or (lambda stage: None)
    progress('biblioteker')
    from PIL import Image
    from rembg import new_session, remove
    if session is None:
        klargoer_model(progress)
        progress('modelindlaesning')
        session = new_session(MODEL, providers=['CPUExecutionProvider'])
    progress('maske')
    with Image.open(source) as original:
        output = remove(original.convert('RGB'), session=session).convert('RGBA')
    progress('kontrol')
    kontroller_maske(output)
    destination = Path(destination)
    # Hele motivet i en 4:3 flade med luft omkring. Undgå at små objekter
    # drukner i den oprindelige 16:9 baggrund eller klippes af CSS object-fit.
    box = output.getchannel('A').point(lambda v: 255 if v >= 16 else 0).getbbox()
    subject = output.crop(box)
    subject.thumbnail((920, 680), Image.Resampling.LANCZOS)
    # Tilpas fladen til motivet i stedet for at sætte et lille motiv midt i
    # 1024×768 tomme pixels. Fast 4:3 og ca. 10 % luft, uden opskalering.
    import math
    width = 4 * math.ceil(max(subject.width / .9, subject.height / .88 * 4 / 3) / 4)
    canvas = Image.new('RGBA', (width, width * 3 // 4))
    canvas.alpha_composite(subject, ((canvas.width-subject.width)//2, (canvas.height-subject.height)//2))
    temporary = destination.with_suffix('.webp.tmp')
    progress('gem')
    try:
        canvas.save(temporary, 'WEBP', quality=92, method=6)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main(argv=None):
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--status-fil', type=Path)
    args = parser.parse_args(argv)
    status = {'trin': 'start'}

    def save_status():
        if args.status_fil:
            temporary = args.status_fil.with_suffix('.tmp')
            temporary.write_text(json.dumps(status), encoding='utf-8')
            temporary.replace(args.status_fil)

    def progress(stage):
        status['trin'] = stage
        save_status()
        print('\nCUTOUT_STAGE=' + stage, flush=True)

    try:
        fritlaeg(args.original, args.output, progress=progress)
    except (Exception, SystemExit) as exc:
        # En separat statusfil kan ikke blive opslugt af en download-progressbar.
        # Ingen fejltekst, request-data, headers eller nøgler kopieres til loggen.
        status['fejltype'] = type(exc).__name__
        http_status = getattr(getattr(exc, 'response', None), 'status_code', None)
        if type(http_status) is int:
            status['http_status'] = http_status
        if isinstance(exc, OSError) and type(exc.errno) is int:
            status['errno'] = exc.errno
        save_status()
        print('\nCUTOUT_ERROR=' + type(exc).__name__, file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
