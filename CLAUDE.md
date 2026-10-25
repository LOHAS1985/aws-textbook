# AWS教科書プロジェクト

## 目的
AWS(SOA-C03を中心とした認定資格)の学習用に、HTMLの教科書を作る。
「サービス」「用語」「ユースケース」の3種類のページで構成する。

## 対象読者
AWS初学者〜AWS認定資格(SAA程度)の学習者

## フォルダ構成
- src/{services,terms,usecases}/{slug}.html … 各ページの本文(編集するのはこちら)
- src/{terms,usecases}/_template.html … 新規ページのひな形(`_` で始まるファイルはビルド対象外)
- build.py … `python build.py` で src/ から book/ を生成する(コレクションの並び順・カテゴリ順もここで定義)
- diagrams.py … 本文中の図の記法をSVGに変換する
- book/index.html … トップ(サービス・用語・ユースケース・リンク集への入口)
- book/icons/services/{slug}.svg … サービスのアイコン(AWS公式の Architecture Icons 2026年7月版の48px SVGを、改変せずファイル名だけ slug にしたもの)。サービス一覧・各サービスページの見出し・リンク集・トップの検索結果に build.py が表示する。サービスを追加したら公式パッケージ(https://aws.amazon.com/jp/architecture/icons/)から同じ形でコピーする。専用アイコンがないサービス(Copilot・Database Encryption SDK・STS・SAM・Kiro・IPAM・DNS Firewall)は所属カテゴリの公式カテゴリアイコンを使っている
- src/links.html・src/links.json … リンク集(book/links.html)の本文と、サービスごとの公式ページ(製品ページ・ドキュメント)のパス。サービスを追加したら links.json にも追加する(URLは実際にアクセスして確認する)
- book/{services,terms,usecases}/index.html … 各コレクションの目次(カテゴリ別)
- book/{services,terms,usecases}/{slug}.html … 各ページ(生成物。直接編集しない)
- book/css/style.css … 共通スタイル(全ページで共有。これは直接編集する)
- book/icons/・book/manifest.webmanifest … ホーム画面用アイコンとWebアプリ設定(アイコンは `python tools/make_icons.py book/icons` で再生成)
- book/sw.js … オフラインで読むための Service Worker(生成物。直接編集しない)。build.py が book/ の全ファイルとその内容のハッシュを書き込み、利用者のブラウザは初回に全ファイル(約2.8MB)を保存し、更新時は変わったファイルだけを取り直す。book/ に置くファイルを増やすと自動で保存対象になる
- deploy.sh … `sh deploy.sh "メッセージ"` でビルド→コミット→push し、book/ を gh-pages ブランチに公開する

## 公開(GitHub Pages)
- リポジトリ: https://github.com/LOHAS1985/aws-textbook (public)
- 公開URL: https://lohas1985.github.io/aws-textbook/ (gh-pages ブランチ = book/ の中身。push 後1〜2分で反映)
- **修正を行ったら、確認を求めずに毎回すぐ `sh deploy.sh "修正内容"` を実行して GitHub に push する**(ページ以外の修正=CLAUDE.md・build.py・style.css なども同様)
- コミットメッセージは「YYYY-MM-DD 修正内容」の形式。日付は deploy.sh が自動で付けるので、引数には修正内容だけを具体的に書く(例: `sh deploy.sh "CloudWatchにメトリクス一覧を追加"`)
- Python がない環境では deploy.sh がビルドを省略して src/ だけを push する(警告が出る)。その場合は book/ が古いままなので、Python のある環境で再度 deploy.sh を実行するよう利用者に伝える
- gh は "C:\Program Files\GitHub CLI\gh.exe"

## 残タスク
- 今後対応する加筆・デザイン改善の予定は TASKS.md にチェックリストでまとめている。対応したら `[x]` に更新する

## 本文ファイルのメタ情報(先頭に書く)
    <!-- title: ページ名 -->
    <!-- category: カテゴリ名 -->
    <!-- lead: 一言説明 -->

## 各ページの構成
### サービス(services)
1. サービス概要(どんなサービスか)
2. 主な機能・特徴
3. ユースケース
4. 料金の考え方
5. 関連サービス(該当ページへのリンク)
6. 試験・実務でのポイント
7. まとめ
- 機能が多いサービス(例: services/systems-manager.html)は、1章に機能の分類表(各機能へのページ内リンク)を置き、2章で機能ごとに `<div class="feature" id="f-…"><h4>機能名</h4><p>概要</p><dl><dt>できること</dt><dd>…</dd>…</dl></div>` のブロックで1つずつ紹介する
- AWSのサービスとして提供されていないもの(機能・概念。例: VPCフローログ)は用語ページにする

### 用語(terms)
1. 詳しい説明 2. 関連する用語 3. 関連サービス
(どの種類のページでも「一言で言うと」の章は作らない。短い説明はメタ情報の lead に書く)

### ユースケース(usecases)
1. やりたいこと 2. 構成図 3. 使うサービスと役割 4. 構築の流れ 5. ポイント・注意点
- SOA-C03の出題分野に合わせて、次の5グループ(category)に分ける:
  監視・ログ・自動修復 / 信頼性・事業継続 / デプロイ・自動化 / セキュリティ・コンプライアンス / ネットワーク・コンテンツ配信
- グループの順番と説明文は build.py の COLLECTIONS(categories・category_desc)で定義する
- サービスのカテゴリごとの色は build.py の category_colors で定義する(AWS公式アイコンの配色に合わせる)。一覧のカードと各ページの見出しの色に使われるので、カテゴリを追加したら色も追加する

(確認問題は載せない)

## 図解
- 仕組み・構成・比較・判断フローなど、文章だけでは分かりにくい箇所には必ず図を入れる
- 基本は diagrams.py の記法で書く(書き方は diagrams.py 冒頭を参照)。ビルド時に文字のはみ出しが WARNING で出るので解消する
- 記法で表せない図(例: services/ec2.html のラック配置)はインラインSVGを直接書き、色は style.css の dg-* クラスを使う(ダークモード対応のため色を直書きしない)
- キャプションは「図N 説明」
- 図の配色の意味をそろえる:accent=説明の中心となる要素/ok=成功・推奨・正常/ng=失敗・非推奨・障害/blue=利用者・外部・送信元/box=その他の構成要素。点線の矢印(dash)は「使われない・切り替え前・補足的な流れ」

## ルール
- 太字(strong)は1つの段落・項目につき3か所まで。`<strong class="em">`(蛍光ペン風の強調)は試験で特に問われる語句だけに使う
- 6章「試験・実務でのポイント」が10項目を超えたら、`<div class="point">` の中を `<h4>テーマ</h4><ul>…</ul>` で分ける
- 次のものは build.py が自動で付けるので本文には書かない:見出し(h2・h3)の id とアンカー、ページ内目次(h3が5個以上のページ)、最終更新日(git のコミット日時)、ページの説明(meta description。lead を使う)、列が4つ以上の表のスマホ用カード表示(結合セルのある表は対象外)、サービスページ末尾の「このサービスが登場するユースケース」と用語ページ末尾の「この用語が出てくるページ」(本文中のリンクから自動で集める。ユースケースからサービス・用語へリンクを張ると増える)
- Notionからの移行は完了済み。今後はNotionを参照せず、AWS公式ドキュメント等で自ら調べて加筆・修正する
- 加筆した内容に「補足」の表示(ラベル・括弧書き・note枠)は付けない。通常の本文として書く
- ページ上に「Notion」への言及や制作に関する説明文は表示しない
- HTMLは素のHTML+CSSのみ(外部ライブラリなし)。JavaScriptは build.py が出力する一覧の絞り込み、トップページの全ページ検索、オフライン用の Service Worker(sw.js と各ページでの登録)だけに使う
- サービスの一覧はサービス名だけのコンパクトな表示(lead は表示しないが、絞り込みの検索対象には含める)
- 全ページに「目次へ戻る」「前へ/次へ」のリンクを付ける(build.py が自動で付ける)
- コレクション間のリンクは相対パス(例: 用語ページから `../services/vpc.html`)
- スマホでも読めるレスポンシブデザインにする
