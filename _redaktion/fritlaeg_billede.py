"""Fritlæg én ny illustration med BiRefNet General. Originalen ændres aldrig."""
from pathlib import Path
import argparse

MODEL = 'birefnet-general'


def kontroller_maske(image):
    """Afvis grove maskefejl; dette er ikke en semantisk kontrol af motivet."""
    alpha = image.getchannel('A')
    counts = alpha.histogram()
    total = image.width * image.height
    solid = sum(counts[128:]) / total
    clear = sum(counts[:10]) / total
    if not 0.12 <= solid <= 0.85 or clear < 0.12:
        raise ValueError('Masken bevarer for lidt motiv eller for meget baggrund')


def fritlaeg(source, destination, session=None):
    from PIL import Image
    from rembg import new_session, remove
    if session is None:
        session = new_session(MODEL, providers=['CPUExecutionProvider'])
    with Image.open(source) as original:
        output = remove(original.convert('RGB'), session=session).convert('RGBA')
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
    try:
        canvas.save(temporary, 'WEBP', quality=92, method=6)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    fritlaeg(args.original, args.output)
