from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def build_icon(source_png: Path, target_ico: Path) -> None:
    base = Image.open(source_png).convert("RGBA")
    canvas = Image.new("RGBA", (512, 512), (255, 255, 255, 0))

    # Pencil image area
    pencil = base.resize((360, 360), Image.LANCZOS)
    canvas.paste(pencil, (20, 76), pencil)

    # Text area
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arialbd.ttf", 64)
    except Exception:
        font = ImageFont.load_default()

    text = "MANIFeST OU"
    x, y = 120, 420

    # subtle stroke for readability
    for dx in (-2, -1, 1, 2):
        for dy in (-2, -1, 1, 2):
            draw.text((x + dx, y + dy), text, font=font, fill=(255, 255, 255, 220))
    draw.text((x, y), text, font=font, fill=(28, 62, 97, 255))

    target_ico.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target_ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    src = root / "app" / "static" / "img" / "HU_Bleistift.png"
    dst = root / "app" / "static" / "img" / "manifest_ou.ico"
    build_icon(src, dst)
    print(dst)
