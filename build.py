"""src/ 以下の本文から book/ 以下の教科書HTMLを生成する。

使い方: python build.py

コレクション(サービス・用語・運用シナリオ)ごとに src/{コレクション}/*.html を置く。
本文ファイルの先頭には次のメタ情報を書く。
    <!-- title: ページ名 -->
    <!-- category: カテゴリ名 -->
    <!-- lead: 一言説明 -->
図は diagrams.py の記法で書くとSVGに変換される。
公式リンク(book/links.html)は、src/links.html の本文と src/links.json(サービスごとの公式ページ)から作る。
"""
import hashlib
import html
import json
import re
import shlex
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path

from checks import check_pages
from diagrams import render_figures, text_width

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
        "categories": ["AWSの基礎", "ネットワーク", "セキュリティ・認証", "ストレージ", "設計・運用", "サービスの選び方"],
        "search": "用語・キーワードで絞り込み(例: IP、暗号化、DNS)",
        "order": [
            "shared-responsibility", "region-az", "default-vpc", "root-user", "access-methods", "arn", "tags",
            "pricing-basics", "support-plans", "service-quotas", "sla-availability", "managed-serverless",
            "well-architected", "compliance-artifact", "json-yaml",
            "dns", "dns-record-types", "cidr", "route-table", "nacl-security-group", "vpc-flow-logs",
            "eni-elastic-ip", "vpc-endpoint", "vpc-peering",
            "inbound-traffic", "outbound-traffic", "port-numbers", "http-status-codes",
            "iam-policy-evaluation", "iam-roles-credentials", "iam-passrole", "encryption", "tls-termination", "oidc", "spf",
            "storage-types", "performance-metrics",
            "high-availability-scaling", "deploy-strategies", "dr-strategies", "circuit-breaker",
            "cloudwatch-alarm-states", "event-driven-remediation", "cron-rate-expressions", "throttling-retry", "terraform-git",
            "monitoring-logging-comparison", "messaging-comparison", "caching-comparison",
            "hybrid-connectivity", "vpc-connectivity", "security-detection-comparison",
            "secrets-config-comparison", "cost-management-comparison",
        ],
    },
    {
        "key": "usecases",
        "label": "運用シナリオ",
        "desc": "やりたいこと別に、構成を自分で組み立ててから、解説で答えと考え方を確かめる(AWSアカウントは不要)",
        "categories": [
            "監視・ログ・自動修復", "信頼性・事業継続", "デプロイ・自動化",
            "セキュリティ・コンプライアンス", "ネットワーク・コンテンツ配信",
        ],
        "search": "やりたいこと・サービス名で絞り込み(例: バックアップ、パッチ)",
        # 各ページは 2章で構成を組み立て(自由構成・穴埋め)、3章以降の解説は「解説を読む」で表示する(book/js/sim.js)。
        # 一言説明を書くと使うサービスが分かってしまうので、lead は書かない。
        # 一覧は分野ごとの番号付きリストにし、演習の結果を並べる
        "no_lead": True,
        "numbered": True,
        "script": "sim.js",
        "old_key": "exercises",  # 統合前の構成演習のURL(book/exercises/)は、このコレクションのページへ転送する
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
    {
        # src/news/YYYY-MM-DD.html を毎日1件、クラウドの定期エージェントが追加する。
        # category は「YYYY年M月」。新しい日付から順に並べる
        "key": "news",
        "label": "ニュース",
        "desc": "AWSの新しい発表を、図解つきで分かりやすく解説(毎日更新)",
        "categories": [],
        "search": "サービス名・キーワードで絞り込み(例: Lambda、料金、東京リージョン)",
        "order": [],
        "newest_first": True,
    },
]
_by_key = {c["key"]: c for c in COLLECTIONS}

# SOA-C03の出題分野(試験ガイドより)。運用シナリオのカテゴリと同じ順番で対応させる。
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
        if col.get("no_lead") and meta.get("lead"):
            warnings.append(f"{where}: {col['label']}には lead を書きません(使うサービスが分かってしまうため)")
            meta.pop("lead")
        pages.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "category": meta.get("category", "その他"),
            "lead": meta.get("lead", ""),
            "raw": text,  # 検査用(行番号がファイルと一致するよう、メタ情報も含める)
            "body": render_figures(body, where, warnings),
            "updated": updated.get(f"src/{col['key']}/{path.name}", int(time.time())),
        })
    order = {s: i for i, s in enumerate(col["order"])}
    pages.sort(key=lambda p: (order.get(p["slug"], len(order)), p["title"]))
    if col.get("newest_first"):
        pages.sort(key=lambda p: p["slug"], reverse=True)
    return pages


# 被リンクの一覧を付けるページ:(リンク先のコレクション, リンク元のコレクション, 見出し)
BACKLINKS = [
    ("services", ["usecases"], "このサービスが登場する運用シナリオ"),
    ("terms", ["services", "usecases"], "この用語が出てくるページ"),
]


def add_backlinks(loaded):
    """サービス・用語のページの末尾に、そのページへリンクしている他のコレクションのページの一覧を付ける。"""
    labels = {c["key"]: c["label"] for c in COLLECTIONS}
    for target, sources, heading in BACKLINKS:
        for p in loaded.get(target, []):
            href = f'href="../{target}/{p["slug"]}.html'
            refs = [(key, q) for key in sources for q in loaded.get(key, []) if href in link_body(q)]
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
{desc}<script>
// 表示設定(テーマ・文字サイズ)を、画面が描かれる前に反映する(設定画面は js/site.js)
try {{
  var s = JSON.parse(localStorage.getItem("aws-textbook-prefs") || "{{}}");
  if (s.theme) document.documentElement.setAttribute("data-theme", s.theme);
  if (s.size) document.documentElement.setAttribute("data-size", s.size);
}} catch (e) {{}}
</script>
<link rel="stylesheet" href="{prefix}css/style.css">
<link rel="icon" type="image/png" href="{prefix}icons/favicon-32.png">
<link rel="apple-touch-icon" href="{prefix}icons/apple-touch-icon.png">
<link rel="manifest" href="{prefix}manifest.webmanifest">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1d2127" media="(prefers-color-scheme: dark)">
<script>
if ("serviceWorker" in navigator && location.protocol !== "file:") {{
  navigator.serviceWorker.register("{prefix}sw.js").catch(function () {{}});
}}
</script>
<script src="{prefix}js/site.js" defer></script>
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
        f'{c["label"]}</a>' for c in COLLECTIONS if c.get("nav", True))
    links += f'<a href="{prefix}links.html"{cur if current == "links" else ""}>公式リンク</a>'
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
            + "  </div>\n</div>\n" + page_toc(items) + body + "\n" + p.get("graph", "")
            + pager(prev, nxt) + "</main>\n" + TO_TOP
            + exercise_graph(col, p) + page_script(col) + TAIL)


def exercise_graph(col, p):
    """構成演習の「自由構成」で使う正解の構成を、2章の図と問いから取り出して JSON で埋め込む。
    空欄(blank)のノードは正解の選択肢の名前に置き換え、不正解の選択肢は紛らわしい部品として渡す。"""
    raw = p["raw"]
    if 'class="ex-item"' not in raw:
        return ""
    answers, distractors = {}, []
    for attrs, inner in re.findall(r'<div class="ex-item"([^>]*)>(.*?)</ul>\s*</div>', raw, re.S):
        node = re.search(r'data-node="([^"]+)"', attrs)
        if not node:
            continue
        for li_attrs, text in re.findall(r'<li\b([^>]*)>(.*?)<span class="ex-why"', inner, re.S):
            short = re.search(r'data-short="([^"]+)"', li_attrs)
            label = html.unescape(short.group(1)) if short else plain(text).strip()
            if "data-ok" in li_attrs:
                answers[node.group(1)] = label
            else:
                distractors.append(label)
    m = re.search(r'<figure class="figure" data-diagram>\s*(.*?)\s*<figcaption>', raw, re.S)
    if not m:
        return ""
    colw, rowh, nodes, edges = 170.0, 90.0, [], []
    for line in m.group(1).splitlines():
        try:
            tok = shlex.split(line.strip())
        except ValueError:
            continue
        if not tok:
            continue
        if tok[0] == "grid":
            colw, rowh = float(tok[1]), float(tok[2])
        elif tok[0] == "node" and tok[4] != "plain":
            nid, style, main = tok[1], tok[4], tok[5].replace("\\n", " ")
            sub = tok[6] if len(tok) > 6 and "=" not in tok[6] else ""
            label = answers.get(nid, main) if style == "blank" else main
            nodes.append({"id": nid, "label": label, "sub": "" if style == "blank" else sub,
                          "x": float(tok[2]), "y": float(tok[3])})
        elif tok[0] == "edge":
            flags = set(tok[3:])
            edges.append([tok[1], tok[2], "dash" in flags, "both" in flags])
    # 同じ名前のノード(2台のEC2など)は補足で見分ける
    names = [n["label"] for n in nodes]
    for n in nodes:
        if names.count(n["label"]) > 1 and n["sub"]:
            n["label"] += f"({n['sub']})"
    labels = {n["label"] for n in nodes}
    data = {"colw": colw, "rowh": rowh, "nodes": nodes, "edges": edges,
            "distractors": sorted({d for d in distractors if d not in labels})}
    js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/json" id="ex-graph">{js}</script>\n'


def page_script(col):
    """コレクション専用のスクリプト(構成演習の答え合わせなど)を読み込むタグ。"""
    return f'<script src="../js/{col["script"]}" defer></script>\n' if col.get("script") else ""


def cat_style(col, category):
    """カテゴリの色を CSS変数 --cat として渡す属性(色が決まっていなければ空)。"""
    color = col.get("category_colors", {}).get(category)
    return f' style="--cat:{color}"' if color else ""


def render_collection_index(col, pages, loaded):
    parts = [head(f"{col['label']} | {SITE_TITLE}", "../", col["desc"]), header("../", col["key"]), "<main>\n",
             f'<div class="page-head"><h1>{col["label"]}</h1><p class="lead">{col["desc"]}</p></div>\n']
    if col["key"] in BOOKLET_KEYS and pages:
        parts.append(f'<p class="booklet-link"><a href="../print/{col["key"]}.html">まとめて印刷・PDFに保存'
                     f'(全{len(pages)}ページを1つに)</a></p>\n')
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
    if col.get("numbered"):
        parts.append(numbered_index(col, groups, loaded))
        groups = []
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
            keys = search_keys(p, category)
            if compact:
                tip = html.escape(p["title"] + (":" + plain(p["lead"]) if p["lead"] else ""))
                inner = (f'{service_icon(p["slug"], "../", 28)}'
                         f'<span class="name">{html.escape(p["title"])}</span><span class="go" aria-hidden="true">›</span>')
                parts.append(f'  <li data-keys="{html.escape(keys)}"><a href="{p["slug"]}.html" '
                             f'title="{tip}">{inner}</a></li>\n')
            else:
                inner = (f'<span class="name">{html.escape(p["title"])}</span>'
                         f'<span class="desc">{p["lead"]}</span>')
                parts.append(f'  <li data-keys="{html.escape(keys)}"><a href="{p["slug"]}.html">{inner}</a></li>\n')
        parts.append("</ul>\n</details>\n</section>\n" if compact else "</ul>\n</section>\n")
    if compact:
        parts.append("</div>\n")
    if col.get("search") and pages:
        parts.append('<p class="empty-state" id="toc-none" hidden>該当するページがありません。</p>\n'
                     + SEARCH_SCRIPT.replace("__HELPERS__", search_helpers()))
    parts += ["</main>\n", page_script(col), TAIL]
    return "".join(parts)


def numbered_index(col, groups, loaded):
    """運用シナリオの一覧。試験分野ごとに番号付きで並べる(演習の結果は sim.js が名前の横に表示する)。"""
    out = []
    for i, (category, items) in enumerate(groups, 1):
        domain = (f'<span class="uc-domain">分野{i}<span class="uc-weight">{EXAM_DOMAINS[i - 1][1]}%</span></span>'
                  if i <= len(EXAM_DOMAINS) else "")
        out.append(f'<section class="toc-category uc-group" id="cat{i}">\n<h2>{domain}'
                   f'<span class="uc-cat">{html.escape(category)}</span> <span class="count">({len(items)})</span></h2>\n')
        if category in col.get("category_desc", {}):
            out.append(f'<p class="cat-desc">{html.escape(col["category_desc"][category])}</p>\n')
        out.append('<ol class="uc-list">\n')
        for n, p in enumerate(items, 1):
            out.append(f'  <li data-keys="{html.escape(search_keys(p, category))}"><a class="uc-link" href="{p["slug"]}.html">'
                       f'<span class="uc-no">{i}-{n:02d}</span><span class="name">{html.escape(p["title"])}</span></a></li>\n')
        out.append("</ol>\n</section>\n")
    return "".join(out)


def norm(s):
    """検索用の正規化(全角英数を半角に、英字を小文字に)。"""
    return unicodedata.normalize("NFKC", s).lower()


def search_keys(p, category, extra=""):
    """一覧の絞り込み・全ページ検索の対象。表示しない lead・カテゴリ・本文からリンクしているサービス名も含める
    (運用シナリオは lead がないので、使うサービスの名前で探せるようにする)。"""
    return norm(" ".join([p["title"], p["slug"], category, plain(p["lead"]), " ".join(p.get("uses", [])), extra]))


# 検索で同じものとして扱う言い換え(略称・英語名・日本語の言い方)。
# 入力した語がどれかと一致すると、同じグループの語のどれかを含むページも見つかる。小文字・半角で書く
SYNONYMS = [
    ["ec2", "仮想サーバー", "仮想マシン", "vm", "elastic compute cloud"],
    ["elb", "alb", "nlb", "gwlb", "ロードバランサー", "ロードバランサ", "負荷分散", "load balancer", "elastic load balancing"],
    ["s3", "オブジェクトストレージ", "simple storage service"],
    ["ebs", "ブロックストレージ", "elastic block store"],
    ["efs", "nfs", "ファイル共有", "elastic file system"],
    ["rds", "rdb", "リレーショナルデータベース", "mysql", "postgresql", "relational database service"],
    ["dynamodb", "nosql", "キーバリュー", "ddb"],
    ["elasticache", "redis", "memcached", "valkey"],
    ["キャッシュ", "cache", "caching"],
    ["lambda", "ラムダ", "サーバーレス", "serverless", "関数"],
    ["iam", "identity and access management", "アクセス許可", "権限"],
    ["sso", "シングルサインオン", "identity center", "saml"],
    ["kms", "key management service", "暗号化キー", "cmk", "カスタマーマネージドキー"],
    ["暗号化", "encryption", "sse", "sse-kms", "sse-s3"],
    ["cloudwatch", "cw", "メトリクス", "metrics", "アラーム", "alarm"],
    ["監視", "モニタリング", "monitoring"],
    ["ログ", "log", "logs"],
    ["cloudtrail", "証跡", "監査ログ"],
    ["config", "aws config", "構成変更", "準拠"],
    ["ssm", "systems manager", "session manager", "patch manager", "run command", "state manager",
     "パラメータストア", "parameter store"],
    ["cfn", "cloudformation", "iac", "infrastructure as code", "スタック", "stack"],
    ["route53", "route 53", "dns", "名前解決"],
    ["cloudfront", "cdn", "コンテンツ配信", "エッジ", "edge"],
    ["vpc", "virtual private cloud", "仮想ネットワーク"],
    ["sg", "セキュリティグループ", "security group", "nacl", "ネットワークacl", "ファイアウォール", "firewall"],
    ["nat", "natゲートウェイ", "nat gateway"],
    ["vpn", "ipsec", "site-to-site", "client vpn", "リモートアクセス"],
    ["dx", "direct connect", "専用線"],
    ["tgw", "transit gateway"],
    ["エンドポイント", "endpoint", "privatelink", "vpce"],
    ["sqs", "キュー", "queue", "dlq", "デッドレターキュー"],
    ["sns", "通知", "notification", "pub/sub"],
    ["eventbridge", "イベントバス", "cloudwatch events", "scheduler", "スケジューラー"],
    ["step functions", "sfn", "ワークフロー", "ステートマシン"],
    ["asg", "auto scaling", "オートスケーリング", "スケーリング", "scaling"],
    ["コンテナ", "container", "docker", "ecs", "eks", "fargate", "kubernetes", "k8s"],
    ["ci/cd", "cicd", "パイプライン", "pipeline", "codepipeline", "codebuild", "codedeploy"],
    ["デプロイ", "deploy", "リリース", "release"],
    ["x-ray", "xray", "トレース", "trace", "tracing", "分散トレーシング"],
    ["waf", "ウェブacl", "web acl", "sqlインジェクション", "xss"],
    ["shield", "ddos"],
    ["guardduty", "脅威の検出", "脅威検出"],
    ["inspector", "脆弱性", "cve"],
    ["macie", "個人情報", "pii", "機密データ"],
    ["secrets manager", "シークレット", "パスワード", "password", "ローテーション", "rotation"],
    ["acm", "証明書", "certificate", "ssl", "tls", "https"],
    ["organizations", "scp", "マルチアカウント", "複数アカウント", "ou"],
    ["backup", "バックアップ", "スナップショット", "snapshot"],
    ["dr", "災害対策", "ディザスタリカバリ", "disaster recovery"],
    ["フェイルオーバー", "failover", "切り替え"],
    ["高可用性", "multi-az", "マルチaz", "冗長化", "ha"],
    ["料金", "費用", "コスト", "cost", "請求", "billing"],
    ["ri", "リザーブドインスタンス", "reserved instance", "savings plans"],
    ["kinesis", "ストリーム", "stream", "firehose"],
    ["sts", "assumerole", "一時的な認証情報", "ロールの引き受け"],
    ["cognito", "ユーザー認証", "サインイン"],
    ["api gateway", "apigw", "rest api"],
    ["imds", "imdsv2", "メタデータ", "metadata"],
    ["ami", "マシンイメージ", "ゴールデンイメージ", "image builder"],
    ["az", "アベイラビリティーゾーン", "availability zone"],
    ["リージョン", "region"],
    ["cidr", "ipアドレス", "ip address", "サブネットマスク", "ipam"],
    ["踏み台", "bastion", "ssh", "rdp"],
    ["パッチ", "patch", "更新プログラム"],
]


def search_helpers():
    """一覧の絞り込みと全ページ検索で共通の、言い換えを含めた一致判定(JavaScript)。"""
    syn = json.dumps([[norm(w) for w in g] for g in SYNONYMS], ensure_ascii=False)
    return SEARCH_HELPERS.replace("__SYN__", syn)


# terms("ec2 ログ") → [["ec2", 言い換え…], ["ログ", 言い換え…]]。語ごとに、言い換えのどれかを含めば一致
SEARCH_HELPERS = """  var SYN = __SYN__;
  function norm(s) { return (s.normalize ? s.normalize("NFKC") : s).toLowerCase(); }
  // 言い換えに含まれる短い英字(dr・ha・ri など)は、ほかの語の一部(address・share など)に当たらないよう単語として探す
  function word(a) { return /^[a-z0-9]{1,3}$/.test(a) ? new RegExp("(^|[^a-z0-9])" + a + "([^a-z0-9]|$)") : a; }
  function terms(v) {
    return norm(v).trim().split(/\\s+/).filter(Boolean).map(function (w) {
      var alts = [], known = false;
      SYN.forEach(function (g) {
        if (g.indexOf(w) < 0) return;
        known = true;
        g.forEach(function (a) { if (a !== w) alts.push(word(a)); });
      });
      alts.unshift(known ? word(w) : w);
      return alts;
    });
  }
  function hit(keys, alts) {
    return alts.some(function (a) { return typeof a === "string" ? keys.indexOf(a) >= 0 : a.test(keys); });
  }
  function hitAll(keys, ts) { return ts.every(function (alts) { return hit(keys, alts); }); }
  // 「/」キーで検索欄へ移る
  document.addEventListener("keydown", function (e) {
    var t = e.target.tagName;
    if (e.key === "/" && t !== "INPUT" && t !== "TEXTAREA" && !e.ctrlKey && !e.metaKey) { e.preventDefault(); q.focus(); }
  });
"""


# 目次の絞り込み(スペース区切りのAND検索。該当なしのカテゴリは隠し、件数を更新する)
SEARCH_SCRIPT = """<script>
(function () {
  var q = document.getElementById("toc-q");
  var hits = document.getElementById("toc-hits");
  var none = document.getElementById("toc-none");
__HELPERS__
  var sections = document.querySelectorAll(".toc-category");
  var total = document.querySelectorAll(".toc-category li").length;
  function apply() {
    var words = terms(q.value);
    var shown = 0;
    sections.forEach(function (sec) {
      var n = 0;
      sec.querySelectorAll("li").forEach(function (li) {
        var keys = li.getAttribute("data-keys");
        var ok = hitAll(keys, words);
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
    desc = "AWS認定(SOA-C03を中心)の学習用に、サービス・用語・運用シナリオを図解でまとめた教科書"
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
                          "k": search_keys(p, p["category"], h3)})
    parts.append('<div class="toc-search site-search" id="search">\n'
                 '  <input type="search" id="site-q" placeholder="全ページを検索(例: ロードバランサー、IMDSv2、DR)"'
                 ' aria-label="全ページを検索" autocomplete="off">\n'
                 '  <span class="toc-hits" id="site-hits"></span>\n</div>\n'
                 '<ul class="search-results" id="site-results" hidden></ul>\n'
                 + SITE_SEARCH_SCRIPT.replace("__INDEX__", json.dumps(index, ensure_ascii=False))
                 .replace("__HELPERS__", search_helpers()))

    parts.append('<ul class="card-list top-cards">\n')
    for c in COLLECTIONS:
        n = len(loaded[c["key"]])
        badge = f"{n}ページ" if n else "準備中"
        parts.append(f'  <li><a href="{c["key"]}/index.html"><span class="name">{c["label"]}'
                     f'<span class="badge">{badge}</span></span><span class="desc">{c["desc"]}</span></a></li>\n')
    parts.append('  <li><a href="links.html"><span class="name">公式リンク</span>'
                 '<span class="desc">試験ガイドや各サービスの公式ページ・ドキュメントへのリンク</span></a></li>\n')
    parts.append("</ul>\n")

    # 試験分野ごとの入口(運用シナリオのカテゴリへ)
    parts.append('<section class="top-section">\n<h2>試験分野から学ぶ(SOA-C03)</h2>\n'
                 '<p class="cat-desc">分野ごとの運用シナリオから読み始め、出てくるサービス・用語のページへ進むのがおすすめです。</p>\n'
                 '<ol class="domain-list">\n')
    for i, (name, weight) in enumerate(EXAM_DOMAINS, 1):
        parts.append(f'  <li><a href="usecases/index.html#cat{i}"><span class="name">{html.escape(name)}</span>'
                     f'<span class="badge">{weight}%</span></a></li>\n')
    parts.append("</ol>\n</section>\n")

    # 最新のニュース(新しい日付から5件)
    if loaded["news"]:
        parts.append('<section class="top-section">\n<h2>最新のAWSニュース</h2>\n<ul class="recent-list">\n')
        for p in loaded["news"][:5]:
            parts.append(f'  <li><time datetime="{p["slug"]}">{p["slug"]}</time>'
                         f'<a href="news/{p["slug"]}.html">{html.escape(p["title"])}</a></li>\n')
        parts.append('</ul>\n<p class="cat-desc"><a href="news/index.html">ニュースの一覧へ</a></p>\n</section>\n')

    # 最近更新したページ(ニュースは上の欄に出すので除く)
    recent = sorted(((p, c) for c in COLLECTIONS if c["key"] != "news" for p in loaded[c["key"]]),
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
__HELPERS__
  if (location.hash === "#search") q.focus();
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  function apply() {
    var words = terms(q.value);
    if (!words.length) { list.hidden = true; hits.textContent = ""; return; }
    var found = pages.filter(function (p) { return hitAll(p.k, words); });
    found.sort(function (a, b) {
      return (hitAll(norm(a.t), words) ? 0 : 1) - (hitAll(norm(b.t), words) ? 0 : 1);
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


EX_ITEM_RE = re.compile(r'<div class="ex-item"[^>]*>.*?</ul>\s*</div>', re.S)


def link_body(p):
    """リンクを数えるための本文。構成演習の問い(不正解の選択肢の解説を含む)は除く。"""
    return EX_ITEM_RE.sub("", p["body"])


GRAPH_KEYS = ("services", "terms", "usecases")  # つながり図・用語のポップアップに使うコレクション
LINK_RE = re.compile(r'href="(?:\.\./(services|terms|usecases)/)?([\w-]+)\.html')


def collect_links(loaded):
    """サービス・用語・運用シナリオのページ同士のリンク。{(key, slug): {(key, slug), ...}}
    あわせて、各ページが本文からリンクしているサービスの名前を p["uses"] に入れる(検索用)。"""
    pages = {(k, p["slug"]): p for k in GRAPH_KEYS for p in loaded[k]}
    out = {}
    for (key, slug), p in pages.items():
        found = {(k or key, s) for k, s in LINK_RE.findall(link_body(p))}
        out[(key, slug)] = {t for t in found if t in pages and t != (key, slug)}
        p["uses"] = sorted(pages[t]["title"] for t in out[(key, slug)] if t[0] == "services")
    return out


def fit(text, width, size):
    """幅に収まるように末尾を「…」で切る。"""
    if text_width(text, size) <= width:
        return text
    while text and text_width(text + "…", size) > width:
        text = text[:-1]
    return text + "…"


def page_graph(key, p, links, titles):
    """このページとリンクでつながるページの図(左=リンク元、右=リンク先。互いにリンクしていれば右に両向きの矢印)。"""
    me = (key, p["slug"])
    kind_order = {k: i for i, k in enumerate(GRAPH_KEYS)}

    def order(t):
        return (kind_order[t[0]], titles[t])
    outs = sorted(links.get(me, ()), key=order)
    ins = sorted((t for t, dst in links.items() if me in dst and t not in links.get(me, ())), key=order)
    if not outs and not ins:
        return ""
    row, nh, colw, cw, gap, top = 30, 22, 230, 180, 70, 30
    rows = max(len(ins), len(outs), 1)
    W, H = 2 * colw + 2 * gap + cw + 4, top + rows * row + 6
    cx0, cx1, cy = colw + gap, colw + gap + cw, top + rows * row / 2
    labels = {c["key"]: c["label"] for c in COLLECTIONS}

    def node(t, x, y):
        return (f'<a href="../{t[0]}/{t[1]}.html"><title>{html.escape(labels[t[0]])}:{html.escape(titles[t])}</title>'
                f'<rect x="{x}" y="{y - nh / 2:.0f}" width="{colw}" height="{nh}" rx="11" class="gr-{t[0]}"/>'
                f'<text x="{x + 10}" y="{y + 4.5:.0f}" class="gr-t">{html.escape(fit(titles[t], colw - 20, 13))}</text></a>')

    def ys(n):
        start = cy - n * row / 2 + row / 2
        return [start + i * row for i in range(n)]
    out = []
    for t, y in zip(ins, ys(len(ins))):
        out.append(f'<path class="gr-line" d="M{colw},{y:.0f} C{colw + gap / 2},{y:.0f} {cx0 - gap / 2},{cy:.0f} {cx0},{cy:.0f}" '
                   'marker-end="url(#gr-arrow)"/>')
        out.append(node(t, 0, y))
    for t, y in zip(outs, ys(len(outs))):
        both = me in links.get(t, ())
        out.append(f'<path class="gr-line" d="M{cx1},{cy:.0f} C{cx1 + gap / 2},{cy:.0f} {cx1 + gap / 2},{y:.0f} {cx1 + gap},{y:.0f}" '
                   'marker-end="url(#gr-arrow)"' + (' marker-start="url(#gr-arrow)"' if both else "") + "/>")
        out.append(node(t, cx1 + gap, y))
    out.append(f'<rect x="{cx0}" y="{cy - 20:.0f}" width="{cw}" height="40" rx="12" class="gr-me"/>'
               f'<text x="{cx0 + cw / 2:.0f}" y="{cy + 5:.0f}" text-anchor="middle" class="gr-tb">'
               f'{html.escape(fit(p["title"], cw - 16, 14))}</text>')
    if ins:
        out.append(f'<text x="{colw / 2:.0f}" y="14" text-anchor="middle" class="gr-h">リンク元({len(ins)})</text>')
    if outs:
        out.append(f'<text x="{cx1 + gap + colw / 2:.0f}" y="14" text-anchor="middle" class="gr-h">リンク先({len(outs)})</text>')
    svg = (f'<svg viewBox="0 0 {W} {H:.0f}" style="max-width:{W}px;min-width:600px" role="img" '
           f'aria-label="{html.escape(p["title"])}とリンクでつながるページの図">'
           '<defs><marker id="gr-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
           'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="dg-head"/></marker></defs>\n'
           + "\n".join(out) + "\n</svg>")
    legend = "".join(f'<span class="gr-key gr-key-{k}">{labels[k]}</span>' for k in GRAPH_KEYS)
    return ('<section class="chapter graph-chapter">\n<h2>このページのつながり</h2>\n<details class="graph">\n'
            f'<summary>つながり図を開く(リンク先 {len(outs)}件・リンク元 {len(ins)}件)</summary>\n'
            f'<figure class="figure">\n<div class="fig-scroll">\n{svg}\n</div>\n'
            f'<figcaption>左はこのページへリンクしているページ、右はこのページからリンクしているページ'
            f'(両向きの矢印は互いにリンク)。名前を押すとそのページへ移動します。{legend}</figcaption>\n'
            '</figure>\n</details>\n</section>\n')


def write_glossary(loaded):
    """本文中のサービス・用語へのリンクに出すポップアップの内容(book/js/glossary.js)。"""
    data = {}
    for key in ("services", "terms"):
        label = _by_key[key]["label"]
        for p in loaded[key]:
            icon = key == "services" and (ICON_DIR / f'{p["slug"]}.svg').exists()
            data[f'{key}/{p["slug"]}'] = {"t": p["title"], "d": plain(p["lead"]), "c": label, "i": icon}
    js = ("// build.py が生成するファイル(直接編集しない)。js/site.js が用語のポップアップに使う\n"
          "window.AWSB_GLOSSARY = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n")
    (OUT / "js" / "glossary.js").write_text(js, encoding="utf-8")


BOOKLET_KEYS = ("services", "terms", "usecases")  # まとめ冊子(印刷・PDF用に全ページを1つにしたページ)を作るコレクション


def booklet_body(key, p):
    """冊子の1ページ分の本文。見出しの id にページの slug を付けて重ならないようにし、
    同じコレクションへのリンクは冊子の中の移動にする。"""
    core = re.sub(r'<section class="chapter">(?:(?!</section>).)*class="ex-item".*?</section>\s*', "", p["core"], flags=re.S)
    body, _ = add_heading_ids(stack_tables(core))
    ids = set(re.findall(r'\bid="([^"]+)"', body))
    slug = p["slug"]

    def fix_id(m):
        return f'{m.group(1)}{slug}-{m.group(2)}{m.group(3)}' if m.group(2) in ids else m.group(0)
    body = re.sub(r'(\bid="|href="#|url\(#)([^")]+)([")])', fix_id, body)

    def fix_href(m):
        href = m.group(1)
        if re.match(r"(https?:|#|/|\.\./|mailto:)", href):
            return m.group(0)
        target = re.match(r"([\w-]+)\.html(#.*)?$", href)
        if target and not target.group(2):
            return f'href="#p-{target.group(1)}"'
        return f'href="../{key}/{href}"'
    return re.sub(r'href="([^"]*)"', fix_href, body)


def render_booklet(col, pages):
    key = col["key"]
    title = f"{col['label']}のまとめ冊子"
    parts = [head(f"{title} | {SITE_TITLE}", "../", col["desc"]), header("../", key), '<main class="booklet">\n',
             f'<div class="page-head booklet-cover">\n<p class="booklet-site">{SITE_TITLE}</p>\n<h1>{col["label"]}</h1>\n'
             f'<p class="lead">{col["desc"]}(全{len(pages)}ページ)</p>\n'
             '<p class="booklet-help">このページは、印刷やPDFでの保存のために全ページを1つにまとめたものです。'
             'ブラウザーの印刷(Ctrl+P、スマホは共有メニューの「プリント」)から、紙に印刷するかPDFとして保存してください。'
             'ページの順番は目次と同じです。</p>\n'
             '<p class="booklet-help"><button type="button" class="booklet-print" onclick="print()">印刷・PDFに保存</button> '
             f'<a href="../{key}/index.html">目次へ戻る</a></p>\n'
             + '</div>\n<nav class="booklet-toc" aria-label="冊子の目次">\n<h2>目次</h2>\n']
    for category, items in grouped(col, pages):
        parts.append(f'<h3>{html.escape(category)}</h3>\n<ol>\n')
        parts += [f'<li><a href="#p-{p["slug"]}">{html.escape(p["title"])}</a></li>\n' for p in items]
        parts.append("</ol>\n")
    parts.append("</nav>\n")
    for p in pages:
        parts.append(f'<article class="booklet-page" id="p-{p["slug"]}">\n'
                     f'<div class="page-head hero"{cat_style(col, p["category"])}>\n<div class="hero-text">\n'
                     f'<span class="category">{html.escape(p["category"])}</span>\n<h1>{html.escape(p["title"])}</h1>\n'
                     + (f'<p class="lead">{p["lead"]}</p>\n' if p["lead"] else "")
                     + "</div>\n</div>\n" + booklet_body(key, p) + "\n</article>\n")
    parts += ["</main>\n", TO_TOP, TAIL]
    return "".join(parts)


def write_redirects(col, pages):
    """統合前のURL(book/{old_key}/)から、同じ slug の新しいページへ転送する。"""
    old = OUT / col["old_key"]
    if old.exists():
        shutil.rmtree(old)
    old.mkdir()
    for slug in [p["slug"] for p in pages] + ["index"]:
        url = f'../{col["key"]}/{slug}.html'
        (old / f"{slug}.html").write_text(
            '<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="UTF-8">\n'
            f'<meta http-equiv="refresh" content="0; url={url}">\n<link rel="canonical" href="{url}">\n'
            f'<title>{SITE_TITLE}</title>\n</head>\n<body>\n'
            f'<p>このページは{col["label"]}に移りました。<a href="{url}">移動先を開く</a></p>\n</body>\n</html>\n',
            encoding="utf-8")


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
    title = meta.get("title", "公式リンク")
    return (head(f"{title} | {SITE_TITLE}", "", meta.get("lead", "")) + header("", "links")
            + f'<main>\n<div class="page-head">\n  <h1>{html.escape(title)}</h1>\n'
            + (f'  <p class="lead">{meta["lead"]}</p>\n' if meta.get("lead") else "")
            + "</div>\n" + body + "\n</main>\n" + TAIL)


def write_service_worker():
    """book/ の全ファイルをオフライン用に保存する Service Worker(book/sw.js)を作る。
    ファイルごとに内容のハッシュを持たせ、更新時は変わったファイルだけを取り直す。"""
    files = {}
    for f in sorted(OUT.rglob("*")):
        rel = f.relative_to(OUT).as_posix()
        if f.is_file() and rel != "sw.js" and not f.name.startswith(".") and not rel.startswith("print/"):
            # Windows ではテキストの改行が CRLF で書き出されるが、公開されるのは Git が LF にそろえた内容なので、LF にしてから計算する
            data = f.read_bytes()
            if f.suffix in (".html", ".css", ".js", ".json", ".svg", ".webmanifest"):
                data = data.replace(b"\r\n", b"\n")
            files[rel] = hashlib.sha256(data).hexdigest()[:12]
    version = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:12]
    js = (SERVICE_WORKER_SCRIPT.replace("__VERSION__", version)
          .replace("__FILES__", json.dumps(files, ensure_ascii=False, indent=0)))
    (OUT / "sw.js").write_text(js, encoding="utf-8")


# オフライン用の Service Worker。
# install: 前の版の保存場所から内容が同じファイルを写し、変わったファイルだけをダウンロードする
# activate: 前の版の保存場所を消す
# fetch: 保存済みのファイルがあればそれを返し、なければネットワークに取りに行く
SERVICE_WORKER_SCRIPT = """// build.py が生成するファイル(直接編集しない)
var PREFIX = "aws-textbook-";
var CACHE = PREFIX + "__VERSION__";
var FILES = __FILES__;
var LIST = "__files__.json";

function url(path) { return new URL(path, self.registration.scope).href; }

self.addEventListener("install", function (e) {
  e.waitUntil((async function () {
    var cache = await caches.open(CACHE);
    var old = null, oldFiles = {};
    var names = (await caches.keys()).filter(function (k) { return k.startsWith(PREFIX) && k !== CACHE; });
    if (names.length) {
      old = await caches.open(names[names.length - 1]);
      var list = await old.match(url(LIST));
      if (list) oldFiles = await list.json();
    }
    await Promise.all(Object.keys(FILES).map(async function (path) {
      if (old && oldFiles[path] === FILES[path]) {
        var res = await old.match(url(path));
        if (res) return cache.put(url(path), res);
      }
      var fresh = await fetch(url(path), { cache: "reload" });
      if (!fresh.ok) throw new Error(path + " " + fresh.status);
      return cache.put(url(path), fresh);
    }));
    await cache.put(url(LIST), new Response(JSON.stringify(FILES), { headers: { "Content-Type": "application/json" } }));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", function (e) {
  e.waitUntil((async function () {
    var names = await caches.keys();
    await Promise.all(names.filter(function (k) { return k.startsWith(PREFIX) && k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", function (e) {
  if (e.request.method !== "GET") return;
  var u = new URL(e.request.url);
  if (u.origin !== location.origin) return;
  u.search = ""; u.hash = "";
  if (u.pathname.endsWith("/")) u.pathname += "index.html";
  e.respondWith(caches.open(CACHE).then(function (cache) {
    return cache.match(u.href).then(function (res) { return res || fetch(e.request); });
  }));
});
"""


def main():
    warnings, counts, loaded = [], {}, {}
    updated = git_updated()
    for col in COLLECTIONS:
        loaded[col["key"]] = load_pages(col, warnings, updated)
    links_raw = (SRC / "links.html").read_text(encoding="utf-8")
    check_pages(COLLECTIONS, loaded, {"links.html": links_raw}, OUT, warnings)
    links = collect_links(loaded)
    titles = {(k, p["slug"]): p["title"] for k in GRAPH_KEYS for p in loaded[k]}
    for k in GRAPH_KEYS:
        for p in loaded[k]:
            p["graph"] = page_graph(k, p, links, titles)
    for c in COLLECTIONS:
        for p in loaded[c["key"]]:
            p["core"] = p["body"]  # 被リンクの一覧を付ける前の本文(冊子に使う)
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
        (out_dir / "index.html").write_text(render_collection_index(col, pages, loaded), encoding="utf-8")
        if col.get("old_key"):
            write_redirects(col, pages)
    print_dir = OUT / "print"
    if print_dir.exists():
        shutil.rmtree(print_dir)
    print_dir.mkdir()
    for key in BOOKLET_KEYS:
        (print_dir / f"{key}.html").write_text(render_booklet(_by_key[key], loaded[key]), encoding="utf-8")
    write_glossary(loaded)
    (OUT / "index.html").write_text(render_top(loaded), encoding="utf-8")
    (OUT / "links.html").write_text(render_links(loaded["services"], warnings), encoding="utf-8")
    write_service_worker()
    print("built " + ", ".join(f"{c['label']} {counts[c['key']]}" for c in COLLECTIONS))
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
