"""src/ 以下の本文から book/ 以下の教科書HTMLを生成する。

使い方: python build.py

コレクション(サービス・用語・ユースケース)ごとに src/{コレクション}/*.html を置く。
本文ファイルの先頭には次のメタ情報を書く。
    <!-- title: ページ名 -->
    <!-- category: カテゴリ名 -->
    <!-- lead: 一言説明 -->
図は diagrams.py の記法で書くとSVGに変換される。
リンク集(book/links.html)は、src/links.html の本文と src/links.json(サービスごとの公式ページ)から作る。
"""
import html
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from diagrams import render_figures

ROOT = Path(__file__).parent
SRC = ROOT / "src"
OUT = ROOT / "book"
SITE_TITLE = "AWS教科書"

# key がフォルダ名(src/{key}/ → book/{key}/)。
# categories は目次の並び順、order はページの並び順(= 前へ/次へ の順番)。
# 一覧にないカテゴリ・ページは末尾に追加される。
COLLECTIONS = [
    {
        "key": "services",
        "label": "サービス",
        "desc": "AWSの各サービスの仕組み・機能・料金・ポイント",
        "categories": [
            "コンピューティング", "コンテナ", "ストレージ", "データベース",
            "ネットワークとコンテンツ配信", "セキュリティ、アイデンティティ、コンプライアンス",
            "マネジメントとガバナンス", "クラウド財務管理", "アプリケーション統合", "デベロッパーツール",
            "フレームワーク", "ライブラリ", "分析", "機械学習と人工知能", "移行と転送", "ビジネスアプリケーション",
        ],
        "category_desc": {
            "コンピューティング": "仮想サーバー・関数など、プログラムを動かす基盤",
            "コンテナ": "コンテナの実行・オーケストレーション・イメージの保管",
            "ストレージ": "オブジェクト・ブロック・ファイルの保存とバックアップ",
            "データベース": "リレーショナル・NoSQL・インメモリのデータベース",
            "ネットワークとコンテンツ配信": "VPC・オンプレミスとの接続・DNS・負荷分散・配信",
            "セキュリティ、アイデンティティ、コンプライアンス": "認証・権限・暗号化・証明書・脅威の検出",
            "マネジメントとガバナンス": "監視・ログ・構成管理・自動化・複数アカウントの統制",
            "クラウド財務管理": "料金の分析・詳細な請求データ・割引の購入",
            "アプリケーション統合": "キュー・通知・イベント・ワークフローでサービスをつなぐ",
            "デベロッパーツール": "ビルド・デプロイ・CI/CD・トレース・開発環境",
            "フレームワーク": "サーバーレスアプリの定義・AWSを操作するプログラムの開発",
            "ライブラリ": "アプリに組み込んで使う暗号化などのライブラリ",
            "分析": "ログやストリームデータの検索・分析・配送",
            "機械学習と人工知能": "生成AIのモデルをアプリから使う",
            "移行と転送": "オンプレミスなどからのデータの移行",
            "ビジネスアプリケーション": "メール送信などの業務向けサービス",
        },
        # カテゴリの色(AWS公式アイコンの配色に合わせる)
        "category_colors": {
            "コンピューティング": "#ED7100", "コンテナ": "#ED7100", "ストレージ": "#7AA116",
            "データベース": "#C925D1", "ネットワークとコンテンツ配信": "#8C4FFF",
            "セキュリティ、アイデンティティ、コンプライアンス": "#DD344C",
            "マネジメントとガバナンス": "#E7157B", "アプリケーション統合": "#E7157B",
            "デベロッパーツール": "#C925D1", "フレームワーク": "#C925D1", "ライブラリ": "#DD344C",
            "分析": "#8C4FFF", "移行と転送": "#01A88D", "ビジネスアプリケーション": "#DD344C",
            "クラウド財務管理": "#7AA116", "機械学習と人工知能": "#01A88D",
        },
        "compact": True,
        "search": "サービス名・キーワードで絞り込み(例: VPN、ログ、コンテナ)",
        "order": [
            "ec2", "auto-scaling", "image-builder", "lambda", "elastic-beanstalk",
            "ecs", "eks", "ecr", "copilot",
            "s3", "ebs", "efs", "fsx", "backup", "storage-gateway",
            "rds", "aurora", "dynamodb", "elasticache", "memorydb",
            "vpc", "ipam", "transit-gateway", "site-to-site-vpn", "client-vpn", "direct-connect",
            "route53", "dns-firewall", "application-recovery-controller",
            "elb", "cloudfront", "global-accelerator", "api-gateway",
            "iam", "identity-center", "sts", "organizations", "directory-service", "cognito", "kms",
            "secrets-manager", "acm", "private-ca", "guardduty", "inspector", "macie", "security-hub",
            "waf", "shield", "network-firewall", "security-agent",
            "cloudwatch", "cloudtrail", "config", "systems-manager", "cloudformation", "cdk",
            "control-tower", "trusted-advisor", "health-dashboard", "compute-optimizer", "service-catalog", "ram",
            "managed-grafana", "managed-prometheus", "devops-agent",
            "cost-explorer", "cost-and-usage-reports", "savings-plans",
            "sqs", "sns", "eventbridge", "step-functions", "appsync",
            "codepipeline", "codebuild", "codedeploy", "codeartifact", "xray", "cloudshell", "amplify", "kiro",
            "sam", "sdk", "database-encryption-sdk",
            "athena", "kinesis", "data-firehose", "opensearch", "bedrock", "datasync", "ses",
        ],
    },
    {
        "key": "terms",
        "label": "用語",
        "desc": "AWSを学ぶうえで押さえておきたい用語の解説",
        "categories": ["AWSの基礎", "ネットワーク", "セキュリティ・認証", "ストレージ", "設計・運用"],
        "search": "用語・キーワードで絞り込み(例: IP、暗号化、DNS)",
        "order": [
            "region-az", "arn", "service-quotas",
            "dns", "dns-record-types", "cidr", "route-table", "nacl-security-group", "vpc-flow-logs",
            "eni-elastic-ip", "vpc-endpoint", "vpc-peering",
            "inbound-traffic", "outbound-traffic",
            "iam-policy-evaluation", "encryption", "oidc", "spf",
            "storage-types",
            "high-availability-scaling", "deploy-strategies", "dr-strategies", "circuit-breaker",
        ],
    },
    {
        "key": "usecases",
        "label": "ユースケース",
        "desc": "やりたいこと別の構成例と、使うサービスの組み合わせ",
        "categories": [
            "監視・ログ・自動修復", "信頼性・事業継続", "デプロイ・自動化",
            "セキュリティ・コンプライアンス", "ネットワーク・コンテンツ配信",
        ],
        "search": "やりたいこと・サービス名で絞り込み(例: バックアップ、パッチ)",
        "category_desc": {
            "監視・ログ・自動修復": "メトリクス・ログ・トレースで異常を見つけ、通知や自動修復・性能の改善につなげる",
            "信頼性・事業継続": "スケーリング・高可用性・バックアップ・災害対策",
            "デプロイ・自動化": "イメージの作成・IaCの安全な更新・構成管理・安全なリリース・定時の自動化",
            "セキュリティ・コンプライアンス": "権限・暗号化・ガードレール・脅威と脆弱性への対応・Webの保護",
            "ネットワーク・コンテンツ配信": "VPCの設計と接続・DNS・通信の制限・リモートアクセス・配信・トラブル調査",
        },
        "order": [
            "ec2-memory-monitoring", "log-error-alert", "smart-alarms", "ec2-auto-recovery",
            "health-event-response", "centralized-logging", "container-monitoring", "distributed-tracing",
            "ebs-performance", "rds-performance",
            "auto-scaling-web", "sqs-decoupling", "cache-read-offload", "rds-high-availability",
            "az-failure-isolation", "dynamodb-scaling-recovery", "rds-point-in-time-restore", "s3-data-protection",
            "backup-cross-region", "multi-region-failover",
            "ssm-fleet-configuration", "patch-management", "golden-ami-pipeline", "cloudformation-safe-update",
            "cloudformation-drift", "multi-account-stacksets", "ec2-blue-green-pipeline", "ecs-safe-deploy",
            "lambda-canary-release", "scheduled-start-stop",
            "identity-center-sso", "cross-account-access", "access-denied-troubleshooting", "org-guardrails",
            "config-auto-remediation", "secrets-rotation", "s3-encryption-audit", "vulnerability-management",
            "guardduty-auto-response", "waf-web-protection",
            "vpc-ip-planning", "private-subnet-endpoints", "bastionless-access", "egress-filtering",
            "hybrid-multi-vpc", "hybrid-dns-resolver", "remote-access-vpn", "route53-traffic-routing",
            "static-site-cloudfront", "network-troubleshooting",
        ],
    },
]

# SOA-C03の出題分野(試験ガイドより)。ユースケースのカテゴリと同じ順番で対応させる。
EXAM_DOMAINS = [
    ("モニタリング、ログ記録、分析、修復、パフォーマンスの最適化", 22),
    ("信頼性と事業の継続性", 22),
    ("デプロイ、プロビジョニング、オートメーション", 22),
    ("セキュリティとコンプライアンス", 16),
    ("ネットワークとコンテンツ配信", 18),
]

TOC_MIN_H3 = 5  # 小見出し(h3)がこの数以上あるページにだけページ内目次を付ける
STACK_MIN_COLS = 4  # この列数以上の表は、スマホで行ごとのカード表示にする

META_RE = re.compile(r"<!--\s*(title|category|lead):\s*(.*?)\s*-->\s*")


def git_updated():
    """src/ 以下の各ファイルの最終更新(UNIX時刻)。未コミットの変更があるファイルは現在時刻にする。"""
    times = {}
    try:
        log = subprocess.run(["git", "log", "--format=@%ct", "--name-only", "--", "src"], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8", check=True).stdout
        status = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return times
    t = 0
    for line in log.splitlines():
        if line.startswith("@"):
            t = int(line[1:])
        elif line and line not in times:
            times[line] = t
    now = int(time.time())
    for line in status.splitlines():
        times[line[3:].strip().strip('"')] = now
    return times


def load_pages(col, warnings, updated):
    pages = []
    src_dir = SRC / col["key"]
    for path in sorted(src_dir.glob("*.html")) if src_dir.exists() else []:
        if path.name.startswith("_"):
            continue
        text = path.read_text(encoding="utf-8")
        meta = dict(META_RE.findall(text))
        body = META_RE.sub("", text).strip()
        slug = path.stem
        where = f"{col['key']}/{slug}"
        if "title" not in meta:
            warnings.append(f"{where}: title がありません")
        pages.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "category": meta.get("category", "その他"),
            "lead": meta.get("lead", ""),
            "body": render_figures(body, where, warnings),
            "updated": updated.get(f"src/{col['key']}/{path.name}", int(time.time())),
        })
    order = {s: i for i, s in enumerate(col["order"])}
    pages.sort(key=lambda p: (order.get(p["slug"], len(order)), p["title"]))
    return pages


# 被リンクの一覧を付けるページ:(リンク先のコレクション, リンク元のコレクション, 見出し)
BACKLINKS = [
    ("services", ["usecases"], "このサービスが登場するユースケース"),
    ("terms", ["services", "usecases"], "この用語が出てくるページ"),
]


def add_backlinks(loaded):
    """サービス・用語のページの末尾に、そのページへリンクしている他のコレクションのページの一覧を付ける。"""
    labels = {c["key"]: c["label"] for c in COLLECTIONS}
    for target, sources, heading in BACKLINKS:
        for p in loaded.get(target, []):
            href = f'href="../{target}/{p["slug"]}.html'
            refs = [(key, q) for key in sources for q in loaded.get(key, []) if href in q["body"]]
            if not refs:
                continue
            items = "".join(
                f'<li><a href="../{key}/{q["slug"]}.html"><span class="title">{html.escape(q["title"])}</span>'
                + (f'<span class="kind">{labels[key]}</span>' if len(sources) > 1 else "")
                + (f'<span class="desc">{q["lead"]}</span>' if q["lead"] else "") + "</a></li>\n"
                for key, q in refs)
            p["body"] += (f'\n<section class="chapter backlinks">\n<h2>{heading}</h2>\n'
                          f'<ul class="backlink-list">\n{items}</ul>\n</section>\n')


def grouped(col, pages):
    cats = list(col["categories"])
    for p in pages:
        if p["category"] not in cats:
            cats.append(p["category"])
    return [(c, [p for p in pages if p["category"] == c]) for c in cats
            if any(p["category"] == c for p in pages)]


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def head(title, prefix, description=""):
    desc = (f'<meta name="description" content="{html.escape(plain(description))}">\n'
            if description else "")
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{desc}<link rel="stylesheet" href="{prefix}css/style.css">
<link rel="icon" type="image/png" href="{prefix}icons/favicon-32.png">
<link rel="apple-touch-icon" href="{prefix}icons/apple-touch-icon.png">
<link rel="manifest" href="{prefix}manifest.webmanifest">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1d2127" media="(prefers-color-scheme: dark)">
</head>
<body>
"""


HEADING_RE = re.compile(r"<(h[23])((?:\s[^>]*)?)>(.*?)</\1>", re.S)


def add_heading_ids(body):
    """h2・h3 に id とアンカーリンクを付け、目次用に (レベル, id, 見出し文字列) の一覧を返す。"""
    items, n2, n3 = [], 0, 0

    def sub(m):
        nonlocal n2, n3
        tag, attrs, inner = m.groups()
        if tag == "h2":
            n2, n3 = n2 + 1, 0
            hid = f"c{n2}"
        else:
            n3 += 1
            hid = f"c{n2}-{n3}"
        found = re.search(r'\bid="([^"]+)"', attrs)
        if found:
            hid = found.group(1)
        else:
            attrs += f' id="{hid}"'
        items.append((tag, hid, plain(inner).strip()))
        return (f'<{tag}{attrs}>{inner}<a class="anchor" href="#{hid}" '
                f'aria-label="この見出しへのリンク">#</a></{tag}>')
    return HEADING_RE.sub(sub, body), items


def page_toc(items):
    if sum(1 for tag, _, _ in items if tag == "h3") < TOC_MIN_H3:
        return ""
    chapters = []  # [(h2の項目, [h3の項目, ...]), ...]
    for item in items:
        if item[0] == "h2" or not chapters:
            chapters.append((item, []))
        else:
            chapters[-1][1].append(item)

    def link(item):
        return f'<a href="#{item[1]}">{html.escape(item[2])}</a>'
    out = ['<nav class="page-toc" aria-label="ページ内目次">\n<details>\n'
           f'<summary>このページの内容({len(items)}項目)</summary>\n<ol>\n']
    for h2, subs in chapters:
        sub_list = "".join(f"<li>{link(s)}</li>" for s in subs)
        out.append(f"<li>{link(h2)}" + (f"<ul>{sub_list}</ul>" if subs else "") + "</li>\n")
    out.append("</ol>\n</details>\n</nav>\n")
    return "".join(out)


def stack_tables(body):
    """列の多い表に class="stack" と各セルの data-label を付ける(スマホでカード表示にするため)。"""
    def sub(m):
        attrs, inner = m.groups()
        rows = re.findall(r"<tr>.*?</tr>", inner, re.S)
        if not rows or "<th" not in rows[0]:
            return m.group(0)
        labels = [plain(h).strip() for h in re.findall(r"<th[^>]*>(.*?)</th>", rows[0], re.S)]
        if len(labels) < STACK_MIN_COLS or "class=" in attrs or "span=" in inner:
            return m.group(0)

        def label_row(r):
            i = -1

            def cell(c):
                nonlocal i
                i += 1
                lab = labels[i] if i < len(labels) else ""
                return f'<td data-label="{html.escape(lab)}">'
            return re.sub(r"<td>", cell, r.group(0))
        inner = re.sub(r"<tr>.*?</tr>", label_row, inner, flags=re.S)
        return f'<table class="stack"{attrs}>{inner}</table>'
    return re.sub(r"<table((?:\s[^>]*)?)>(.*?)</table>", sub, body, flags=re.S)


ICON_DIR = OUT / "icons" / "services"  # AWS公式アイコン(Architecture Icons)をサービスのslug名で置く


def service_icon(slug, prefix, size):
    """サービスのアイコン(なければ空文字)。名前と並べて表示するので alt は空にする。"""
    if not (ICON_DIR / f"{slug}.svg").exists():
        return ""
    return (f'<img class="svc-icon" src="{prefix}icons/services/{slug}.svg" alt="" '
            f'width="{size}" height="{size}" loading="lazy">')


def fmt_date(ts):
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def header(prefix, current=None):
    cur = ' class="current"'
    links = "".join(
        f'<a href="{prefix}{c["key"]}/index.html"{cur if c["key"] == current else ""}>'
        f'{c["label"]}</a>' for c in COLLECTIONS)
    links += f'<a href="{prefix}links.html"{cur if current == "links" else ""}>リンク集</a>'
    return f"""<header class="site-header" id="top">
  <div class="inner">
    <a class="site-title" href="{prefix}index.html">{SITE_TITLE}</a>
    <nav class="site-nav">{links}</nav>
  </div>
</header>
"""


TAIL = "</body>\n</html>\n"
TO_TOP = '<a class="to-top" href="#top" aria-label="ページの先頭へ">↑</a>\n'


def pager(prev, nxt):
    def link(p, cls, label):
        if p is None:
            return f'<span class="{cls} empty"></span>'
        return (f'<a class="{cls}" href="{p["slug"]}.html">'
                f'<span class="label">{label}</span>{html.escape(p["title"])}</a>')
    return ('<nav class="pager">\n'
            f'  {link(prev, "prev", "← 前へ")}\n'
            '  <a class="toc" href="index.html">目次へ戻る</a>\n'
            f'  {link(nxt, "next", "次へ →")}\n'
            '</nav>\n')


def render_page(col, pages, i):
    p = pages[i]
    prev = pages[i - 1] if i > 0 else None
    nxt = pages[i + 1] if i + 1 < len(pages) else None
    cat_no = [c for c, _ in grouped(col, pages)].index(p["category"]) + 1
    body, items = add_heading_ids(stack_tables(p["body"]))
    icon = service_icon(p["slug"], "../", 56) if col["key"] == "services" else ""
    return (head(f"{p['title']} | {SITE_TITLE}", "../", p["lead"])
            + header("../", col["key"])
            + f'<main>\n<div class="page-head hero"{cat_style(col, p["category"])}>\n'
            + (f'  <div class="hero-icon">{icon}</div>\n' if icon else "")
            + '  <div class="hero-text">\n'
            + f'  <a class="category" href="index.html#cat{cat_no}">{html.escape(p["category"])}</a>\n'
            + f'  <h1>{html.escape(p["title"])}</h1>\n'
            + (f'  <p class="lead">{p["lead"]}</p>\n' if p["lead"] else "")
            + f'  <p class="updated">最終更新:<time datetime="{fmt_date(p["updated"])}">'
            + f'{fmt_date(p["updated"])}</time></p>\n'
            + "  </div>\n</div>\n" + page_toc(items) + body + "\n" + pager(prev, nxt) + "</main>\n" + TO_TOP + TAIL)


def cat_style(col, category):
    """カテゴリの色を CSS変数 --cat として渡す属性(色が決まっていなければ空)。"""
    color = col.get("category_colors", {}).get(category)
    return f' style="--cat:{color}"' if color else ""


def render_collection_index(col, pages):
    parts = [head(f"{col['label']} | {SITE_TITLE}", "../", col["desc"]), header("../", col["key"]), "<main>\n",
             f'<div class="page-head"><h1>{col["label"]}</h1><p class="lead">{col["desc"]}</p></div>\n']
    if not pages:
        parts.append('<p class="empty-state">準備中です。</p>\n')
    groups = grouped(col, pages)
    if col.get("search") and pages:
        parts.append('<div class="toc-search">\n'
                     f'  <input type="search" id="toc-q" placeholder="{html.escape(col["search"])}"'
                     ' aria-label="絞り込み" autocomplete="off">\n'
                     '  <span class="toc-hits" id="toc-hits"></span>\n</div>\n')
    descs = col.get("category_desc", {})
    compact = col.get("compact")
    if compact:
        parts.append('<div class="svc-columns">\n')
    for i, (category, items) in enumerate(groups, 1):
        if compact:
            # カテゴリごとのカード(折りたたみ可)。説明文はカテゴリ名にマウスを重ねたときだけ出す
            tip = html.escape(category + (":" + descs[category] if category in descs else ""))
            parts.append(f'<section class="toc-category svc-card" id="cat{i}"{cat_style(col, category)}>\n'
                         f'<details open>\n<summary title="{tip}"><h2><span class="cat-name">'
                         f'{html.escape(category.split("、")[0])}</span>'
                         f'<span class="count">{len(items)}</span></h2></summary>\n<ul class="svc-list">\n')
        else:
            parts.append(f'<section class="toc-category" id="cat{i}">\n<h2>{html.escape(category)} '
                         f'<span class="count">({len(items)})</span></h2>\n')
            if category in descs:
                parts.append(f'<p class="cat-desc">{html.escape(descs[category])}</p>\n')
            parts.append('<ul class="card-list">\n')
        for p in items:
            # 一覧には表示しない lead・カテゴリも検索対象に含める
            keys = " ".join([p["title"], p["slug"], category, re.sub(r"<[^>]+>", "", p["lead"])])
            if compact:
                tip = html.escape(p["title"] + (":" + plain(p["lead"]) if p["lead"] else ""))
                inner = (f'{service_icon(p["slug"], "../", 28)}'
                         f'<span class="name">{html.escape(p["title"])}</span><span class="go" aria-hidden="true">›</span>')
                parts.append(f'  <li data-keys="{html.escape(keys.lower())}"><a href="{p["slug"]}.html" '
                             f'title="{tip}">{inner}</a></li>\n')
            else:
                inner = (f'<span class="name">{html.escape(p["title"])}</span>'
                         f'<span class="desc">{p["lead"]}</span>')
                parts.append(f'  <li data-keys="{html.escape(keys.lower())}"><a href="{p["slug"]}.html">{inner}</a></li>\n')
        parts.append("</ul>\n</details>\n</section>\n" if compact else "</ul>\n</section>\n")
    if compact:
        parts.append("</div>\n")
    if col.get("search") and pages:
        parts.append('<p class="empty-state" id="toc-none" hidden>該当するページがありません。</p>\n'
                     + SEARCH_SCRIPT)
    parts += ["</main>\n", TAIL]
    return "".join(parts)


# 目次の絞り込み(スペース区切りのAND検索。該当なしのカテゴリは隠し、件数を更新する)
SEARCH_SCRIPT = """<script>
(function () {
  var q = document.getElementById("toc-q");
  var hits = document.getElementById("toc-hits");
  var none = document.getElementById("toc-none");
  var sections = document.querySelectorAll(".toc-category");
  var total = document.querySelectorAll(".toc-category li").length;
  function apply() {
    var words = q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
    var shown = 0;
    sections.forEach(function (sec) {
      var n = 0;
      sec.querySelectorAll("li").forEach(function (li) {
        var keys = li.getAttribute("data-keys");
        var ok = words.every(function (w) { return keys.indexOf(w) >= 0; });
        li.hidden = !ok;
        if (ok) n++;
      });
      sec.hidden = n === 0;
      var det = sec.querySelector("details");
      if (det && words.length && n) det.open = true;
      var cnt = sec.querySelector("h2 .count");
      cnt.textContent = cnt.textContent.charAt(0) === "(" ? "(" + n + ")" : n;
      shown += n;
    });
    hits.textContent = words.length ? shown + " / " + total + "件" : "";
    none.hidden = shown > 0;
  }
  q.addEventListener("input", apply);
  q.addEventListener("keydown", function (e) { if (e.key === "Escape") { q.value = ""; apply(); } });
})();
</script>
"""


def render_top(loaded):
    desc = "AWS認定(SOA-C03を中心)の学習用に、サービス・用語・ユースケースを図解でまとめた教科書"
    parts = [head(SITE_TITLE, "", desc), header(""), "<main>\n",
             f'<div class="page-head"><h1>{SITE_TITLE}</h1><p class="lead">{desc}</p></div>\n']

    # 全ページ横断の検索(タイトル・説明・カテゴリ・小見出しが対象)
    index = []
    for c in COLLECTIONS:
        for p in loaded[c["key"]]:
            h3 = " ".join(plain(h) for h in re.findall(r"<h3[^>]*>(.*?)</h3>", p["body"], re.S))
            icon = c["key"] == "services" and (ICON_DIR / f'{p["slug"]}.svg').exists()
            index.append({"t": p["title"], "c": c["label"], "u": f'{c["key"]}/{p["slug"]}.html',
                          "i": f'icons/services/{p["slug"]}.svg' if icon else "",
                          "d": plain(p["lead"]),
                          "k": " ".join([p["title"], p["slug"], p["category"], plain(p["lead"]), h3]).lower()})
    parts.append('<div class="toc-search site-search">\n'
                 '  <input type="search" id="site-q" placeholder="全ページを検索(例: ライフサイクル、IMDSv2、フェイルオーバー)"'
                 ' aria-label="全ページを検索" autocomplete="off">\n'
                 '  <span class="toc-hits" id="site-hits"></span>\n</div>\n'
                 '<ul class="search-results" id="site-results" hidden></ul>\n'
                 + SITE_SEARCH_SCRIPT.replace("__INDEX__", json.dumps(index, ensure_ascii=False)))

    parts.append('<ul class="card-list top-cards">\n')
    for c in COLLECTIONS:
        n = len(loaded[c["key"]])
        badge = f"{n}ページ" if n else "準備中"
        parts.append(f'  <li><a href="{c["key"]}/index.html"><span class="name">{c["label"]}'
                     f'<span class="badge">{badge}</span></span><span class="desc">{c["desc"]}</span></a></li>\n')
    parts.append('  <li><a href="links.html"><span class="name">リンク集</span>'
                 '<span class="desc">試験ガイドや各サービスの公式ページ・ドキュメントへのリンク</span></a></li>\n')
    parts.append("</ul>\n")

    # 試験分野ごとの入口(ユースケースのカテゴリへ)
    parts.append('<section class="top-section">\n<h2>試験分野から学ぶ(SOA-C03)</h2>\n'
                 '<p class="cat-desc">分野ごとのユースケースから読み始め、出てくるサービス・用語のページへ進むのがおすすめです。</p>\n'
                 '<ol class="domain-list">\n')
    for i, (name, weight) in enumerate(EXAM_DOMAINS, 1):
        parts.append(f'  <li><a href="usecases/index.html#cat{i}"><span class="name">{html.escape(name)}</span>'
                     f'<span class="badge">{weight}%</span></a></li>\n')
    parts.append("</ol>\n</section>\n")

    # 最近更新したページ
    recent = sorted(((p, c) for c in COLLECTIONS for p in loaded[c["key"]]),
                    key=lambda pc: -pc[0]["updated"])[:10]
    parts.append('<section class="top-section">\n<h2>最近更新したページ</h2>\n<ul class="recent-list">\n')
    for p, c in recent:
        parts.append(f'  <li><time datetime="{fmt_date(p["updated"])}">{fmt_date(p["updated"])}</time>'
                     f'<span class="badge">{c["label"]}</span>'
                     f'<a href="{c["key"]}/{p["slug"]}.html">{html.escape(p["title"])}</a></li>\n')
    parts.append("</ul>\n</section>\n")
    parts += ["</main>\n", TAIL]
    return "".join(parts)


# トップの全ページ検索(スペース区切りのAND検索。タイトルに一致したページを先に並べる)
SITE_SEARCH_SCRIPT = """<script>
(function () {
  var pages = __INDEX__;
  var q = document.getElementById("site-q");
  var hits = document.getElementById("site-hits");
  var list = document.getElementById("site-results");
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  function apply() {
    var words = q.value.toLowerCase().trim().split(/\\s+/).filter(Boolean);
    if (!words.length) { list.hidden = true; hits.textContent = ""; return; }
    var found = pages.filter(function (p) {
      return words.every(function (w) { return p.k.indexOf(w) >= 0; });
    });
    found.sort(function (a, b) {
      var ta = words.every(function (w) { return a.t.toLowerCase().indexOf(w) >= 0; }) ? 0 : 1;
      var tb = words.every(function (w) { return b.t.toLowerCase().indexOf(w) >= 0; }) ? 0 : 1;
      return ta - tb;
    });
    hits.textContent = found.length + "件";
    list.innerHTML = found.slice(0, 30).map(function (p) {
      var icon = p.i ? '<img class="svc-icon" src="' + p.i + '" alt="" width="20" height="20">' : "";
      return '<li><a href="' + p.u + '"><span class="badge">' + esc(p.c) + '</span>' + icon + '<span class="name">' +
        esc(p.t) + '</span><span class="desc">' + esc(p.d) + '</span></a></li>';
    }).join("") || '<li class="empty-state">該当するページがありません。</li>';
    list.hidden = false;
  }
  q.addEventListener("input", apply);
  q.addEventListener("keydown", function (e) { if (e.key === "Escape") { q.value = ""; apply(); } });
})();
</script>
"""


def official_url(kind, path):
    """links.json の値を公式ページのURLにする(http で始まる値はそのまま使う)。"""
    if path.startswith("http"):
        return path
    base = "https://aws.amazon.com/jp/" if kind == "product" else "https://docs.aws.amazon.com/ja_jp/"
    return base + path + ("" if path.endswith(("/", ".html")) else "/")


def render_links(services, warnings):
    text = (SRC / "links.html").read_text(encoding="utf-8")
    meta = dict(META_RE.findall(text))
    data = json.loads((SRC / "links.json").read_text(encoding="utf-8"))
    col = next(c for c in COLLECTIONS if c["key"] == "services")
    rows = []
    for category, items in grouped(col, services):
        rows.append(f'<h3>{html.escape(category)}</h3>\n<div class="table-wrap"><table class="links">\n'
                    '<tr><th>サービス</th><th>製品ページ</th><th>ドキュメント</th></tr>\n')
        for p in items:
            if p["slug"] not in data:
                warnings.append(f"links.json: {p['slug']} がありません")
            product, docs = data.get(p["slug"], [None, None])
            cells = [f'<a href="{official_url(k, v)}" target="_blank" rel="noopener">公式</a>' if v else "—"
                     for k, v in (("product", product), ("docs", docs))]
            rows.append(f'<tr><td><a class="svc-link" href="services/{p["slug"]}.html">'
                        f'{service_icon(p["slug"], "", 20)}{html.escape(p["title"])}</a></td>'
                        f'<td>{cells[0]}</td><td>{cells[1]}</td></tr>\n')
        rows.append("</table></div>\n")
    body = META_RE.sub("", text).strip().replace("<!-- SERVICE_LINKS -->", "".join(rows))
    title = meta.get("title", "リンク集")
    return (head(f"{title} | {SITE_TITLE}", "", meta.get("lead", "")) + header("", "links")
            + f'<main>\n<div class="page-head">\n  <h1>{html.escape(title)}</h1>\n'
            + (f'  <p class="lead">{meta["lead"]}</p>\n' if meta.get("lead") else "")
            + "</div>\n" + body + "\n</main>\n" + TAIL)


def main():
    warnings, counts, loaded = [], {}, {}
    updated = git_updated()
    for col in COLLECTIONS:
        loaded[col["key"]] = load_pages(col, warnings, updated)
    add_backlinks(loaded)
    for col in COLLECTIONS:
        pages = loaded[col["key"]]
        counts[col["key"]] = len(pages)
        out_dir = OUT / col["key"]
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        for i, p in enumerate(pages):
            (out_dir / f"{p['slug']}.html").write_text(render_page(col, pages, i), encoding="utf-8")
        (out_dir / "index.html").write_text(render_collection_index(col, pages), encoding="utf-8")
    (OUT / "index.html").write_text(render_top(loaded), encoding="utf-8")
    (OUT / "links.html").write_text(render_links(loaded["services"], warnings), encoding="utf-8")
    print("built " + ", ".join(f"{c['label']} {counts[c['key']]}" for c in COLLECTIONS))
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
