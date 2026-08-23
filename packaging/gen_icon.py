"""Gera os ícones do PowerZap (PNG e ICO) usando Pillow."""
from PIL import Image, ImageDraw, ImageFont

SIZE = 512
BG_TOP = (46, 125, 50)
BG_BOTTOM = (27, 94, 32)
ACCENT = (200, 255, 212)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

for y in range(SIZE):
    t = y / SIZE
    r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
    g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
    b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
    draw.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))

radius = 110
mask = Image.new("L", (SIZE, SIZE), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE, SIZE], radius=radius, fill=255)
img.putalpha(mask)
draw = ImageDraw.Draw(img)

cx, cy = SIZE / 2, SIZE / 2
bubble_r = 150
draw.rounded_rectangle(
    [cx - bubble_r, cy - bubble_r + 10, cx + bubble_r, cy + bubble_r],
    radius=90, fill=(255, 255, 255, 235),
)
draw.polygon(
    [(cx - 60, cy + bubble_r - 25), (cx - 95, cy + bubble_r + 55),
     (cx - 5, cy + bubble_r - 15)],
    fill=(255, 255, 255, 235),
)

font = None
for candidate in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "arialbd.ttf",
    "arial.ttf",
]:
    try:
        font = ImageFont.truetype(candidate, 170)
        break
    except OSError:
        continue
if font is None:
    font = ImageFont.load_default()

bbox = draw.textbbox((0, 0), "PZ", font=font)
w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1] - 8), "PZ",
          font=font, fill=(27, 94, 32, 255))

img.save("assets/icon.png")

ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.resize((256, 256), Image.LANCZOS).save("assets/icon.ico", sizes=ico_sizes)
print("Ícones gerados em assets/")
