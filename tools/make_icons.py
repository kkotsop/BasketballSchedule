"""Makes assets/logo.png and the home-screen icons from tools/source/logo_rbg.png.  Usage: python tools/make_icons.py"""
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parent.parent
src = Image.open(ROOT / "tools/source/logo_rbg.png").convert("RGBA")
A = ROOT / "assets"
src.resize((256, 256), Image.LANCZOS).save(A / "logo.png", optimize=True)
def icon(size, pad=0.08):
    im = Image.new("RGBA", (size, size), (255, 255, 255, 255)); inner = int(size * (1 - 2 * pad))
    im.alpha_composite(src.resize((inner, inner), Image.LANCZOS), ((size - inner) // 2,) * 2)
    return im.convert("RGB")
icon(192).save(A / "icon-192.png", optimize=True); icon(512).save(A / "icon-512.png", optimize=True); icon(180).save(A / "apple-touch-icon.png", optimize=True)
print("icons written to", A)
