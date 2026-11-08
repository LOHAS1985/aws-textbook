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

from checks import check_pages, check_question_data, thin_page_report
from diagrams import render_figures, text_width

ROOT = Path(__file__).parent
SRC = ROOT / "src"
OUT = ROOT / "book"
GUIDE_REF_RE = re.compile(r'href="\.\./(services|terms|usecases)/([\w-]+)\.html"')
EXAMS_DIR = SRC / "exams"  # 試験別(試験ごとのフォルダ: exam.json・scope.html・roadmap.html・questions.html)
EXAM_LEVELS = [("foundational", "基礎"), ("associate", "アソシエイト"), ("professional", "プロフェッショナル"),
               ("specialty", "スペシャリティ")]
# 試験別の表示に使う仮想のコレクション(一覧はないが、ページの描画・検査で既存の仕組みを使う)
EXAM_COL = {"key": "exams", "label": "試験別", "desc": "AWS認定の試験ごとに、学習範囲・ロードマップと参考書・問題集をまとめる",
            "categories": [], "order": None}
QUESTION_COL = {"key": "questions", "label": "問題集", "desc": "試験別のシナリオ型問題で、AWSの知識と選択理由を確認",
                "categories": [], "script": "quiz.js", "order": None}
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
            "機械学習と人工知能": "機械学習・生成AIのデータ準備、モデル、検索",
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
            "ec2", "auto-scaling", "image-builder", "lambda", "batch", "elastic-beanstalk",
            "ecs", "eks", "ecr", "copilot",
            "s3", "ebs", "efs", "fsx", "backup", "elastic-disaster-recovery", "storage-gateway",
            "rds", "aurora", "dynamodb", "documentdb", "keyspaces", "neptune", "elasticache", "memorydb",
            "vpc", "ipam", "transit-gateway", "site-to-site-vpn", "client-vpn", "direct-connect",
            "route53", "dns-firewall", "application-recovery-controller",
            "elb", "cloudfront", "global-accelerator", "api-gateway",
            "iam", "identity-center", "sts", "organizations", "directory-service", "cognito", "kms",
            "secrets-manager", "acm", "private-ca", "guardduty", "inspector", "macie", "security-hub",
            "waf", "shield", "network-firewall", "security-agent", "artifact",
            "cloudwatch", "cloudtrail", "config", "well-architected-tool", "systems-manager", "cloudformation", "cdk",
            "control-tower", "trusted-advisor", "health-dashboard", "compute-optimizer", "service-catalog", "ram", "resource-groups",
            "managed-grafana", "managed-prometheus", "devops-agent", "devops-guru",
            "cost-explorer", "budgets", "cost-and-usage-reports", "savings-plans",
            "sqs", "sns", "eventbridge", "step-functions", "appsync",
            "codepipeline", "codebuild", "codedeploy", "codeartifact", "xray", "cloudshell", "amplify", "kiro",
            "sam", "sdk", "database-encryption-sdk",
            "athena", "glue", "databrew", "lake-formation", "redshift", "emr", "msk", "managed-flink", "quick",
            "data-exchange", "sagemaker-unified-studio", "kinesis", "data-firehose", "opensearch", "bedrock",
            "kendra", "amazon-q", "sagemaker-ai", "datasync", "application-discovery", "application-migration", "snow-family",
            "dms", "transfer-family", "ses",
            "appflow", "mwaa",
        ],
    },
    {
        "key": "terms",
        "label": "用語",
        "desc": "AWSを学ぶうえで押さえておきたい用語の解説",
        "categories": ["AWSの基礎", "ネットワーク", "セキュリティ・認証", "ストレージ", "設計・運用", "サービスの選び方"],
        "search": "用語・キーワードで絞り込み(例: IP、暗号化、DNS)",
        "rows": True,  # 一覧は1行に1ページ(概要は出さない)
        "order": [
            "shared-responsibility", "region-az", "default-vpc", "root-user", "access-methods", "arn", "tags",
            "pricing-basics", "support-plans", "service-quotas", "sla-availability", "managed-serverless",
            "well-architected", "compliance-artifact", "json-yaml",
            "dns", "dns-record-types", "hosted-zone", "cidr", "route-table", "nacl-security-group", "vpc-flow-logs", "vpc-traffic-mirroring",
            "eni-elastic-ip", "vpc-endpoint", "vpc-peering",
            "inbound-traffic", "outbound-traffic", "port-numbers", "http-status-codes",
            "iam-policy-evaluation", "iam-roles-credentials", "instance-profile", "iam-passrole", "encryption", "tls-termination", "oidc", "spf",
            "storage-types", "performance-metrics",
            "high-availability-scaling", "deploy-strategies", "dr-strategies", "circuit-breaker",
            "cloudwatch-alarm-states", "event-driven-remediation", "cron-rate-expressions", "throttling-retry", "terraform-git",
            "monitoring-logging-comparison", "messaging-comparison", "caching-comparison",
            "data-engineering-basics", "data-store-selection",
            "data-quality", "open-table-formats", "vector-search", "data-governance",
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
        # src/news/YYYY-MM-DD-NN.html を発表(トピック)ごとに、クラウドの定期エージェントが追加する。
        # NN はその日の中の番号(1から)。category は「YYYY年M月」。新しい日付から順に並べ、同じ日の中は番号の順
        "key": "news",
        "label": "ニュース",
        "desc": "AWSの新しい発表を、図解つきで分かりやすく解説(毎日更新)",
        "categories": [],
        "search": "サービス名・キーワードで絞り込み(例: Lambda、料金、東京リージョン)",
        "order": [],
        "newest_first": True,
        "rows": True,  # 一覧は1行に1ページ(概要は出さない)
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

META_RE = re.compile(r"<!--\s*(title|category|lead|verified):\s*(.*?)\s*-->\s*")


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
        page_date = ""
        if col["key"] == "news":
            # ニュースの日付はファイル名(YYYY-MM-DD-NN)から作り、タイトル(見出しだけ)とは分けて表示する
            if NEWS_SLUG_RE.fullmatch(slug):
                y, m, d = slug[:10].split("-")
                page_date = f"{int(y)}年{int(m)}月{int(d)}日"
            else:
                warnings.append(f"{where}: ニュースのファイル名は YYYY-MM-DD-NN.html にします(NN は同じ日の中の番号)")
            if "のAWSニュース" in meta.get("title", ""):
                warnings.append(f"{where}: ニュースの title には日付を書きません(主な発表だけを書く)")
        pages.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "category": meta.get("category", "その他"),
            "lead": meta.get("lead", ""),
            "verified": meta.get("verified", ""),  # 料金・上限などを公式ドキュメントで確認した日(YYYY-MM-DD)
            "date": page_date,
            "raw": text,  # 検査用(行番号がファイルと一致するよう、メタ情報も含める)
            "body": figure_legend(render_figures(body, where, warnings)),
            "updated": updated.get(f"src/{col['key']}/{path.name}", int(time.time())),
        })
    order = {s: i for i, s in enumerate(col["order"])}
    pages.sort(key=lambda p: (order.get(p["slug"], len(order)), p["title"]))
    if col.get("newest_first"):
        # 新しい日付から。同じ日の中は番号の順(注目の発表が先)
        pages.sort(key=lambda p: news_sort_key(p["slug"]), reverse=True)
    return pages


NEWS_SLUG_RE = re.compile(r"(\d{4}-\d{2}-\d{2})-(\d{2})")


def news_sort_key(slug):
    m = NEWS_SLUG_RE.fullmatch(slug)
    return (m.group(1), -int(m.group(2))) if m else ("", 0)


DEA_C01_SKILL_COUNTS = {
    1: {1: 12, 2: 10, 3: 4, 4: 11},
    2: {1: 8, 2: 6, 3: 6, 4: 6},
    3: {1: 9, 2: 6, 3: 8, 4: 5},
    4: {1: 7, 2: 6, 3: 4, 4: 5, 5: 7},
}


def add_question_bank(page, src_dir):
    """試験別の本文に、分野ごとの追加問題データをHTMLとして組み込む。"""
    title_path = src_dir / "dea-c01-titles.json"
    titles = json.loads(title_path.read_text(encoding="utf-8"))
    if set(titles) != {str(question_id) for question_id in range(1, 101)}:
        raise ValueError(f"{title_path}: 問1〜100の選択画面用タイトルが必要です")
    page = annotate_existing_questions(page, titles)
    questions = {domain: [] for domain in range(1, 5)}
    question_titles = dict(titles)
    for domain in questions:
        path = src_dir / f"domain-{domain}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        valid_skills = {
            f"{domain}.{task}.{number}"
            for task, count in DEA_C01_SKILL_COUNTS[domain].items()
            for number in range(1, count + 1)
        }
        for question in data:
            question_id = str(question["id"])
            title = question.get("title", titles.get(question_id))
            if not title:
                raise ValueError(f"{path}: 問{question_id}の選択画面用タイトルがありません")
            if int(question_id) > 100:
                skill = question.get("skill", "")
                if skill not in valid_skills:
                    raise ValueError(f"{path}: 問{question_id}のSkill「{skill}」が公式ガイドにありません")
                question_titles[question_id] = title
            questions[domain].append(render_question(question, domain, title))

    expected_ids = {str(question_id) for question_id in range(1, 201)}
    if set(question_titles) != expected_ids:
        raise ValueError(f"{src_dir}: 問1〜200の選択画面用タイトルが必要です")
    if len(set(question_titles.values())) != len(question_titles):
        raise ValueError(f"{src_dir}: 選択画面用タイトルが重複しています")

    for domain in range(1, 5):
        rendered = "\n".join(questions[domain])
        if not rendered:
            continue
        if domain < 4:
            next_heading = f'<div class="quiz-domain">\n<h3 id="domain{domain + 1}"'
            pos = page.find(next_heading)
            if pos < 0:
                raise ValueError(f"{src_dir.name}: 分野{domain + 1}の見出しがありません")
            insertion = page.rfind("</div>", 0, pos)
        else:
            marker = '\n</div>\n\n<div class="quiz-actions">'
            insertion = page.find(marker)
            if insertion < 0:
                raise ValueError(f"{src_dir.name}: 問題フォームの終了位置がありません")
        page = page[:insertion] + "\n" + rendered + "\n" + page[insertion:]
    return re.sub(r'<h3 id="domain[1-4]">.*?</h3>\s*', "", page)


def annotate_existing_questions(page, titles):
    domain_headings = list(re.finditer(r'<h3 id="domain([1-4])"', page))
    matches = list(re.finditer(r'(<section class="quiz-q")([^>]*)>', page))
    for question_number, match in reversed(list(enumerate(matches, 1))):
        domain = max(
            (heading for heading in domain_headings if heading.start() < match.start()),
            key=lambda heading: heading.start(),
        ).group(1)
        attrs = match.group(2)
        attrs += (f' data-id="{question_number}" data-domain="{domain}"'
                  f' data-difficulty="intermediate" data-title="{html.escape(titles[str(question_number)], quote=True)}"')
        page = page[:match.start(2)] + attrs + page[match.end(2):]
    return page


def render_question(question, domain, title):
    """問題データ1件を、JavaScriptなしでも読める選択問題HTMLにする。"""
    qid = question["id"]
    answer = question["answer"]
    answer_labels = "、".join(value.upper() for value in answer)
    input_type = "radio" if question["type"] == "single" else "checkbox"
    difficulty_labels = {"basic": "基礎", "intermediate": "標準", "advanced": "応用"}
    choices = []
    incorrect = []
    correct_reason = ""
    for choice in question["choices"]:
        value = choice["id"]
        choices.append(
            f'<li><label><input type="{input_type}" name="q{qid}" value="{html.escape(value, quote=True)}"> '
            f'{html.escape(choice["text"])}</label></li>')
        if value in answer:
            correct_reason = choice["why"]
        else:
            incorrect.append(f'<li><strong>{html.escape(value.upper())}:</strong> {html.escape(choice["why"])}</li>')
    links = "".join(
        f'<a href="{html.escape(link["href"], quote=True)}">{html.escape(link["label"])}</a>'
        for link in question.get("links", []))
    links = f'<p>{" / ".join([links])}</p>' if links else ""
    instruction = html.escape(question["instruction"])
    choice_html = "\n".join(choices)
    incorrect_html = "\n".join(incorrect)
    return (
        f'<section class="quiz-q" data-id="{qid}" data-title="{html.escape(title, quote=True)}" data-domain="{domain}" '
        f'data-difficulty="{question["difficulty"]}" data-answer="{",".join(answer)}" '
        f'data-type="{question["type"]}">\n'
        f'<h4>問{qid} <span class="quiz-difficulty">{difficulty_labels[question["difficulty"]]}</span></h4>\n'
        f'<p class="quiz-stem">{html.escape(question["stem"])}</p>\n'
        f'<fieldset class="quiz-options"><legend>{instruction}</legend>\n'
        f'<ol class="quiz-choices">\n{choice_html}\n</ol></fieldset>\n'
        f'<details class="quiz-answer"><summary>答えと解説を確認</summary>\n'
        f'<p><strong>正解: {answer_labels}</strong></p>\n'
        f'<p>{html.escape(correct_reason)}</p>\n<ul>\n{incorrect_html}\n</ul>\n{links}'
        f'</details>\n</section>')


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


# アイコンがない項目の空き(並べた名前の開始位置をそろえる。svc-icon-blank の幅はアイコンの 28px に合わせる)
BLANK_ICON = '<span class="svc-icon-blank" aria-hidden="true"></span>'


def fmt_date(ts):
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def header(prefix, current=None):
    cur = ' class="current"'
    links = "".join(
        f'<a href="{prefix}{c["key"]}/index.html"{cur if c["key"] == current else ""}>'
        f'{c["label"]}</a>' for c in COLLECTIONS if c.get("nav", True))
    links += f'<a href="{prefix}exams/index.html"{cur if current == "exams" else ""}>試験別</a>'
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
                f'<span class="label">{label}{" " + p["date"] if p["date"] else ""}</span>'
                f'{html.escape(p["title"])}</a>')
    return ('<nav class="pager">\n'
            f'  {link(prev, "prev", "← 前へ")}\n'
            '  <a class="toc" href="index.html">目次へ戻る</a>\n'
            f'  {link(nxt, "next", "次へ →")}\n'
            '</nav>\n')


def verified_label(ymd):
    y, m, d = ymd.split("-")
    return f"{int(y)}年{int(m)}月{int(d)}日"


def render_page(col, pages, i, prefix="../"):
    p = pages[i]
    prev = pages[i - 1] if i > 0 else None
    nxt = pages[i + 1] if i + 1 < len(pages) else None
    cat_no = [c for c, _ in grouped(col, pages)].index(p["category"]) + 1
    body, items = add_heading_ids(stack_tables(p["body"]))
    icon = service_icon(p["slug"], prefix, 56) if col["key"] == "services" else ""
    title = f"{p['title']} | {p['date']}のAWSニュース" if p["date"] else p["title"]
    quiz_page = col["key"] == "questions"
    page_head = ""
    if not quiz_page:
        page_head = (f'<div class="page-head hero"{cat_style(col, p["category"])}>\n'
                     + (f'  <div class="hero-icon">{icon}</div>\n' if icon else "")
                     + '  <div class="hero-text">\n'
                     + f'  <a class="category" href="index.html#cat{cat_no}">{html.escape(p["category"])}</a>\n'
                     + (f'  <p class="news-date"><time datetime="{p["slug"][:10]}">{p["date"]}</time>のAWSニュース</p>\n'
                        if p["date"] else "")
                     + f'  <h1>{html.escape(p["title"])}</h1>\n'
                     + (f'  <p class="lead">{p["lead"]}</p>\n' if p["lead"] else "")
                     + f'  <p class="updated">最終更新:<time datetime="{fmt_date(p["updated"])}">'
                     + f'{fmt_date(p["updated"])}</time></p>\n'
                     + (f'  <p class="updated">内容の確認:{verified_label(p["verified"])}</p>\n' if p["verified"] else "")
                     + "  </div>\n</div>\n")
    main_class = ' class="quiz-page"' if quiz_page else ""
    return (head(f"{title} | {SITE_TITLE}", prefix, p["lead"])
            + header(prefix, col["key"])
            + f'<main{main_class}>\n' + page_head + page_toc(items) + body + "\n" + p.get("graph", "")
            + pager(prev, nxt) + "</main>\n" + TO_TOP
            + exercise_graph(col, p) + page_script(col, prefix) + TAIL)


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


def page_script(col, prefix="../"):
    """コレクション専用のスクリプト(構成演習の答え合わせなど)を読み込むタグ。"""
    return f'<script src="{prefix}js/{col["script"]}" defer></script>\n' if col.get("script") else ""


def cat_style(col, category):
    """カテゴリの色を CSS変数 --cat として渡す属性(色が決まっていなければ空)。"""
    color = col.get("category_colors", {}).get(category)
    return f' style="--cat:{color}"' if color else ""


def render_collection_index(col, pages, loaded):
    parts = [head(f"{col['label']} | {SITE_TITLE}", "../", col["desc"]), header("../", col["key"]), "<main>\n",
             f'<div class="page-head"><h1>{col["label"]}</h1><p class="lead">{col["desc"]}</p></div>\n']
    if col["key"] == "questions":
        parts.append('<p class="cat-desc" id="quiz-storage-note" hidden>このブラウザーでは保存済みの成績を読み込めません。</p>\n')
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
            parts.append(f'<ul class="{"row-list" if col.get("rows") else "card-list"}">\n')
        for p in items:
            # 一覧には表示しない lead・カテゴリも検索対象に含める
            extra = question_search_text(p) if col["key"] == "questions" else ""
            keys = search_keys(p, category, extra)
            if compact:
                tip = html.escape(p["title"] + (":" + plain(p["lead"]) if p["lead"] else ""))
                inner = (f'{service_icon(p["slug"], "../", 28) or BLANK_ICON}'
                         f'<span class="name">{html.escape(p["title"])}</span><span class="go" aria-hidden="true">›</span>')
                parts.append(f'  <li data-keys="{html.escape(keys)}"><a href="{p["slug"]}.html" '
                             f'title="{tip}">{inner}</a></li>\n')
            elif col.get("rows"):
                # 1行に1ページ。概要(lead)は一覧に出さず、検索の対象にだけ含める
                inner = ((f'<time class="date" datetime="{p["slug"][:10]}">{p["date"]}</time>' if p["date"] else "")
                         + f'<span class="name">{html.escape(p["title"])}</span>')
                parts.append(f'  <li data-keys="{html.escape(keys)}"><a href="{p["slug"]}.html">{inner}</a></li>\n')
            else:
                inner = ((f'<time class="date" datetime="{p["slug"]}">{p["date"]}</time>' if p["date"] else "")
                         + f'<span class="name">{html.escape(p["title"])}</span>'
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
    return norm(" ".join([p["title"], p["slug"], p.get("date", ""), category, plain(p["lead"]), " ".join(p.get("uses", [])), extra]))


def question_search_text(p):
    """問題集では、問題文・選択肢・解説の語句でも試験ページを検索できるようにする。"""
    return " ".join(plain(p["body"]).split())


# 検索で同じものとして扱う言い換え(略称・英語名・日本語の言い方)。
# 入力した語がどれかと一致すると、同じグループの語のどれかを含むページも見つかる。小文字・半角で書く
SYNONYMS = [
    ["devops guru", "devops-guru", "devopsguru", "異常検知", "インサイト"],
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
    ["aws glue", "glue", "glue data catalog", "データカタログ", "crawler", "クローラー", "etl"],
    ["aws glue databrew", "glue databrew", "databrew", "データ準備", "レシピ"],
    ["lake formation", "lakeformation", "データレイク", "fine-grained access control", "細粒度アクセス制御"],
    ["redshift", "データウェアハウス", "data warehouse", "spectrum", "redshift serverless"],
    ["emr", "elastic mapreduce", "hadoop", "spark", "分散処理"],
    ["aws dms", "database migration service", "データベース移行", "継続的レプリケーション", "cdc"],
    ["msk", "managed streaming for apache kafka", "apache kafka", "kafka", "トピック", "パーティション"],
    ["appflow", "saas", "saas連携", "データ連携"],
    ["mwaa", "managed workflows for apache airflow", "airflow", "dag", "有向非巡回グラフ"],
    ["managed service for apache flink", "amazon managed service for apache flink", "flink", "ストリーム処理"],
    ["aws batch", "batch", "バッチジョブ", "ジョブキュー", "job queue"],
    ["amazon quick", "quicksight", "quick sight", "bi", "business intelligence", "ダッシュボード"],
    ["aws data exchange", "data exchange", "データセットの共有", "データ購読", "データグラント"],
    ["sagemaker unified studio", "unified studio", "sagemaker catalog", "domain unit", "ドメインユニット", "プロジェクト"],
    ["amazon sagemaker ai", "sagemaker ai", "sagemaker canvas", "data wrangler", "feature store"],
    ["amazon kendra", "kendra", "エンタープライズ検索", "自然言語検索"],
    ["amazon documentdb", "documentdb", "docdb", "mongodb互換", "ドキュメントデータベース"],
    ["amazon keyspaces", "keyspaces", "apache cassandra", "cql", "ワイドカラム"],
    ["amazon neptune", "neptune", "グラフデータベース", "graph database", "gremlin", "opencypher", "sparql"],
    ["aws application discovery service", "application discovery", "agentless collector", "サーバー検出", "移行計画"],
    ["aws transform mgn", "aws application migration service", "application migration service", "mgn", "ブロックレベルレプリケーション"],
    ["aws snow family", "snow family", "snowball edge", "aws snowball", "オフラインデータ転送"],
    ["amazon q", "q business", "amazon q business", "q developer", "amazon q developer", "generative ai assistant"],
    ["aws well-architected tool", "well-architected tool", "well architected tool", "ワークロードレビュー"],
    ["aws transfer family", "transfer family", "sftp", "ftps", "as2", "ファイル転送"],
    ["etl", "extract transform load", "抽出", "変換", "ロード", "バッチ", "ストリーミング", "リプレイ"],
    ["データ品質", "data quality", "データ検証", "データサンプリング", "データスキュー"],
    ["apache iceberg", "iceberg", "オープンテーブル形式", "open table format", "スキーマ進化", "schema evolution"],
    ["ベクトル検索", "vector search", "hnsw", "ivf", "embedding", "埋め込み", "ベクトル化"],
    ["データガバナンス", "data governance", "データリネージ", "lineage", "データ共有", "データ主権", "匿名化"],
    ["sts", "assumerole", "一時的な認証情報", "ロールの引き受け"],
    ["cognito", "ユーザー認証", "サインイン"],
    ["api gateway", "apigw", "rest api"],
    ["imds", "imdsv2", "インスタンスメタデータ", "instance metadata"],
    ["インスタンスプロファイル", "instance profile", "instanceprofile", "ec2のロール"],
    ["ホストゾーン", "hosted zone", "パブリックホストゾーン", "プライベートホストゾーン", "phz"],
    ["resolver", "リゾルバー", "インバウンドエンドポイント", "アウトバウンドエンドポイント", "転送ルール", "条件付きフォワーダー"],
    ["トラフィックミラーリング", "traffic mirroring", "ミラーリング", "パケットキャプチャ", "vxlan", "ids"],
    ["ami", "マシンイメージ", "ゴールデンイメージ", "image builder"],
    ["az", "アベイラビリティーゾーン", "availability zone"],
    ["リージョン", "region"],
    ["cidr", "ipアドレス", "ip address", "サブネットマスク", "ipam"],
    ["踏み台", "bastion", "ssh", "rdp"],
    ["パッチ", "patch", "更新プログラム"],
    ["budgets", "aws budgets", "予算", "予算管理", "予算アラート", "予算アクション"],
    ["elastic disaster recovery", "drs", "災害復旧", "ディザスタリカバリ", "ステージングエリア"],
    ["resource groups", "リソースグループ", "tag editor", "タグエディター", "タグ編集", "resource tagging api"],
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


def search_fields(p, headings, extra=""):
    """トップの全ページ検索の根拠に使う項目。項目ごとの重みは SITE_SEARCH_SCRIPT の FIELDS と対応させる。
    本文の全文は入れない(検索データが大きくなりすぎるため。本文の内容は小見出し・説明・関連サービスで拾う)。"""
    return {"uses": p.get("uses", []), "heading": headings, "lead": plain(p["lead"]),
            "category": p["category"], "other": " ".join([p["slug"], p.get("date", ""), extra])}


def render_top(loaded, exams, exam_pages):
    desc = "AWS認定の学習用に、AWS共通のサービス・用語・運用シナリオと、試験別の学習範囲・問題集をまとめた教科書"
    parts = [head(SITE_TITLE, "", desc), header(""), "<main>\n",
             f'<div class="page-head"><h1>{SITE_TITLE}</h1><p class="lead">{desc}</p></div>\n']

    # 全ページ横断の検索(タイトル・説明・カテゴリ・小見出しが対象)
    index = []
    for c in COLLECTIONS:
        for p in loaded[c["key"]]:
            headings = [plain(h) for h in re.findall(r"<h3[^>]*>(.*?)</h3>", p["body"], re.S)]
            extra = question_search_text(p) if c["key"] == "questions" else ""
            icon = c["key"] == "services" and (ICON_DIR / f'{p["slug"]}.svg').exists()
            index.append({"t": p["title"], "c": c["label"], "u": f'{c["key"]}/{p["slug"]}.html',
                          "i": f'icons/services/{p["slug"]}.svg' if icon else "",
                          "d": plain(p["lead"]), "g": c["key"],
                          "f": search_fields(p, headings, extra)})
    for c in (EXAM_COL, QUESTION_COL):
        for p in loaded[c["key"]]:
            headings = [plain(h) for h in re.findall(r"<h3[^>]*>(.*?)</h3>", p["body"], re.S)]
            extra = question_search_text(p) if c["key"] == "questions" else ""
            index.append({"t": p["title"], "c": f'{c["label"]}(試験別)', "u": p["path"] + ".html", "i": "",
                          "d": plain(p["lead"]), "g": "exams", "f": search_fields(p, headings, extra)})
    parts.append('<div class="toc-search site-search" id="search">\n'
                 '  <input type="search" id="site-q" placeholder="全ページを検索(例: ロードバランサー、IMDSv2、DR)"'
                 ' aria-label="全ページを検索" autocomplete="off">\n'
                 '  <span class="toc-hits" id="site-hits"></span>\n</div>\n'
                 '<div class="prefs-seg search-kinds" id="site-kinds" role="group" aria-label="種類で絞り込み" hidden>\n'
                 + "".join(f'  <button type="button" data-g="{g}" aria-pressed="{str(g == "all").lower()}">{label}</button>\n'
                           for g, label in SEARCH_KINDS)
                 + '</div>\n'
                 '<ul class="search-results" id="site-results" hidden></ul>\n'
                 + SITE_SEARCH_SCRIPT.replace("__INDEX__", json.dumps(index, ensure_ascii=False))
                 .replace("__HELPERS__", search_helpers()))

    parts.append('<h2>AWS共通</h2>\n<ul class="card-list top-cards">\n')
    for c in COLLECTIONS:
        n = len(loaded[c["key"]])
        badge = f"{n}ページ" if n else "準備中"
        parts.append(f'  <li><a href="{c["key"]}/index.html"><span class="name">{c["label"]}'
                     f'<span class="badge">{badge}</span></span><span class="desc">{c["desc"]}</span></a></li>\n')
    parts.append('  <li><a href="links.html"><span class="name">公式リンク</span>'
                 '<span class="desc">試験ガイドや各サービスの公式ページ・ドキュメントへのリンク</span></a></li>\n')
    parts.append("</ul>\n")
    parts.append('<h2>試験別</h2>\n<ul class="card-list top-cards">\n'
                 f'  <li><a href="exams/index.html"><span class="name">AWS認定の試験別<span class="badge">{len(exams)}資格</span></span>'
                 '<span class="desc">試験ごとの学習範囲・ロードマップと参考書・問題集</span></a></li>\n</ul>\n')

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
            parts.append(f'  <li><time datetime="{p["slug"][:10]}">{p["slug"][:10]}</time>'
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


# トップの全ページ検索(スペース区切りのAND検索。項目ごとの重みで点数を付け、点数の高い順に並べ、根拠を出す)
SITE_SEARCH_SCRIPT = """<script>
(function () {
  var pages = __INDEX__;
  var q = document.getElementById("site-q");
  var hits = document.getElementById("site-hits");
  var list = document.getElementById("site-results");
  var kinds = document.getElementById("site-kinds");
  var kind = "all";
__HELPERS__
  if (location.hash === "#search") q.focus();
  kinds.hidden = false;
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  // 項目ごとの重み(大きいほど強い一致)。語ごとに最も強い一致を採り、全語に一致したページだけを点数順に出す
  var FIELDS = [
    {name: "title", label: "タイトル", w: 10, texts: function (p) { return [p.t]; }},
    {name: "uses", label: "関連サービス", w: 6, texts: function (p) { return p.f.uses; }},
    {name: "heading", label: "小見出し", w: 4, texts: function (p) { return p.f.heading; }},
    {name: "lead", label: "説明", w: 4, texts: function (p) { return p.f.lead ? [p.f.lead] : []; }},
    {name: "category", label: "カテゴリ", w: 2, texts: function (p) { return [p.f.category]; }},
    {name: "other", label: "その他", w: 1, texts: function (p) { return [p.f.other]; }}
  ];
  // 言い換えは元の語より弱い重みにする(直接の一致が言い換えより先に来る)。SYN は build.py の SYNONYMS
  function variants(w) {
    var out = [{t: w, f: 1, o: ""}];
    SYN.forEach(function (g) {
      if (g.indexOf(w) < 0) return;
      g.forEach(function (a) { if (a !== w) out.push({t: a, f: 0.5, o: w}); });
    });
    return out;
  }
  // 短い英字(dr・ha など)は、ほかの語の一部に当たらないよう単語として探す
  function hasTerm(text, term) {
    var s = norm(text || "");
    return /^[a-z0-9]{1,3}$/.test(term) ? new RegExp("(^|[^a-z0-9])" + term + "([^a-z0-9]|$)").test(s) : s.indexOf(term) >= 0;
  }
  // 説明・その他は長いので、一致した語の前後だけを根拠に出す
  function snip(text, term) {
    var s = norm(text), i = s.indexOf(term);
    if (i < 0) return s.slice(0, 30);
    var a = Math.max(0, i - 12);
    return (a > 0 ? "…" : "") + s.substr(a, term.length + 30) + "…";
  }
  function score(p, words) {
    var total = 0, why = [];
    for (var i = 0; i < words.length; i++) {
      var best = null;
      variants(words[i]).forEach(function (v) {
        FIELDS.forEach(function (f) {
          f.texts(p).forEach(function (t) {
            if (!hasTerm(t, v.t)) return;
            var s = f.w * v.f;
            if (!best || s > best.s) best = {s: s, f: f, t: t, v: v};
          });
        });
      });
      if (!best) return null;
      total += best.s;
      var shown = best.f.name === "lead" || best.f.name === "other" ? snip(best.t, best.v.t) : best.t;
      why.push((best.v.o ? "言い換え「" + best.v.o + "→" + best.v.t + "」・" : "") + best.f.label + "「" + shown + "」");
    }
    return {s: total, why: why};
  }
  function apply() {
    var words = norm(q.value).trim().split(/\\s+/).filter(Boolean);
    if (!words.length) { list.hidden = true; hits.textContent = ""; return; }
    var found = [];
    pages.forEach(function (p, n) {
      if (kind !== "all" && p.g !== kind) return;
      var r = score(p, words);
      if (r) found.push({p: p, s: r.s, why: r.why, n: n});
    });
    found.sort(function (a, b) { return b.s - a.s || a.n - b.n; });
    hits.textContent = found.length + "件" + (found.length > 30 ? "(先頭30件を表示)" : "");
    list.innerHTML = found.slice(0, 30).map(function (x) {
      var p = x.p;
      var icon = p.i ? '<img class="svc-icon" src="' + p.i + '" alt="" width="20" height="20">' : "";
      return '<li><a href="' + p.u + '"><span class="badge">' + esc(p.c) + '</span>' + icon + '<span class="name">' +
        esc(p.t) + '</span><span class="desc">' + esc(p.d) + '</span>' +
        '<span class="why">根拠: ' + x.why.slice(0, 3).map(function (w) { return esc(w); }).join(" / ") + '</span></a></li>';
    }).join("") || '<li class="empty-state">該当するページがありません。</li>';
    list.hidden = false;
  }
  // 種類のチップ(すべて・サービス・用語…)で結果を絞る
  kinds.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b) return;
    kind = b.getAttribute("data-g");
    kinds.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
    apply();
  });
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


def write_news_day_redirects(pages):
    """日ごとのページだった頃のURL(book/news/YYYY-MM-DD.html)から、その日の最初の発表のページへ転送する。"""
    seen = set()
    for p in pages:
        day = p["slug"][:10]
        if day in seen:
            continue
        seen.add(day)
        (OUT / "news" / f"{day}.html").write_text(
            redirect_html(f"{p['slug']}.html", f"{p['date']}のAWSニュース"), encoding="utf-8")


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


EXAM_STATUS_LABEL = {"beta": "ベータ版(試験の内容は変わることがあります)", "retiring": "廃止予定", "retired": "廃止済み"}


def load_exams():
    """試験別のフォルダ(src/exams/{試験ID}/)から、試験の情報(exam.json)を読む。試験は級の順、ID順に並べる。"""
    exams = []
    for folder in EXAMS_DIR.iterdir() if EXAMS_DIR.exists() else []:
        meta_path = folder / "exam.json"
        if folder.is_dir() and meta_path.exists():
            exam = json.loads(meta_path.read_text(encoding="utf-8"))
            exam["folder"] = folder
            exams.append(exam)
    order = {key: i for i, (key, _) in enumerate(EXAM_LEVELS)}
    exams.sort(key=lambda e: (order.get(e["level"], len(order)), e["id"]))
    return exams


def exam_links(text, prefix):
    """試験別のページは book/exams/{試験ID}/ に置くので、本文の ../ で始まるリンクを1段深くする。"""
    return text.replace('href="../', f'href="{prefix}')


def exam_page(exam, slug, title, category, lead, body, updated, verified=""):
    """試験別のページを、コレクションのページと同じ形の辞書にする(描画・検査・検索で共通に使う)。"""
    key = "questions" if slug.endswith("/questions") else "exams"
    return {"key": key, "slug": slug, "path": f"exams/{exam['id']}/{slug.split('/')[1]}", "title": title,
            "category": category, "lead": lead, "date": "", "verified": verified, "body": body, "raw": body,
            "core": body, "graph": "", "updated": updated}


def exam_overview_html(exam):
    """試験の概要と、分野・配点・タスクの表。公式の試験ガイドの内容を exam.json から作る。"""
    parts = ['<section class="chapter">\n<h2>1. 試験の概要</h2>\n',
             f'<p>試験コードは{html.escape(exam["code"])}です。</p>\n']
    status = EXAM_STATUS_LABEL.get(exam["status"], "")
    if status or exam.get("status_note"):
        parts.append(f'<p>{html.escape(" ".join(part for part in (status, exam.get("status_note", "")) if part))}</p>\n')
    if exam.get("note"):
        parts.append(f'<p>{html.escape(exam["note"])}</p>\n')
    parts.append(f'<p><a href="{exam["guide_url"]}">公式の試験ガイド</a>で最新の内容を確認できます。</p>\n</section>\n')
    if exam["domains"]:
        rows = []
        for i, domain in enumerate(exam["domains"], 1):
            tasks = "<br>".join(f"{i}.{j} {html.escape(task['name_ja'])}" for j, task in enumerate(domain["tasks"], 1))
            weight = "" if domain.get("weight") is None else f"{domain['weight']}%"
            rows.append(f'<tr><td>{html.escape(domain["name_ja"])}<br><small>{html.escape(domain["name"])}</small></td>'
                        f'<td>{weight}</td><td>{tasks}</td></tr>\n')
        parts.append('<section class="chapter">\n<h2>2. 分野・配点・タスク</h2>\n'
                     '<div class="table-wrap"><table>\n<tr><th>分野</th><th>配点</th><th>タスク</th></tr>\n'
                     + "".join(rows) + "</table></div>\n</section>\n")
    return "".join(parts)


def exam_scope_page(exam, updated, warnings):
    """学習範囲のページ。試験の概要・分野の表(exam.json)と、任意の本文(scope.html)を並べる。"""
    where = f"exams/{exam['id']}/scope"
    body = exam_overview_html(exam)
    source = exam["folder"] / "scope.html"
    if source.exists():
        text = META_RE.sub("", source.read_text(encoding="utf-8")).strip()
        body += exam_links(render_figures(text, where, warnings), "../../")
    return exam_page(exam, f"{exam['id']}/scope", f"{exam['code']}の学習範囲", exam["code"],
                     f"{short_name(exam)}の分野・配点・タスクと、関連する教科書のページ", body,
                     updated.get(f"src/exams/{exam['id']}/exam.json", int(time.time())))


def exam_roadmap_page(exam, updated, warnings):
    """学習ロードマップ(roadmap.html)。ステップと項目ごとに、参考書のページ(reference/)を作る。"""
    source = exam["folder"] / "roadmap.html"
    if not source.exists():
        return None
    where = f"exams/{exam['id']}/roadmap"
    text = source.read_text(encoding="utf-8")
    meta = dict(META_RE.findall(text))
    raw = META_RE.sub("", text).strip()
    page = exam_page(exam, f"{exam['id']}/roadmap", meta.get("title", f"{exam['code']}の学習ロードマップ"), exam["code"],
                     meta.get("lead", ""), exam_links(render_figures(raw, where, warnings), "../../"),
                     updated.get(f"src/exams/{exam['id']}/roadmap.html", int(time.time())), meta.get("verified", ""))
    page["steps"] = roadmap_steps(raw)
    return page


def roadmap_steps(raw):
    """学習ロードマップを、ステップ(h3)と、その中の項目(箇条書きの1行)に分ける。
    項目ごとに参考書のページを作るため、項目で参照しているページ(services・terms・usecases)を集める。"""
    steps = []
    for chunk in re.split(r"(?=<h3[^>]*>)", raw)[1:]:
        title = plain(re.match(r"<h3[^>]*>(.*?)</h3>", chunk, re.S).group(1))
        found = re.search(r"ステップ(\d+)", title)
        number = int(found.group(1)) if found else len(steps) + 1
        items = []
        for li in re.findall(r"<li>(.*?)</li>", chunk, re.S):
            refs = []
            for ref in GUIDE_REF_RE.findall(li):
                if ref not in refs:
                    refs.append(ref)
            if not refs:
                continue
            text = plain(li)
            label = re.split(r"[:：]", text, 1)[0].strip() if re.search(r"[:：]", text) else text
            items.append({"label": label, "refs": refs, "slug": f"step{number}-{len(items) + 1}"})
        steps.append({"title": title, "items": items})
    return steps


def exam_questions_page(exam, updated, warnings):
    """問題集(questions.html)。DEA-C01 の問題は、分野ごとの追加問題データ(domain-N.json)を組み込む。"""
    source = exam["folder"] / "questions.html"
    if not source.exists():
        return None
    where = f"exams/{exam['id']}/questions"
    text = source.read_text(encoding="utf-8")
    if (exam["folder"] / "dea-c01-titles.json").exists():
        text = add_question_bank(text, exam["folder"])
    meta = dict(META_RE.findall(text))
    raw = META_RE.sub("", text).strip()
    return exam_page(exam, f"{exam['id']}/questions", meta.get("title", f"{exam['code']} 問題集"), meta.get("category", exam["code"]),
                     meta.get("lead", ""), exam_links(render_figures(raw, where, warnings), "../../"),
                     updated.get(f"src/exams/{exam['id']}/questions.html", int(time.time())), meta.get("verified", ""))


def exam_top_html(exam, pages):
    """試験ごとの入口。学習範囲は必ずあり、ロードマップ・問題集は作られているものだけ並べる。"""
    links = [("scope.html", "学習範囲", "分野・配点・タスク")]
    if pages["roadmap"]:
        links.append(("roadmap.html", "学習ロードマップと参考書", "学ぶ順番と項目ごとの参考書"))
    if pages["questions"]:
        links.append(("questions.html", "問題集", "シナリオ型の問題で理解を確認"))
    items = "".join(f'  <li><a href="{href}"><span class="exam-name">{name}</span>'
                    f'<span class="exam-status">{desc}</span></a></li>\n' for href, name, desc in links)
    return (head(f"{short_name(exam)} | {SITE_TITLE}", "../../", short_name(exam)) + header("../../", "exams")
            + f'<main>\n<div class="page-head{progress_class(exam)}">\n'
            + f'<p class="category">{html.escape(exam["code"])}</p>\n'
            + f'<h1>{html.escape(short_name(exam))}{progress_badge(exam)}</h1>\n</div>\n'
            + f'<ul class="exam-list">\n{items}</ul>\n'
            + '<p><a href="../index.html">試験の一覧へ戻る</a></p>\n'
            + "</main>\n" + TO_TOP + TAIL)



PROGRESS_LABEL = {"studying": "学習中", "passed": "合格済み"}


def progress_class(exam):
    """試験の進み具合に応じた CSS のクラス(学習中・合格済み。なければ空)。"""
    return f' progress-{exam["progress"]}' if exam.get("progress") in PROGRESS_LABEL else ""


def progress_badge(exam):
    label = PROGRESS_LABEL.get(exam.get("progress", ""), "")
    return f'<span class="progress-badge {exam["progress"]}">{label}</span>' if label else ""


def short_name(exam):
    """「AWS Certified」は全資格に共通するので、表示では省く。"""
    return re.sub(r"^AWS Certified\s+", "", exam["name"])


def exams_index_html(exams):
    """試験の一覧。級ごとに、1行に1試験(コード・名前・状態)を並べる。学習中・合格済みは色で示す。"""
    parts = [head(f"試験別 | {SITE_TITLE}", "../", "AWS認定の試験ごとに、学習範囲・ロードマップと参考書・問題集をまとめる"),
             header("../", "exams"), "<main>\n", '<div class="page-head"><h1>試験別</h1></div>\n']
    for key, label in EXAM_LEVELS:
        group = [e for e in exams if e["level"] == key]
        if not group:
            continue
        parts.append(f'<h2>{label}</h2>\n<ul class="exam-list">\n')
        for e in group:
            status = EXAM_STATUS_LABEL.get(e["status"], "")
            parts.append(f'  <li class="{progress_class(e).strip()}"><a href="{e["id"]}/index.html">'
                         f'<span class="code">{html.escape(e["code"])}</span>'
                         f'<span class="exam-name">{html.escape(short_name(e))}</span>'
                         + (f'<span class="exam-status">{status}</span>' if status else "")
                         + f'{progress_badge(e)}</a></li>\n')
        parts.append("</ul>\n")
    parts.append("</main>\n" + TO_TOP + TAIL)
    return "".join(parts)



def render_roadmap(page, exam):
    """学習ロードマップのページ。本文の後ろに、項目ごとの参考書のページへの一覧を付ける。"""
    body, items = add_heading_ids(stack_tables(page["body"]))
    index = []
    for step in page["steps"]:
        if step["items"]:
            index.append(f'<h3>{html.escape(step["title"])}</h3>\n<ul>\n'
                         + "".join(f'<li><a href="reference/{item["slug"]}.html">{html.escape(item["label"])}</a></li>\n'
                                   for item in step["items"])
                         + "</ul>\n")
    reference = ('<section class="chapter">\n<h2>4. 参考書の一覧</h2>\n'
                 '<p>学習の項目ごとに、参考書のページを分けています。項目を開くと、その項目で使うサービス・用語の説明が並びます。</p>\n'
                 + "".join(index) + "</section>\n") if index else ""
    return (head(f"{page['title']} | {SITE_TITLE}", "../../", page["lead"]) + header("../../", "exams")
            + f'<main>\n<div class="page-head{progress_class(exam)}">\n<p class="category">{html.escape(exam["code"])}</p>\n'
            + f'<h1>{html.escape(page["title"])}</h1>\n'
            + (f'<p class="lead">{page["lead"]}</p>\n' if page["lead"] else "")
            + "</div>\n" + page_toc(items) + body + "\n" + reference
            + "</main>\n" + TO_TOP + TAIL)


def item_pager(prev, nxt):
    def link(item, cls, label):
        if item is None:
            return f'<span class="{cls} empty"></span>'
        return (f'<a class="{cls}" href="{item["slug"]}.html"><span class="label">{label}</span>'
                f'{html.escape(item["label"])}</a>')
    return ('<nav class="pager">\n  ' + link(prev, "prev", "← 前の項目") + '\n'
            '  <a class="toc" href="../roadmap.html">ロードマップへ戻る</a>\n  '
            + link(nxt, "next", "次の項目 →") + '\n</nav>\n')


def reference_item_html(exam, step, item, prev, nxt, loaded):
    """参考書の1項目分のページ。その項目で参照しているページの本文を、順番どおりに並べる(印刷用)。"""
    pages = []
    for key, slug in item["refs"]:
        p = next((x for x in loaded.get(key, []) if x["slug"] == slug), None)
        if p is not None:
            pages.append((key, p))
    included = {p["slug"] for _, p in pages}
    articles = []
    for key, p in pages:
        # book/exams/{試験ID}/reference/ から見たリンクにする。項目の中にないページへのリンクは通常のページへ向ける
        article = booklet_body(key, p).replace('href="../', 'href="../../../')
        article = re.sub(r'href="#p-([\w-]+)"',
                         lambda m: m.group(0) if m.group(1) in included else f'href="../../../{key}/{m.group(1)}.html"',
                         article)
        articles.append(f'<article class="booklet-page" id="p-{p["slug"]}">\n'
                        f'<div class="page-head hero"{cat_style(_by_key[key], p["category"])}>\n<div class="hero-text">\n'
                        f'<span class="category">{html.escape(p["category"])}</span>\n<h1>{html.escape(p["title"])}</h1>\n'
                        + (f'<p class="lead">{p["lead"]}</p>\n' if p["lead"] else "")
                        + "</div>\n</div>\n" + article + "\n</article>\n")
    return (head(f"{item['label']} | {SITE_TITLE}", "../../../", "") + header("../../../", "exams")
            + '<main class="booklet guide">\n'
            + f'<div class="page-head booklet-cover">\n<p class="booklet-site">{html.escape(step["title"])}</p>\n'
            + f'<h1>{html.escape(item["label"])}</h1>\n'
            + '<p class="booklet-help">この項目で使うサービス・用語を、参考書としてまとめたページです。'
            'ブラウザーの印刷(Ctrl+P)から、紙に印刷するかPDFとして保存してください。</p>\n'
            + '<p class="booklet-help"><button type="button" class="booklet-print" onclick="print()">印刷・PDFに保存</button></p>\n'
            + "</div>\n" + "".join(articles) + item_pager(prev, nxt) + "</main>\n" + TO_TOP + TAIL)


def write_reference_pages(exam, page, loaded):
    """学習ロードマップの項目ごとに、参考書のページを書く。前の項目・次の項目へつながる。"""
    folder = OUT / "exams" / exam["id"] / "reference"
    folder.mkdir(parents=True, exist_ok=True)
    items = [(step, item) for step in page["steps"] for item in step["items"]]
    for n, (step, item) in enumerate(items):
        prev = items[n - 1][1] if n > 0 else None
        nxt = items[n + 1][1] if n + 1 < len(items) else None
        (folder / f"{item['slug']}.html").write_text(reference_item_html(exam, step, item, prev, nxt, loaded),
                                                     encoding="utf-8")


def redirect_html(url, label):
    return ('<!DOCTYPE html>\n<html lang="ja">\n<head>\n<meta charset="UTF-8">\n'
            f'<meta http-equiv="refresh" content="0; url={url}">\n<link rel="canonical" href="{url}">\n'
            f'<title>{SITE_TITLE}</title>\n</head>\n<body>\n'
            f'<p>このページは{label}に移りました。<a href="{url}">移動先を開く</a></p>\n</body>\n</html>\n')


# 試験別の移行前のURL(公開済みのリンクを切らないため、新しいページへ転送する)
LEGACY_PAGES = [
    ("questions/index.html", "../exams/index.html", "試験別"),
    ("questions/dea-c01.html", "../exams/dea-c01/questions.html", "DEA-C01の問題集"),
    ("guides/dea-c01.html", "../exams/dea-c01/roadmap.html", "DEA-C01の学習ロードマップ"),
    ("terms/data-engineer-exam-map.html", "../exams/dea-c01/scope.html", "DEA-C01の学習範囲"),
]


def write_exams(exams, loaded):
    """試験別のページ(一覧・試験の入口・学習範囲・ロードマップ・問題集)と、移行前のURLの転送を書く。"""
    base = OUT / "exams"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)
    (base / "index.html").write_text(exams_index_html(exams), encoding="utf-8")
    for e in exams:
        folder = base / e["id"]
        folder.mkdir()
        pages = e["pages"]
        (folder / "index.html").write_text(exam_top_html(e, pages), encoding="utf-8")
        (folder / "scope.html").write_text(render_page(EXAM_COL, [pages["scope"]], 0, "../../"), encoding="utf-8")
        if pages["roadmap"]:
            (folder / "roadmap.html").write_text(render_roadmap(pages["roadmap"], e), encoding="utf-8")
            write_reference_pages(e, pages["roadmap"], loaded)
        if pages["questions"]:
            (folder / "questions.html").write_text(render_page(QUESTION_COL, [pages["questions"]], 0, "../../"),
                                                   encoding="utf-8")
    for stale in ("questions", "guides"):  # 移行前の一覧・ページは、転送ページだけにする
        shutil.rmtree(OUT / stale, ignore_errors=True)
    for path, url, label in LEGACY_PAGES:
        target = OUT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(redirect_html(url, label), encoding="utf-8")


# ---- 図の凡例 ----

# 図の配色の意味(CLAUDE.md の決まり)。図で使われている分だけ、図の下に凡例として出す
LEGEND_ITEMS = [
    ("accent", "説明の中心", ("dg-accent", "dg-ta")),
    ("ok", "成功・推奨・正常", ("dg-ok", "dg-tok")),
    ("ng", "失敗・非推奨・障害", ("dg-ng", "dg-tng")),
    ("blue", "利用者・外部・送信元", ("dg-blue",)),
    ("box", "その他の構成要素", ("dg-box",)),
    ("blank", "空欄(問いで答える)", ("dg-blank",)),
    ("dash", "点線の矢印(使われない・切り替え前・補足)", ("dg-dash",)),
]
FIGURE_RE = re.compile(r'<figure class="figure">.*?</figure>', re.S)


def legend_swatch(kind):
    if kind == "dash":
        return ('<svg width="22" height="10" viewBox="0 0 22 10" aria-hidden="true" focusable="false" '
                'style="vertical-align:-1px"><line x1="1" y1="5" x2="21" y2="5" class="dg-line dg-dash"/></svg>')
    cls = {"accent": "dg-accent", "ok": "dg-ok", "ng": "dg-ng", "blue": "dg-blue", "box": "dg-box",
           "blank": "dg-blank"}[kind]
    return ('<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true" focusable="false" '
            f'style="vertical-align:-2px"><rect x="1" y="1" width="12" height="12" rx="3" class="{cls}"/></svg>')


def figure_legend(body):
    """図の下に、その図で使われている配色の意味を小さく出す(図の本体の外に置き、図のCSSの影響を受けないようにする)。"""
    def sub(m):
        fig = m.group(0)
        used = [(kind, label) for kind, label, classes in LEGEND_ITEMS
                if any(re.search(rf"\b{c}\b", fig) for c in classes)]
        if not used:
            return fig
        keys = "".join(f'<span class="fig-item">{legend_swatch(k)} {label}</span>' for k, label in used)
        return f'{fig}\n<p class="cat-desc fig-legend">{keys}</p>'
    return FIGURE_RE.sub(sub, body)


# ---- 選び方の入口・索引・比較表・選び方診断・マイページ(生成ページ) ----

# 検索の種類のチップ(トップの全ページ検索)。値は検索データの "g"
SEARCH_KINDS = [("all", "すべて"), ("services", "サービス"), ("terms", "用語"), ("usecases", "運用シナリオ"),
                ("news", "ニュース"), ("exams", "試験別・問題集")]

# 読みの辞書: 漢字で始まる見出しの読み(ひらがな)。索引の並びとかな行の振り分けに使う。漢字で始まる見出しを増やしたら足す
READINGS = {
    "責任共有モデル": "せきにんきょうゆうもでる",
    "料金の基本": "りょうきんのきほん",
    "保存時の暗号化と転送時の暗号化": "ほぞんじのあんごうかとてんそうじのあんごうか",
    "高可用性とスケーリング": "こうかようせいとすけーりんぐ",
    "監視・記録のサービスの選び方": "かんしきろくのさーびすのえらびかた",
    "機密情報・設定値の保存先の選び方": "きみつじょうほうせっていちのほぞんさきのえらびかた",
}
KANA_ROWS = [("あ", "あいうえお"), ("か", "かきくけこ"), ("さ", "さしすせそ"), ("た", "たちつてと"),
             ("な", "なにぬねの"), ("は", "はひふへほ"), ("ま", "まみむめも"), ("や", "やゆよ"),
             ("ら", "らりるれろ"), ("わ", "わをん")]
SMALL_KANA = str.maketrans("ぁぃぅぇぉゃゅょゎ", "あいうえおやゆよわ")


def index_section(title):
    """索引の見出し。(並び順の区分, 区分の中の順, 見出しの文字, アンカー, 読み)を返す。
    Amazon・AWS の付く名前は、その後ろの語で引く。カタカナはひらがなにして読む。"""
    if title in READINGS:
        reading = READINGS[title]
    else:
        name = re.sub(r"^(Amazon|AWS)\s+", "", title)
        reading = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c
                          for c in unicodedata.normalize("NFKC", name)).lower()
    first = unicodedata.normalize("NFD", reading[:1])[:1].translate(SMALL_KANA)
    if first and first.isascii() and first.isalnum():
        if first.isdigit():
            return (0, "0", "0-9", "idx-num", reading)
        return (0, first.upper(), first.upper(), f"idx-{first.lower()}", reading)
    for i, (label, chars) in enumerate(KANA_ROWS):
        if first and first in chars:
            return (1, i, label, f"idx-kana{i + 1}", reading)
    return (2, 0, "その他", "idx-other", reading)


def render_index_all(loaded):
    """用語・サービスの索引。名前の読みの順に、英字・かな行・その他に分ける。"""
    desc = "サービスと用語を、名前の読みの順に引けます"
    rows = [(index_section(p["title"]), key, p) for key in ("services", "terms") for p in loaded[key]]
    rows.sort(key=lambda r: (r[0][0], r[0][1], r[0][4]))
    sections = []  # [(アンカー, 見出し, [(コレクション, ページ)])]
    for info, key, p in rows:
        if not sections or sections[-1][0] != info[3]:
            sections.append((info[3], info[2], []))
        sections[-1][2].append((key, p))
    if not any(sid == "idx-other" for sid, _, _ in sections):
        sections.append(("idx-other", "その他", []))
    nav = "".join(f'<a href="#{sid}">{html.escape(label)}({len(items)})</a> ' for sid, label, items in sections)
    parts = [head(f"用語・サービスの索引 | {SITE_TITLE}", "../", desc), header("../", "terms"), "<main>\n",
             f'<div class="page-head"><h1>用語・サービスの索引</h1><p class="lead">{desc}</p></div>\n',
             '<p class="cat-desc">「Amazon」「AWS」を除いた名前で並べています。読みが分からない見出しは「その他」に入ります。</p>\n',
             f'<p class="booklet-link">{nav}</p>\n']
    for sid, label, items in sections:
        parts.append(f'<section class="toc-category" id="{sid}">\n<h2>{html.escape(label)} '
                     f'<span class="count">({len(items)})</span></h2>\n')
        if not items:
            parts.append('<p class="cat-desc">該当する見出しはありません。</p>\n')
        else:
            parts.append('<ul class="svc-list">\n')
            for key, p in items:
                href = f"../services/{p['slug']}.html" if key == "services" else f"{p['slug']}.html"
                icon = (service_icon(p["slug"], "../", 28) if key == "services" else "") or BLANK_ICON
                parts.append(f'  <li><a href="{href}">{icon}<span class="name">{html.escape(p["title"])}</span>'
                             f'<span class="badge">{html.escape(p["category"])}</span></a></li>\n')
            parts.append("</ul>\n")
        parts.append("</section>\n")
    parts += ["</main>\n", TAIL]
    return "".join(parts)


def service_price(p):
    """サービスページの「料金の考え方」の最初の段落(比較表の一行に使う。数値は書き写さず、短く切る)。"""
    m = re.search(r"<h2[^>]*>\s*\d*\.?\s*料金の考え方\s*</h2>(.*?)(?=<h2|\Z)", p["body"], re.S)
    if not m:
        return ""
    # 「下の図のように」など、そのページの図を指す段落は比較表では意味が通らないので飛ばす
    for para in re.finditer(r"<p>(.*?)</p>", m.group(1), re.S):
        text = " ".join(plain(para.group(1)).split())
        if text and "図" not in text:
            return text if len(text) <= 160 else text[:160] + "…"
    return ""


COMPARE_SCRIPT = """<script>
(function () {
  var items = JSON.parse(document.getElementById("compare-data").textContent);
  var root = document.getElementById("compare-root");
  var MAX = 3;
  var picked = [];
  function el(tag, text, cls) {
    var e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  root.innerHTML = "";
  var search = el("input");
  search.type = "search";
  search.placeholder = "サービス名で絞り込み";
  search.setAttribute("aria-label", "サービス名で絞り込み");
  search.setAttribute("autocomplete", "off");
  var status = el("p", "", "cat-desc");
  status.setAttribute("aria-live", "polite");
  var list = el("ul", undefined, "compare-pick");
  var result = el("div");
  var rows = items.map(function (it) {
    var li = el("li");
    var label = el("label");
    var box = el("input");
    box.type = "checkbox";
    box.value = it.s;
    label.appendChild(box);
    label.appendChild(document.createTextNode(" " + it.t));
    li.appendChild(label);
    list.appendChild(li);
    box.addEventListener("change", function () {
      if (box.checked) picked.push(it);
      else picked = picked.filter(function (p) { return p.s !== it.s; });
      update();
    });
    return { it: it, li: li, box: box, text: (it.t + " " + it.l).toLowerCase() };
  });
  search.addEventListener("input", function () {
    var q = search.value.trim().toLowerCase();
    rows.forEach(function (r) { r.li.hidden = q !== "" && r.text.indexOf(q) < 0; });
  });
  function update() {
    rows.forEach(function (r) { r.box.disabled = picked.length >= MAX && !r.box.checked; });
    status.textContent = "選択中 " + picked.length + "/" + MAX + "件(2〜3件を選ぶと比べられます)";
    result.innerHTML = "";
    if (picked.length < 2) {
      result.appendChild(el("p", "2件以上選ぶと比較表が出ます。", "cat-desc"));
      return;
    }
    var table = el("table");
    table.className = "stack";
    var thead = el("thead");
    var hr = el("tr");
    hr.appendChild(el("th", "項目"));
    picked.forEach(function (it) {
      var th = el("th");
      var a = el("a", it.t);
      a.href = "services/" + it.s + ".html";
      th.appendChild(a);
      hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);
    var tbody = el("tbody");
    [["一言説明", "l"], ["料金の考え方", "p"], ["最終確認日", "v"]].forEach(function (row) {
      var tr = el("tr");
      tr.appendChild(el("th", row[0]));
      picked.forEach(function (it) {
        var td = el("td", it[row[1]] || "—");
        td.setAttribute("data-label", it.t);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    result.appendChild(table);
    result.appendChild(el("p", "数値(料金・上限など)は各ページで確認してください。", "cat-desc"));
  }
  root.appendChild(search);
  root.appendChild(status);
  root.appendChild(list);
  root.appendChild(result);
  update();
})();
</script>
"""


def render_compare(loaded):
    desc = "2〜3個のサービスを選んで、一言説明・料金の考え方・最終確認日を並べて比べます"
    items = [{"s": p["slug"], "t": p["title"], "l": plain(p["lead"]), "p": service_price(p),
              "v": verified_label(p["verified"]) if p["verified"] else ""} for p in loaded["services"]]
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    static = "".join(f'  <li><a href="services/{p["slug"]}.html">{html.escape(p["title"])}</a></li>\n'
                     for p in loaded["services"])
    parts = [head(f"サービスの比較表 | {SITE_TITLE}", "", desc), header(""), "<main>\n",
             f'<div class="page-head"><h1>サービスの比較表</h1><p class="lead">{desc}</p></div>\n',
             '<div id="compare-root">\n'
             '<p class="cat-desc">JavaScript が動くと、2〜3件を選んで比較表を出せます。'
             '料金・上限などの数値は、各サービスのページで確認してください。</p>\n'
             f'<ul class="svc-list">\n{static}</ul>\n</div>\n',
             f'<script type="application/json" id="compare-data">{data}</script>\n',
             COMPARE_SCRIPT,
             "</main>\n", TAIL]
    return "".join(parts)


# 選び方診断の質問と候補。候補の tag は AWS の公式な特徴に基づく代表例(要件によって他のサービスも選べる)
CHOOSER_QUESTIONS = [
    {"id": "purpose", "q": "何をしたいですか", "when": None, "options": [
        ["compute", "プログラムを動かす(サーバー・関数・コンテナ)"],
        ["storage", "データを保存する・配信する"],
        ["database", "データを保存して検索・更新する"],
        ["network", "ネットワークを作る・接続する"],
        ["integration", "サービス同士をつないで処理を連携する"]]},
    {"id": "mgmt", "q": "サーバーの管理をどこまで任せたいですか", "when": None, "options": [
        ["managed", "管理したくない(AWSに任せたい)"],
        ["container", "コンテナで動かしたい"],
        ["vm", "OSごと自分で管理したい"],
        ["any", "指定しない"]]},
    {"id": "data", "q": "データの形は", "when": ["database", "storage"], "options_by": {
        "database": [["sql", "表形式(SQLで検索する)"], ["kv", "キーと値(一定の形で速く取り出す)"],
                     ["doc", "JSONなどのドキュメント"], ["graph", "関係(グラフ)をたどる"],
                     ["olap", "大量データを集計・分析する"], ["any", "指定しない"]],
        "storage": [["object", "ファイル単位(画像・ログなど)"], ["file", "共有フォルダのようなファイル"],
                    ["block", "OSのディスク(ブロック)"], ["any", "指定しない"]]}},
    {"id": "fast", "q": "応答の速さは", "when": ["database"], "options": [
        ["fast", "ミリ秒単位で応答する必要がある"],
        ["any", "数十ミリ秒〜秒単位で足りる、または指定しない"]]},
    {"id": "net", "q": "アクセスの経路は", "when": ["compute", "storage", "database", "network"], "options": [
        ["public", "インターネットから直接アクセスさせる"],
        ["onprem", "オンプレミスの社内ネットワークとつなぐ"],
        ["any", "指定しない"]]},
]
CHOOSER_CANDIDATES = [
    {"s": "lambda", "p": "compute", "m": ["managed"], "d": [], "f": False, "n": ["public", "onprem"]},
    {"s": "elastic-beanstalk", "p": "compute", "m": ["managed"], "d": [], "f": False, "n": ["public", "onprem"]},
    {"s": "ecs", "p": "compute", "m": ["container", "managed"], "d": [], "f": False, "n": ["public", "onprem"]},
    {"s": "eks", "p": "compute", "m": ["container"], "d": [], "f": False, "n": ["public", "onprem"]},
    {"s": "ec2", "p": "compute", "m": ["vm"], "d": [], "f": False, "n": ["public", "onprem"]},
    {"s": "s3", "p": "storage", "m": ["managed"], "d": ["object"], "f": False, "n": ["public", "onprem"]},
    {"s": "efs", "p": "storage", "m": ["managed"], "d": ["file"], "f": False, "n": ["onprem"]},
    {"s": "fsx", "p": "storage", "m": ["managed"], "d": ["file"], "f": False, "n": ["onprem"]},
    {"s": "ebs", "p": "storage", "m": ["vm"], "d": ["block"], "f": False, "n": []},
    {"s": "rds", "p": "database", "m": ["managed"], "d": ["sql"], "f": False, "n": ["onprem"]},
    {"s": "aurora", "p": "database", "m": ["managed"], "d": ["sql"], "f": False, "n": ["onprem"]},
    {"s": "dynamodb", "p": "database", "m": ["managed"], "d": ["kv"], "f": True, "n": ["onprem"]},
    {"s": "elasticache", "p": "database", "m": ["managed"], "d": ["kv"], "f": True, "n": ["onprem"]},
    {"s": "documentdb", "p": "database", "m": ["managed"], "d": ["doc"], "f": False, "n": ["onprem"]},
    {"s": "neptune", "p": "database", "m": ["managed"], "d": ["graph"], "f": False, "n": ["onprem"]},
    {"s": "redshift", "p": "database", "m": ["managed"], "d": ["sql", "olap"], "f": False, "n": ["onprem"]},
    {"s": "vpc", "p": "network", "m": ["managed"], "d": [], "f": False, "n": []},
    {"s": "site-to-site-vpn", "p": "network", "m": ["managed"], "d": [], "f": False, "n": ["onprem"]},
    {"s": "direct-connect", "p": "network", "m": ["managed"], "d": [], "f": False, "n": ["onprem"]},
    {"s": "elb", "p": "network", "m": ["managed"], "d": [], "f": False, "n": ["public", "onprem"]},
    {"s": "cloudfront", "p": "network", "m": ["managed"], "d": [], "f": False, "n": ["public"]},
    {"s": "route53", "p": "network", "m": ["managed"], "d": [], "f": False, "n": ["public"]},
    {"s": "sqs", "p": "integration", "m": ["managed"], "d": [], "f": False, "n": []},
    {"s": "sns", "p": "integration", "m": ["managed"], "d": [], "f": False, "n": []},
    {"s": "eventbridge", "p": "integration", "m": ["managed"], "d": [], "f": False, "n": []},
    {"s": "step-functions", "p": "integration", "m": ["managed"], "d": [], "f": False, "n": []},
    {"s": "api-gateway", "p": "integration", "m": ["managed"], "d": [], "f": False, "n": ["public"]},
]

CHOOSER_SCRIPT = """<script>
(function () {
  var data = JSON.parse(document.getElementById("chooser-data").textContent);
  var root = document.getElementById("chooser-root");
  var answers = {};
  var shown = {};
  var fieldsets = {};
  var result;
  function el(tag, text, cls) {
    var e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  }
  function optionsOf(q) {
    return q.options_by ? (q.options_by[answers.purpose] || []) : q.options;
  }
  // 目的によって選択肢が変わる質問は、目的が変わったときに組み直す
  function build(q, fs) {
    var opts = optionsOf(q);
    if (!opts.some(function (o) { return o[0] === answers[q.id]; })) answers[q.id] = q.id === "purpose" ? undefined : "any";
    fs.innerHTML = "";
    fs.appendChild(el("legend", q.q));
    opts.forEach(function (o) {
      var lab = el("label");
      var r = el("input");
      r.type = "radio";
      r.name = q.id;
      r.value = o[0];
      r.checked = answers[q.id] === o[0];
      r.addEventListener("change", function () {
        answers[q.id] = o[0];
        update();
      });
      lab.appendChild(r);
      lab.appendChild(document.createTextNode(" " + o[1]));
      fs.appendChild(lab);
    });
    fs.setAttribute("data-purpose", answers.purpose || "");
  }
  function match(c) {
    if (c.p !== answers.purpose) return false;
    return data.questions.every(function (q) {
      var a = answers[q.id];
      if (q.id === "purpose" || !shown[q.id] || !a || a === "any") return true;
      if (q.id === "mgmt") return c.m.indexOf(a) >= 0;
      if (q.id === "data") return c.d.indexOf(a) >= 0;
      if (q.id === "fast") return !!c.f;
      if (q.id === "net") return c.n.indexOf(a) >= 0;
      return true;
    });
  }
  function render() {
    result.innerHTML = "";
    if (!answers.purpose) {
      result.appendChild(el("p", "まず「何をしたいですか」を選んでください。", "cat-desc"));
      return;
    }
    var found = data.candidates.filter(match);
    result.appendChild(el("h2", "候補(" + found.length + "件)"));
    if (!found.length) {
      result.appendChild(el("p", "条件に合うサービスがありません。「指定しない」を選ぶか、条件を変えてみてください。", "cat-desc"));
      return;
    }
    var ul = el("ul", undefined, "card-list");
    found.forEach(function (c) {
      var li = el("li");
      var a = el("a");
      a.href = "services/" + c.s + ".html";
      a.appendChild(el("span", c.t, "name"));
      a.appendChild(el("span", c.l, "desc"));
      li.appendChild(a);
      ul.appendChild(li);
    });
    result.appendChild(ul);
  }
  function update() {
    data.questions.forEach(function (q) {
      var fs = fieldsets[q.id];
      shown[q.id] = !q.when || (!!answers.purpose && q.when.indexOf(answers.purpose) >= 0);
      fs.hidden = !shown[q.id];
      if (q.options_by && fs.getAttribute("data-purpose") !== (answers.purpose || "")) build(q, fs);
    });
    render();
  }
  root.innerHTML = "";
  data.questions.forEach(function (q) {
    var fs = el("fieldset", undefined, "chooser-q");
    fieldsets[q.id] = fs;
    root.appendChild(fs);
    build(q, fs);
  });
  result = el("div");
  result.setAttribute("aria-live", "polite");
  root.appendChild(result);
  update();
})();
</script>
"""


def render_chooser(loaded, warnings):
    desc = "いくつかの質問に答えると、目的に合うサービスの候補を絞り込みます"
    services = {p["slug"]: p for p in loaded["services"]}
    cands = []
    for c in CHOOSER_CANDIDATES:
        if c["s"] not in services:
            warnings.append(f"chooser.html: 候補のサービス「{c['s']}」のページがありません")
            continue
        cands.append({**c, "t": services[c["s"]]["title"], "l": plain(services[c["s"]]["lead"])})
    data = json.dumps({"questions": CHOOSER_QUESTIONS, "candidates": cands}, ensure_ascii=False).replace("</", "<\\/")
    static_q = "".join(
        f'  <li>{html.escape(q["q"])}:'
        + "・".join(html.escape(o[1]) for o in dict.fromkeys(
            tuple(o) for o in (q["options"] if "options" in q else [x for v in q["options_by"].values() for x in v])))
        + "</li>\n" for q in CHOOSER_QUESTIONS)
    static_c = "".join(f'  <li><a href="services/{c["s"]}.html">{html.escape(c["t"])}</a></li>\n' for c in cands)
    parts = [head(f"選び方診断 | {SITE_TITLE}", "", desc), header(""), "<main>\n",
             f'<div class="page-head"><h1>選び方診断</h1><p class="lead">{desc}</p></div>\n',
             '<div id="chooser-root">\n'
             '<p class="cat-desc">JavaScript が動くと、質問に答えて候補を絞り込めます。候補は代表的な例です。'
             '要件に合うかは、各サービスのページで確認してください。</p>\n'
             f'<h2>質問</h2>\n<ol>\n{static_q}</ol>\n'
             f'<h2>候補のサービス</h2>\n<ul class="svc-list">\n{static_c}</ul>\n</div>\n',
             f'<script type="application/json" id="chooser-data">{data}</script>\n',
             CHOOSER_SCRIPT,
             "</main>\n", TAIL]
    return "".join(parts)


def render_mypage():
    """しおり・学習メモの一覧(中身は js/mypage.js が localStorage から組み立てる)。"""
    desc = "このブラウザーに保存したしおり・学習メモを、一覧で見返せます"
    return (head(f"しおり・メモ | {SITE_TITLE}", "", desc) + header("") + "<main>\n"
            f'<div class="page-head"><h1>しおり・メモ</h1><p class="lead">{desc}</p></div>\n'
            '<div id="my-root"></div>\n'
            '<noscript><p class="empty-state">しおり・学習メモは、JavaScript が動くブラウザーで使えます。</p></noscript>\n'
            "</main>\n" + TAIL)


def main():
    warnings, counts, loaded = [], {}, {}
    updated = git_updated()
    for col in COLLECTIONS:
        loaded[col["key"]] = load_pages(col, warnings, updated)
    links_raw = (SRC / "links.html").read_text(encoding="utf-8")
    extra = {"links.html": links_raw}
    links = collect_links(loaded)
    titles = {(k, p["slug"]): p["title"] for k in GRAPH_KEYS for p in loaded[k]}
    for k in GRAPH_KEYS:
        for p in loaded[k]:
            p["graph"] = page_graph(k, p, links, titles)
    for c in COLLECTIONS:
        for p in loaded[c["key"]]:
            p["core"] = p["body"]  # 被リンクの一覧を付ける前の本文(冊子に使う)
    add_backlinks(loaded)
    exams = load_exams()
    exam_pages = []  # 試験別のページ(学習範囲・ロードマップ・問題集)
    for e in exams:
        e["pages"] = {"scope": exam_scope_page(e, updated, warnings),
                     "roadmap": exam_roadmap_page(e, updated, warnings),
                     "questions": exam_questions_page(e, updated, warnings)}
        exam_pages += [p for p in e["pages"].values() if p]
    loaded["exams"] = [p for p in exam_pages if p["key"] == "exams"]
    loaded["questions"] = [p for p in exam_pages if p["key"] == "questions"]
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
        if col["key"] == "news":
            write_news_day_redirects(pages)
    print_dir = OUT / "print"
    if print_dir.exists():
        shutil.rmtree(print_dir)
    print_dir.mkdir()
    for key in BOOKLET_KEYS:
        (print_dir / f"{key}.html").write_text(render_booklet(_by_key[key], loaded[key]), encoding="utf-8")
    write_glossary(loaded)
    write_exams(exams, loaded)
    (OUT / "terms" / "index-all.html").write_text(render_index_all(loaded), encoding="utf-8")
    (OUT / "compare.html").write_text(render_compare(loaded), encoding="utf-8")
    (OUT / "chooser.html").write_text(render_chooser(loaded, warnings), encoding="utf-8")
    (OUT / "mypage.html").write_text(render_mypage(), encoding="utf-8")
    # 生成したページ(試験別のページを含む)へのリンクも検査するため、書き出しの後に検査する
    for e in exams:
        extra[f"exams/{e['id']}/index.html"] = ""
    extra["exams/index.html"] = ""
    check_question_data(EXAMS_DIR, warnings)
    check_pages(COLLECTIONS + [EXAM_COL, QUESTION_COL], loaded, extra, OUT, warnings)
    (OUT / "index.html").write_text(render_top(loaded, exams, exam_pages), encoding="utf-8")
    (OUT / "links.html").write_text(render_links(loaded["services"], warnings), encoding="utf-8")
    checklist_page = OUT / "checklist.html"
    if checklist_page.exists():
        checklist_page.unlink()
    write_service_worker()
    print("built " + ", ".join(f"{c['label']} {counts[c['key']]}" for c in COLLECTIONS))
    for w in warnings:
        print("WARNING:", w)
    for line in thin_page_report(COLLECTIONS, loaded):
        print(line)


if __name__ == "__main__":
    main()
