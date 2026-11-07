# 主要ページを PC幅・スマホ幅で撮影し、前回の撮影との差を出す(表示の崩れに気づくための確認)
# 使い方:
#   1. 手元で book/ を配信する: python -m http.server 8000 -d book
#   2. python tools/visual_check.py                                  (既定: http://localhost:8000/)
#      python tools/visual_check.py --base https://lohas1985.github.io/aws-textbook/   (公開版)
# 撮影した画像は tools/.visual/ に保存する。2回目以降は、前回の画像と比べて変わった画素の割合を出す。
# 閾値を超えたページがあれば終了コード 1。Playwright か Pillow が無い時は入れ方を出して終了コード 2。
import argparse
import io
import sys
from pathlib import Path

PAGES = [
    "index.html",                      # トップ
    "services/index.html",             # サービス一覧
    "services/s3.html",                # サービスの1ページ
    "usecases/auto-scaling-web.html",  # 運用シナリオ(構成演習)
    "exams/dea-c01/questions.html",    # 問題集
]
VIEWPORTS = {"pc": {"width": 1280, "height": 800}, "sp": {"width": 375, "height": 812}}
OUT = Path(__file__).parent / ".visual"
PIXEL_DIFF = 16  # この差(0〜255)より大きい画素だけを「変わった」とみなす(圧縮や描画のゆらぎを除く)


def changed_ratio(old_png, new_png):
    """2枚の画像で変わった画素の割合(0〜1)。大きさが違えば全体が変わったとみなして 1 を返す。"""
    from PIL import Image, ImageChops
    old = Image.open(io.BytesIO(old_png)).convert("RGB")
    new = Image.open(io.BytesIO(new_png)).convert("RGB")
    if old.size != new.size:
        return 1.0
    diff = ImageChops.difference(old, new).convert("L").point(lambda v: 255 if v > PIXEL_DIFF else 0)
    return diff.histogram()[255] / (old.size[0] * old.size[1])


def main():
    parser = argparse.ArgumentParser(description="主要ページの表示を撮影し、前回との差を出す")
    parser.add_argument("--base", default="http://localhost:8000/", help="book/ を開いているURL")
    parser.add_argument("--threshold", type=float, default=0.005, help="変わった画素の割合の閾値(既定 0.5%%)")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright が入っていません。次の2つを実行してください:")
        print("  pip install playwright")
        print("  python -m playwright install chromium")
        return 2
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("Pillow が入っていません。次を実行してください: pip install pillow")
        return 2

    OUT.mkdir(exist_ok=True)
    base = args.base if args.base.endswith("/") else args.base + "/"
    rows = []  # (状態, 差の割合, 名前, URL)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for label, size in VIEWPORTS.items():
                context = browser.new_context(viewport=size, color_scheme="light", reduced_motion="reduce")
                page = context.new_page()
                for path in PAGES:
                    url = base + path
                    name = f"{label}-{path[:-len('.html')].replace('/', '_')}"
                    file = OUT / f"{name}.png"
                    try:
                        page.goto(url, wait_until="networkidle")
                        png = page.screenshot(full_page=True)
                    except Exception as error:  # 開けなかったページは報告して続ける
                        rows.append(("失敗", None, name, f"{url} ({error.__class__.__name__})"))
                        continue
                    old = file.read_bytes() if file.exists() else None
                    file.write_bytes(png)  # 比べ終わったら今回の画像で置き換える(次回の「前回」になる)
                    if old is None:
                        rows.append(("初回", None, name, url))
                    else:
                        ratio = changed_ratio(old, png)
                        rows.append(("変化あり" if ratio > args.threshold else "変化なし", ratio, name, url))
                context.close()
        finally:
            browser.close()

    over = [r for r in rows if r[0] in ("変化あり", "失敗")]
    for state, ratio, name, url in rows:
        share = "" if ratio is None else f" {ratio * 100:6.2f}%"
        print(f"{state:<6}{share}  {name}  {url}")
    print(f"撮影先: {OUT}")
    if over:
        print(f"確認が必要: {len(over)}件(閾値 {args.threshold * 100:.2f}% を超えた、または開けなかったページ)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
