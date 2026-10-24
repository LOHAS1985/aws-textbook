# ホーム画面用アイコンを生成する(紺の背景に本のマークと「AWS 教科書」)
from PIL import Image, ImageDraw, ImageFont
import sys
out = sys.argv[1]
S = 1024
NAVY, ORANGE, WHITE, PAGE = (31, 41, 55), (240, 151, 74), (255, 255, 255), (230, 236, 242)
F_EN = "C:/Windows/Fonts/NotoSansJP-Black.otf"
F_JA = "C:/Windows/Fonts/NotoSansJP-Bold.otf"

def draw(full_bleed):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if full_bleed:
        d.rectangle([0, 0, S, S], fill=NAVY)
    else:
        r = 220  # 角丸(古いPillowには rounded_rectangle がない)
        d.rectangle([r, 0, S - r, S], fill=NAVY)
        d.rectangle([0, r, S, S - r], fill=NAVY)
        for x, y in ((0, 0), (S - 2 * r, 0), (0, S - 2 * r), (S - 2 * r, S - 2 * r)):
            d.ellipse([x, y, x + 2 * r, y + 2 * r], fill=NAVY)
    # 開いた本(セーフゾーン=中央80%に収める)
    cx, top, bot, w = S // 2, 250, 520, 290
    d.polygon([(cx, top + 30), (cx - w, top), (cx - w, bot), (cx, bot + 30)], fill=PAGE)
    d.polygon([(cx, top + 30), (cx + w, top), (cx + w, bot), (cx, bot + 30)], fill=WHITE)
    d.line([(cx, top + 30), (cx, bot + 30)], fill=NAVY, width=10)
    for i in range(4):
        y = top + 75 + i * 50
        d.line([(cx - w + 50, y), (cx - 50, y + 22)], fill=(170, 180, 192), width=12)
        d.line([(cx + 50, y + 22), (cx + w - 50, y)], fill=(170, 180, 192), width=12)
    # しおり
    d.polygon([(cx + 150, top - 8), (cx + 205, top - 15), (cx + 205, top + 110), (cx + 178, top + 85), (cx + 150, top + 115)], fill=ORANGE)
    # 文字
    fe = ImageFont.truetype(F_EN, 190)
    d.text((cx, 650), "AWS", font=fe, fill=ORANGE, anchor="mm")
    fj = ImageFont.truetype(F_JA, 92)
    d.text((cx, 790), "教科書", font=fj, fill=WHITE, anchor="mm")
    return im

base = draw(False)
mask = draw(True)
for size in (192, 512):
    base.resize((size, size), Image.LANCZOS).save(f"{out}/icon-{size}.png")
mask.resize((512, 512), Image.LANCZOS).save(f"{out}/icon-maskable-512.png")
mask.convert("RGB").resize((180, 180), Image.LANCZOS).save(f"{out}/apple-touch-icon.png")
base.resize((32, 32), Image.LANCZOS).save(f"{out}/favicon-32.png")
