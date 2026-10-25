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
            "マネジメントとガバナンス", "アプリケーション統合", "デベロッパーツール",
            "フレームワーク", "ライブラリ", "分析", "移行と転送", "ビジネスアプリケーション",
        ],
        "compact": True,
        "search": True,
        "order": [
            "ec2", "auto-scaling", "lambda", "elastic-beanstalk",
            "ecs", "eks", "ecr", "copilot",
            "s3", "ebs", "efs", "fsx", "backup",
            "rds", "aurora", "dynamodb", "elasticache", "memorydb",
            "vpc", "transit-gateway", "site-to-site-vpn", "direct-connect",
            "route53", "elb", "cloudfront", "global-accelerator", "api-gateway",
            "iam", "identity-center", "sts", "organizations", "directory-service", "cognito", "kms",
            "secrets-manager", "acm", "private-ca", "macie", "security-hub",
            "cloudwatch", "cloudtrail", "config", "systems-manager", "cloudformation", "cdk",
            "trusted-advisor", "health-dashboard", "compute-optimizer", "service-catalog", "ram",
            "managed-grafana", "managed-prometheus",
            "sqs", "sns", "eventbridge", "step-functions", "appsync",
            "codepipeline", "codebuild", "codedeploy", "codeartifact", "xray", "cloudshell", "amplify",
            "sam", "sdk", "database-encryption-sdk",
            "athena", "kinesis", "opensearch", "datasync", "ses",
        ],
    },
    {
        "key": "terms",
        "label": "用語",
        "desc": "AWSを学ぶうえで押さえておきたい用語の解説",
        "categories": ["AWSの基礎", "ネットワーク", "セキュリティ・認証", "ストレージ", "設計・運用"],
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
        "category_desc": {
            "監視・ログ・自動修復": "メトリクスやログで異常を見つけ、通知や自動修復につなげる",
            "信頼性・事業継続": "スケーリング・高可用性・バックアップ・災害対策",
            "デプロイ・自動化": "パッチ適用・複数アカウントへの展開・安全なリリース",
            "セキュリティ・コンプライアンス": "権限・暗号化・ガードレール・設定の監査と修復",
            "ネットワーク・コンテンツ配信": "VPCの接続・安全な運用アクセス・配信・トラブル調査",
        },
        "order": [
            "ec2-memory-monitoring", "log-error-alert", "ec2-auto-recovery", "centralized-logging",
            "auto-scaling-web", "rds-high-availability", "backup-cross-region", "multi-region-failover",
            "patch-management", "multi-account-stacksets", "ec2-blue-green-pipeline", "lambda-canary-release",
            "cross-account-access", "config-auto-remediation", "secrets-rotation", "org-guardrails",
            "s3-encryption-audit",
            "bastionless-access", "static-site-cloudfront", "hybrid-multi-vpc", "network-troubleshooting",
        ],
    },
]

META_RE = re.compile(r"<!--\s*(title|category|lead):\s*(.*?)\s*-->\s*")


def load_pages(col, warnings):
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
        })
    order = {s: i for i, s in enumerate(col["order"])}
    pages.sort(key=lambda p: (order.get(p["slug"], len(order)), p["title"]))
    return pages


def grouped(col, pages):
    cats = list(col["categories"])
    for p in pages:
        if p["category"] not in cats:
            cats.append(p["category"])
    return [(c, [p for p in pages if p["category"] == c]) for c in cats
            if any(p["category"] == c for p in pages)]


def head(title, prefix):
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{prefix}css/style.css">
<link rel="icon" type="image/png" href="{prefix}icons/favicon-32.png">
<link rel="apple-touch-icon" href="{prefix}icons/apple-touch-icon.png">
<link rel="manifest" href="{prefix}manifest.webmanifest">
<meta name="theme-color" content="#1f2937">
</head>
<body>
"""


def header(prefix, current=None):
    cur = ' class="current"'
    links = "".join(
        f'<a href="{prefix}{c["key"]}/index.html"{cur if c["key"] == current else ""}>'
        f'{c["label"]}</a>' for c in COLLECTIONS)
    links += f'<a href="{prefix}links.html"{cur if current == "links" else ""}>リンク集</a>'
    return f"""<header class="site-header">
  <div class="inner">
    <a class="site-title" href="{prefix}index.html">{SITE_TITLE}</a>
    <nav class="site-nav">{links}</nav>
  </div>
</header>
"""


TAIL = "</body>\n</html>\n"


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
    return (head(f"{p['title']} | {SITE_TITLE}", "../")
            + header("../", col["key"])
            + "<main>\n<div class=\"page-head\">\n"
            + f'  <span class="category">{html.escape(p["category"])}</span>\n'
            + f'  <h1>{html.escape(p["title"])}</h1>\n'
            + (f'  <p class="lead">{p["lead"]}</p>\n' if p["lead"] else "")
            + "</div>\n" + p["body"] + "\n" + pager(prev, nxt) + "</main>\n" + TAIL)


def render_collection_index(col, pages):
    parts = [head(f"{col['label']} | {SITE_TITLE}", "../"), header("../", col["key"]), "<main>\n",
             f'<div class="page-head"><h1>{col["label"]}</h1></div>\n']
    if not pages:
        parts.append('<p class="empty-state">準備中です。</p>\n')
    groups = grouped(col, pages)
    if col.get("search") and pages:
        parts.append('<div class="toc-search">\n'
                     '  <input type="search" id="toc-q" placeholder="サービス名・キーワードで絞り込み(例: VPN、ログ、コンテナ)"'
                     ' aria-label="絞り込み" autocomplete="off">\n'
                     '  <span class="toc-hits" id="toc-hits"></span>\n</div>\n')
    descs = col.get("category_desc", {})
    compact = col.get("compact")
    for i, (category, items) in enumerate(groups, 1):
        parts.append(f'<section class="toc-category" id="cat{i}">\n<h2>{html.escape(category)} '
                     f'<span class="count">({len(items)})</span></h2>\n')
        if category in descs:
            parts.append(f'<p class="cat-desc">{html.escape(descs[category])}</p>\n')
        parts.append(f'<ul class="{"chip-list" if compact else "card-list"}">\n')
        for p in items:
            # 一覧には表示しない lead・カテゴリも検索対象に含める
            keys = " ".join([p["title"], p["slug"], category, re.sub(r"<[^>]+>", "", p["lead"])])
            if compact:
                inner = f'<span class="name">{html.escape(p["title"])}</span>'
            else:
                inner = (f'<span class="name">{html.escape(p["title"])}</span>'
                         f'<span class="desc">{p["lead"]}</span>')
            parts.append(f'  <li data-keys="{html.escape(keys.lower())}"><a href="{p["slug"]}.html">{inner}</a></li>\n')
        parts.append("</ul>\n</section>\n")
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
      sec.querySelector("h2 .count").textContent = "(" + n + ")";
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


def render_top(counts):
    parts = [head(SITE_TITLE, ""), header(""), "<main>\n",
             f'<div class="page-head"><h1>{SITE_TITLE}</h1></div>\n<ul class="card-list top-cards">\n']
    for c in COLLECTIONS:
        n = counts[c["key"]]
        badge = f"{n}ページ" if n else "準備中"
        parts.append(f'  <li><a href="{c["key"]}/index.html"><span class="name">{c["label"]}'
                     f'<span class="badge">{badge}</span></span><span class="desc">{c["desc"]}</span></a></li>\n')
    parts.append('  <li><a href="links.html"><span class="name">リンク集</span>'
                 '<span class="desc">試験ガイドや各サービスの公式ページ・ドキュメントへのリンク</span></a></li>\n')
    parts += ["</ul>\n</main>\n", TAIL]
    return "".join(parts)


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
            rows.append(f'<tr><td><a href="services/{p["slug"]}.html">{html.escape(p["title"])}</a></td>'
                        f'<td>{cells[0]}</td><td>{cells[1]}</td></tr>\n')
        rows.append("</table></div>\n")
    body = META_RE.sub("", text).strip().replace("<!-- SERVICE_LINKS -->", "".join(rows))
    title = meta.get("title", "リンク集")
    return (head(f"{title} | {SITE_TITLE}", "") + header("", "links")
            + f'<main>\n<div class="page-head">\n  <h1>{html.escape(title)}</h1>\n'
            + (f'  <p class="lead">{meta["lead"]}</p>\n' if meta.get("lead") else "")
            + "</div>\n" + body + "\n</main>\n" + TAIL)


def main():
    warnings, counts, loaded = [], {}, {}
    for col in COLLECTIONS:
        pages = load_pages(col, warnings)
        counts[col["key"]] = len(pages)
        loaded[col["key"]] = pages
        out_dir = OUT / col["key"]
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True)
        for i, p in enumerate(pages):
            (out_dir / f"{p['slug']}.html").write_text(render_page(col, pages, i), encoding="utf-8")
        (out_dir / "index.html").write_text(render_collection_index(col, pages), encoding="utf-8")
    (OUT / "index.html").write_text(render_top(counts), encoding="utf-8")
    (OUT / "links.html").write_text(render_links(loaded["services"], warnings), encoding="utf-8")
    print("built " + ", ".join(f"{c['label']} {counts[c['key']]}" for c in COLLECTIONS))
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
