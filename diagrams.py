"""本文中の簡易記法の図をインラインSVGに変換する。

記法(<figure class="figure" data-diagram> と <figcaption> の間に書く):
  grid 170 90                       1マスの幅・高さ(px。省略時 170 90)
  node ID 列 行 スタイル "本文" ["補足行"] [w=横マス数] [h=縦マス数]
        スタイル: box / blue / accent / ok / ng / plain(枠なし)
        本文中の \\n は改行。列・行は小数も可
  edge ID1 ID2 ["ラベル"] [dash] [both] [hv|vh]    矢印(hv/vh は折れ線)
  group 列1 行1 列2 行2 "ラベル" [pad=8] [accent]  点線の囲み
  label 列 行 "テキスト" [cls=dg-s] [anchor=middle] [dy=0]
"""
import html
import re
import shlex

MARGIN = 24
OPTION_RE = re.compile(r"^(w|h|pad|cls|anchor|dy)=\S+$")
STYLE_CLASS = {"box": "dg-box", "blue": "dg-blue", "accent": "dg-accent",
               "ok": "dg-ok", "ng": "dg-ng", "plain": None}

FIGURE_RE = re.compile(
    r'<figure class="figure" data-diagram>\s*(.*?)\s*(<figcaption>.*?</figcaption>)\s*</figure>', re.S)


def text_width(s, size):
    return sum(size if ord(c) > 0x2000 else size * 0.6 for c in s)


def esc(s):
    return html.escape(s, quote=False)


class Diagram:
    def __init__(self, src, uid, where):
        self.colw, self.rowh = 170, 90
        self.nodes, self.edges, self.groups, self.labels = {}, [], [], []
        self.uid, self.where, self.warnings = uid, where, []
        for raw in src.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                tok = shlex.split(line)
            except ValueError as e:
                self.warnings.append(f"{where}: 記法エラー ({e}): {line}")
                continue
            is_opt = [bool(OPTION_RE.match(t)) for t in tok]
            args = [t for t, o in zip(tok[1:], is_opt[1:]) if not o]
            opts = dict(t.split("=", 1) for t, o in zip(tok[1:], is_opt[1:]) if o)
            try:
                getattr(self, "cmd_" + tok[0])(args, opts)
            except (AttributeError, IndexError, ValueError) as e:
                self.warnings.append(f"{where}: 記法エラー ({e}): {line}")

    # --- 記法の各コマンド ---
    def cmd_grid(self, a, o):
        self.colw, self.rowh = float(a[0]), float(a[1])

    def cmd_node(self, a, o):
        nid, col, row, style = a[0], float(a[1]), float(a[2]), a[3]
        main = a[4].split("\\n")
        sub = a[5] if len(a) > 5 else None
        w, h = float(o.get("w", 1)), float(o.get("h", 1))
        base = 52 if (sub or len(main) > 1) else 40
        if sub and len(main) > 1:
            base = 68
        bw = w * self.colw - 20
        bh = base + (h - 1) * self.rowh
        x = MARGIN + col * self.colw + 10
        y = MARGIN + row * self.rowh + (self.rowh - base) / 2
        self.nodes[nid] = dict(x=x, y=y, w=bw, h=bh, style=style, main=main, sub=sub)
        limit = bw - 12
        for t in main:
            if text_width(t, 14) > limit:
                self.warnings.append(f"{self.where}: node {nid} の文字がはみ出します: {t}")
        if sub and text_width(sub, 12) > limit:
            self.warnings.append(f"{self.where}: node {nid} の補足行がはみ出します: {sub}")

    def cmd_edge(self, a, o):
        flags = set(a[2:])
        label = next((t for t in a[2:] if t not in ("dash", "both", "hv", "vh")), None)
        for n in a[:2]:
            if n not in self.nodes:
                self.warnings.append(f"{self.where}: edge の node {n} が未定義です")
                return
        self.edges.append((a[0], a[1], label, flags))

    def cmd_group(self, a, o):
        c1, r1, c2, r2 = map(float, a[:4])
        self.groups.append(dict(c1=c1, r1=r1, c2=c2, r2=r2, label=a[4] if len(a) > 4 else "",
                                pad=float(o.get("pad", 8)), accent="accent" in a[5:]))

    def cmd_label(self, a, o):
        self.labels.append(dict(col=float(a[0]), row=float(a[1]), text=a[2],
                                cls=o.get("cls", "dg-s"), anchor=o.get("anchor", "middle"),
                                dy=float(o.get("dy", 0))))

    # --- 描画 ---
    @staticmethod
    def clip(n, tx, ty):
        """ノード中心から(tx,ty)方向へ伸ばした線と枠の交点。"""
        cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        hw, hh = n["w"] / 2, n["h"] / 2
        t = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
        return cx + dx * t, cy + dy * t

    def render(self, caption):
        out, maxx, maxy = [], 0.0, 0.0

        def grow(x, y):
            nonlocal maxx, maxy
            maxx, maxy = max(maxx, x), max(maxy, y)

        boxh = 52
        for g in sorted(self.groups, key=lambda g: -(g["c2"] - g["c1"]) * (g["r2"] - g["r1"] + 1)):
            p = g["pad"]
            left = MARGIN + g["c1"] * self.colw + 10 - p
            right = MARGIN + (g["c2"] + 1) * self.colw - 10 + p
            top = MARGIN + g["r1"] * self.rowh + (self.rowh - boxh) / 2 - p - 18
            bottom = MARGIN + (g["r2"] + 1) * self.rowh - (self.rowh - boxh) / 2 + p
            cls = "dg-group dg-group-a" if g["accent"] else "dg-group"
            out.append(f'<rect x="{left:.0f}" y="{top:.0f}" width="{right - left:.0f}" '
                       f'height="{bottom - top:.0f}" rx="10" class="{cls}"/>')
            if g["label"]:
                out.append(f'<text x="{left + 10:.0f}" y="{top + 15:.0f}" class="dg-s">{esc(g["label"])}</text>')
            grow(right, bottom)

        for n in self.nodes.values():
            cls = STYLE_CLASS.get(n["style"], "dg-box")
            if cls:
                out.append(f'<rect x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["w"]:.0f}" '
                           f'height="{n["h"]:.0f}" rx="8" class="{cls}"/>')
            lines = [(t, "dg-tb" if n["style"] == "accent" else "dg-t", 18) for t in n["main"]]
            if n["sub"]:
                lines.append((n["sub"], "dg-s", 17))
            total = sum(lh for _, _, lh in lines)
            cx = n["x"] + n["w"] / 2
            y = n["y"] + n["h"] / 2 - total / 2 + 13
            for t, c, lh in lines:
                out.append(f'<text x="{cx:.0f}" y="{y:.0f}" text-anchor="middle" class="{c}">{esc(t)}</text>')
                y += lh
            grow(n["x"] + n["w"], n["y"] + n["h"])

        mid = f"dg{self.uid}"
        for a, b, label, flags in self.edges:
            na, nb = self.nodes[a], self.nodes[b]
            acx, acy = na["x"] + na["w"] / 2, na["y"] + na["h"] / 2
            bcx, bcy = nb["x"] + nb["w"] / 2, nb["y"] + nb["h"] / 2
            if "hv" in flags:
                sx = acx + (na["w"] / 2 if bcx > acx else -na["w"] / 2)
                ey = bcy + (-nb["h"] / 2 if bcy > acy else nb["h"] / 2)
                pts = [(sx, acy), (bcx, acy), (bcx, ey)]
            elif "vh" in flags:
                sy = acy + (na["h"] / 2 if bcy > acy else -na["h"] / 2)
                ex = bcx + (-nb["w"] / 2 if bcx > acx else nb["w"] / 2)
                pts = [(acx, sy), (acx, bcy), (ex, bcy)]
            else:
                pts = [self.clip(na, bcx, bcy), self.clip(nb, acx, acy)]
            d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
            attrs = f'marker-end="url(#{mid})"'
            if "both" in flags:
                attrs += f' marker-start="url(#{mid})"'
            cls = "dg-line dg-dash" if "dash" in flags else "dg-line"
            out.append(f'<path d="{d}" class="{cls}" {attrs}/>')
            if label:
                segs = list(zip(pts, pts[1:]))
                (x1, y1), (x2, y2) = max(segs, key=lambda s: abs(s[1][0] - s[0][0]) + abs(s[1][1] - s[0][1]))
                lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 + 4
                out.append(f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="middle" class="dg-s dg-halo">{esc(label)}</text>')

        for l in self.labels:
            x = MARGIN + (l["col"] + 0.5) * self.colw
            y = MARGIN + (l["row"] + 0.5) * self.rowh + 5 + l["dy"]
            out.append(f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{l["anchor"]}" class="{l["cls"]}">{esc(l["text"])}</text>')
            grow(x + text_width(l["text"], 12) / (2 if l["anchor"] == "middle" else 1), y + 6)

        W, H = maxx + MARGIN, maxy + MARGIN
        aria = html.escape(re.sub(r"<[^>]+>", "", caption).strip())
        head = (f'<svg viewBox="0 0 {W:.0f} {H:.0f}" style="max-width:{W:.0f}px;min-width:{min(W, 520):.0f}px" '
                f'role="img" aria-label="{aria}">'
                f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="dg-head"/></marker></defs>')
        return head + "\n" + "\n".join(out) + "\n</svg>"


def render_figures(body, where, warnings):
    """本文中の data-diagram 図をすべてSVGに置き換える。"""
    count = 0

    def repl(m):
        nonlocal count
        count += 1
        caption = m.group(2)
        d = Diagram(m.group(1), re.sub(r"\W", "-", where) + f"-{count}", where)
        warnings.extend(d.warnings)
        return (f'<figure class="figure">\n<div class="fig-scroll">\n{d.render(caption)}\n</div>\n'
                f'{caption}\n</figure>')

    return FIGURE_RE.sub(repl, body)
