"""ビルド時に本文(src/)を検査し、ルール違反を WARNING として返す。

build.py の main() から check_pages() が呼ばれる。検査の内容:
  - メタ情報(title・category・lead)の有無、目次にないカテゴリ、build.py の order にないページ
  - 章立て(h2)がページの種類ごとの決まりどおりか
  - 内部リンクの切れ(ページ・ページ内の見出し)
  - 太字(strong)が1つの段落・項目で3か所を超えていないか
  - 6章「試験・実務でのポイント」が10項目を超えるのに h4 で分けていないか
  - 図のキャプションが「図1」から順に番号が振られているか
  - 表記ゆれ(NOTATION)・古い名称(STALE)・使わない表示(FORBIDDEN)
表記の決まりを増やすときは NOTATION に (誤りのパターン, 正しい表記) を足す。
"""
import posixpath
import re

from diagrams import text_width

# ページの種類ごとの章(h2)。見出しはこの文字列で始まること(後ろに補足の語を付けてもよい)
CHAPTERS = {
    "services": ["1. サービス概要", "2. 主な機能・特徴", "3. ユースケース", "4. 料金の考え方",
                 "5. 関連サービス", "6. 試験・実務でのポイント", "7. まとめ"],
    "terms": ["1. 詳しい説明", "2. 関連する用語", "3. 関連サービス"],
    "usecases": ["1. やりたいこと", "2. 構成を組み立てる", "3. 構成図", "4. 使うサービスと役割", "5. 構築の流れ",
                 "6. ポイント・注意点"],
}

# 表記の統一:(使わない表記の正規表現, 使う表記)
NOTATION = [
    (r"レイテンシ(?!ー)", "レイテンシー"),
    (r"インターフェース", "インターフェイス"),
    (r"サーバ(?!ー|レス)", "サーバー"),
    (r"ユーザ(?!ー)", "ユーザー"),
    (r"オンプレ(?!ミス)", "オンプレミス"),
    (r"オートスケーリング", "Auto Scaling"),
    (r"パラメーター", "パラメータ"),
    (r"プロバイダ(?!ー)", "プロバイダー"),
    (r"ロードバランサ(?!ー)", "ロードバランサー"),
    (r"ルートアカウント", "ルートユーザー"),
    (r"指数バックオフ", "エクスポネンシャルバックオフ"),
    (r"フィルタ(?!ー|リング)", "フィルター"),
    (r"アベイラビリティゾーン", "アベイラビリティーゾーン"),
    (r"フェールオーバー", "フェイルオーバー"),
    (r"セキュリティーグループ", "セキュリティグループ"),
    (r"ブルー/グリーン", "Blue/Green"),
    (r"一つ", "1つ"),
    (r"わかる", "分かる"),
    (r"たとえば", "例えば"),
    (r"全て", "すべて"),
    (r"出来る", "できる"),
    (r"下さい", "ください"),
    (r"[ヶヵカ]月", "か月"),
    (r"[（）]", "半角の ( )"),
    (r"[Ａ-Ｚａ-ｚ０-９]", "半角英数字"),
]

# 古い名称:同じ文に「旧」「以前」「終了」などがあれば、経緯の説明として許す
STALE = [
    ("Enterprise On-Ramp", "Enterprise Support(2027年1月1日に終了)"),
    ("Developerサポート", "Business Support+(2027年1月1日に終了)"),
    ("Business以上のサポートプラン", "Business Support+ 以上のサポートプラン"),
    ("Kinesis Data Firehose", "Amazon Data Firehose"),
    ("AWS Single Sign-On", "IAM Identity Center"),
    ("CloudWatch Events", "Amazon EventBridge"),
    ("Elasticsearch Service", "Amazon OpenSearch Service"),
    ("AWS Chatbot", "Amazon Q Developer in chat applications"),
    ("CodeStar Connections", "CodeConnections"),
]
STALE_OK = re.compile(r"旧|以前|終了|名称が変わ|改名")

# 本文に書かないもの
FORBIDDEN = [
    (r"Notion", "Notionへの言及"),
    (r"一言で言うと", "「一言で言うと」の章(短い説明は lead に書く)"),
    (r"補足[::)]|\(補足|class=\"note\"", "「補足」の表示"),
]

BLOCK_RE = re.compile(r"<(p|li|td|th|dd)\b[^>]*>(.*?)</\1>", re.S)
HEADING_RE = re.compile(r"<(h[23])((?:\s[^>]*)?)>(.*?)</\1>", re.S)
HREF_RE = re.compile(r'href="([^"]+)"')
FIGURE_SRC_RE = re.compile(r'(<figure class="figure" data-diagram>).*?(<figcaption>)', re.S)


def _text_only(body):
    """タグ・インラインSVG・コードを除き、図の記法は表示される文字列だけにした本文(表記の検査用)。"""
    body = FIGURE_SRC_RE.sub(
        lambda m: m.group(1) + " ".join(re.findall(r'"([^"]*)"', m.group(0))) + m.group(2), body)
    body = re.sub(r"<svg\b.*?</svg>", "", body, flags=re.S)
    body = re.sub(r"<(pre|code)\b.*?</\1>", "", body, flags=re.S)
    body = re.sub(r"<[^>]+>", "", body)
    return body


def _line_of(raw, pos):
    return raw.count("\n", 0, pos) + 1


def _anchor_ids(raw):
    """build.py の add_heading_ids と同じ規則で付く見出しの id と、本文中の id 属性。"""
    ids = set(re.findall(r'\bid="([^"]+)"', raw))
    n2 = n3 = 0
    for tag, attrs, _ in HEADING_RE.findall(raw):
        if tag == "h2":
            n2, n3 = n2 + 1, 0
            ids.add(f"c{n2}")
        else:
            n3 += 1
            ids.add(f"c{n2}-{n3}")
    return ids


def check_pages(collections, loaded, extra_pages, out_dir, warnings):
    """loaded: {コレクションのkey: [ページ]}(各ページに raw = メタ情報を除いた本文)。
    extra_pages: {公開パス: raw本文}(links.html など、コレクション以外のページ)。"""
    targets = {}  # 公開パス → 見出しの id の集合
    for col in collections:
        key = col["key"]
        targets[f"{key}/index.html"] = None  # 目次ページ(id は検査しない)
        for p in loaded[key]:
            targets[f"{key}/{p['slug']}.html"] = _anchor_ids(p["raw"])
    targets["index.html"] = None
    for path, raw in extra_pages.items():
        targets[path] = _anchor_ids(raw)

    pages = [(col, p) for col in collections for p in loaded[col["key"]]]
    for col, p in pages:
        key, raw = col["key"], p["raw"]
        where = f"{key}/{p['slug']}"
        _check_meta(col, p, where, warnings)
        _check_chapters(key, raw, where, warnings)
        _check_links(f"{key}/{p['slug']}.html", raw, targets, out_dir, where, warnings)
        _check_style(raw, where, warnings)
        if key == "usecases":
            _check_exercise(raw, where, warnings)
    for path, raw in extra_pages.items():
        _check_links(path, raw, targets, out_dir, path, warnings)
        _check_style(raw, path, warnings)


def _check_meta(col, p, where, warnings):
    if not p["lead"] and not col.get("no_lead"):
        warnings.append(f"{where}: lead がありません")
    if col["categories"] and p["category"] not in col["categories"]:
        warnings.append(f"{where}: カテゴリ「{p['category']}」が build.py の categories にありません")
    if col.get("order") and p["slug"] not in col["order"]:
        warnings.append(f"{where}: build.py の order にありません(一覧の末尾に表示されます)")


def _check_chapters(key, raw, where, warnings):
    expected = CHAPTERS.get(key)
    if not expected:
        return
    found = [re.sub(r"<[^>]+>", "", h).strip() for h in re.findall(r"<h2[^>]*>(.*?)</h2>", raw, re.S)]
    if len(found) != len(expected) or any(not f.startswith(e) for f, e in zip(found, expected)):
        warnings.append(f"{where}: 章立てが決まりと違います(期待: {' / '.join(expected)})")


def _check_links(page_path, raw, targets, out_dir, where, warnings):
    base = posixpath.dirname(page_path)
    for m in HREF_RE.finditer(raw):
        href = m.group(1)
        if re.match(r"[a-z]+:", href) or href.startswith("//"):
            continue  # 外部リンク・mailto など
        path, _, frag = href.partition("#")
        target = posixpath.normpath(posixpath.join(base, path)) if path else page_path
        line = _line_of(raw, m.start())
        if target not in targets:
            if path and (out_dir / target).exists():
                continue  # book/ に直接置いているファイル(アイコンなど)
            warnings.append(f"{where}:{line}: リンク切れ {href}")
        elif frag and targets[target] is not None and frag not in targets[target] and frag != "top":
            warnings.append(f"{where}:{line}: リンク先に見出し #{frag} がありません({href})")


def _check_exercise(raw, where, warnings):
    """運用シナリオの構成演習(2章):各問に正解が1つあるか、図の空欄と問いが対応しているか、図に出す名前が枠に収まるか。"""
    colw = 170.0
    m = re.search(r"^\s*grid\s+([\d.]+)", raw, re.M)
    if m:
        colw = float(m.group(1))
    blanks = {}  # 空欄のノードID → 文字を置ける幅
    for nid, opts in re.findall(r'^\s*node\s+(\S+)\s+\S+\s+\S+\s+blank\b(.*)$', raw, re.M):
        w = re.search(r"\bw=([\d.]+)", opts)
        blanks[nid] = (float(w.group(1)) if w else 1) * colw - 32
    items = re.findall(r'<div class="ex-item"([^>]*)>(.*?)</ul>\s*</div>', raw, re.S)
    if not items:
        warnings.append(f"{where}: 問い(ex-item)がありません")
    used = set()
    for n, (attrs, inner) in enumerate(items, 1):
        choices = re.findall(r"<li\b([^>]*)>", inner)
        if len(choices) < 2 or sum("data-ok" in c for c in choices) != 1:
            warnings.append(f"{where}: {n}問目は、選択肢が2つ以上・正解(data-ok)がちょうど1つになるようにしてください")
        node = re.search(r'data-node="([^"]+)"', attrs)
        if not node:
            continue
        nid = node.group(1)
        used.add(nid)
        if nid not in blanks:
            warnings.append(f"{where}: {n}問目の data-node「{nid}」が図の空欄(blank)にありません")
            continue
        for short in re.findall(r'data-short="([^"]+)"', inner):
            if text_width(short, 14) > blanks[nid]:
                warnings.append(f"{where}: {n}問目の data-short「{short}」が図の枠からはみ出します")
    for nid in blanks.keys() - used:
        warnings.append(f"{where}: 図の空欄「{nid}」に対応する問いがありません")


def _check_style(raw, where, warnings):
    # 太字は1つの段落・項目につき3か所まで
    for m in BLOCK_RE.finditer(raw):
        own = re.split(r"<[uo]l\b", m.group(2))[0]  # 入れ子のリストは、その項目として別に数える
        n = len(re.findall(r"<strong\b", own))
        if n > 3:
            warnings.append(f"{where}:{_line_of(raw, m.start())}: 太字が{n}か所あります(1つの段落・項目につき3か所まで)")

    # 6章のポイントが10項目を超えたら h4 で分ける
    m = re.search(r"<h2>6\. 試験・実務でのポイント</h2>(.*?)</section>", raw, re.S)
    if m and "<h4>" not in m.group(1) and m.group(1).count("<li>") > 10:
        warnings.append(f"{where}: 6章のポイントが{m.group(1).count('<li>')}項目あります。<h4> でテーマごとに分けてください")

    # 図の番号は 1 から順に
    nums = [int(n) for n in re.findall(r"<figcaption>図(\d+)", raw)]
    if nums != list(range(1, len(nums) + 1)):
        warnings.append(f"{where}: 図の番号が順になっていません({', '.join(map(str, nums))})")
    if raw.count("<figcaption>") != len(nums):
        warnings.append(f"{where}: 「図N 説明」の形でないキャプションがあります")

    text = _text_only(raw)
    for pattern, good in NOTATION:
        found = sorted(set(re.findall(pattern, text)))
        if found:
            warnings.append(f"{where}: 表記「{'・'.join(found)}」→「{good}」に統一")
    for sentence in re.split(r"[。\n]", text):
        for old, new in STALE:
            if old in sentence and not STALE_OK.search(sentence):
                warnings.append(f"{where}: 古い名称「{old}」→「{new}」")
    for pattern, label in FORBIDDEN:
        if re.search(pattern, raw):
            warnings.append(f"{where}: {label}は本文に書きません")
