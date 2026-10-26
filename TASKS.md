# 残タスク(サービスページの加筆)※完了

SOA-C03で頻出なのに説明が薄い10ページに、仕組みの説明を加筆する。
各ページとも、加筆は2章「主な機能・特徴」を中心に行い、必要に応じて図(diagrams.py の記法)・6章「試験・実務でのポイント」・関連する用語へのリンクも更新する。
終わった項目は `[x]` にし、ページの項目がすべて終わったら `sh deploy.sh "○○ページを加筆"` で公開する。

## 1. VPC(src/services/vpc.html)
- [x] サブネットの予約IP(5つ)と「1サブネット=1AZ」(詳細は用語ページ cidr へリンク)
- [x] Elastic IP(詳細は用語ページ eni-elastic-ip へリンク)
- [x] VPCピアリング(詳細は用語ページ vpc-peering へリンク)
- [x] VPCエンドポイントの2種類(詳細は用語ページ vpc-endpoint へリンク)
- [x] NATゲートウェイはAZ単位のため、AZごとに作って冗長化する
- [x] セキュリティグループ同士の参照(送信元にSGを指定)
- [x] エフェメラルポート(ネットワークACLの戻り通信)
- [x] Reachability Analyzer(到達性の分析)

## 2. ELB(src/services/elb.html)
- [x] ターゲットグループとターゲットタイプ(インスタンス/IP/Lambda/ALB)
- [x] ヘルスチェックの設定項目(パス・間隔・しきい値・成功コード)
- [x] クロスゾーン負荷分散(ALBは既定で有効、NLBは既定で無効)
- [x] 登録解除の遅延(Connection Draining)
- [x] スティッキーセッション
- [x] 内部向け/インターネット向け
- [x] アクセスログ(S3へ出力)
- [x] SNI(1つのリスナーで複数の証明書)
- [x] WAFとの連携

## 3. IAM(src/services/iam.html)
- [x] ポリシーJSONの例(Effect/Action/Resource/Condition)(詳細は用語ページ iam-policy-evaluation へリンク)
- [x] 評価ロジック(明示的なDenyが最優先)
- [x] マネージドポリシーとインラインポリシー
- [x] アクセス許可の境界(Permissions Boundary)
- [x] IAM Access Analyzer
- [x] 認証情報レポート
- [x] IAM Identity Centerを別のサービスページとして作成し、パーミッションセットの説明を移す

## 4. S3(src/services/s3.html)
- [x] バケット・キー・プレフィックス(フォルダは実在しない)
- [x] バージョニング(単独の機能として)
- [x] ライフサイクルルール
- [x] ブロックパブリックアクセス
- [x] 既定の暗号化(SSE-S3)(詳細は用語ページ encryption へリンク)
- [x] Object Lock
- [x] 静的ウェブサイトホスティング
- [x] マルチパートアップロード
- [x] CORS
- [x] イベント通知の送信先としてのEventBridge

## 5. EC2(src/services/ec2.html)
- [x] キーペア
- [x] ユーザーデータ
- [x] インスタンスメタデータとIMDSv2
- [x] 停止・休止・終了の違い(終了保護も)
- [x] ステータスチェック(システム/インスタンス)と自動復旧
- [x] T系インスタンスのCPUクレジット(標準/unlimited)
- [x] RI(Standard/Convertible)とSavings Plans(Compute/EC2 Instance)の種類
- [x] スポットインスタンスの中断通知(2分前)

## 6. RDS(src/services/rds.html)
- [x] DBサブネットグループ
- [x] パラメータグループ/オプショングループ
- [x] メンテナンスウィンドウ
- [x] 暗号化(作成時のみ。後からはスナップショットのコピーで)
- [x] ストレージの自動スケーリング
- [x] Multi-AZのDNS切り替え(エンドポイントは変わらない)
- [x] Performance Insights(と拡張モニタリング)
- [x] Blue/Green Deployments
- [x] 停止は最大7日(過ぎると自動で起動)

## 7. CloudFront(src/services/cloudfront.html)
- [x] ビヘイビア(パスごとのオリジン・設定)
- [x] キャッシュキーとキャッシュポリシー(オリジンリクエストポリシーも)
- [x] 無効化(Invalidation)
- [x] 署名付きURL/署名付きCookie
- [x] 地理的制限
- [x] オリジンフェイルオーバー(オリジングループ)
- [x] CloudFront FunctionsとLambda@Edgeの比較

## 8. CloudFormation(src/services/cloudformation.html)
- [x] 組み込み関数(!Ref・!GetAtt・!Sub・!FindInMap・!Join など)
- [x] Export/ImportValue(スタック間の参照)
- [x] ロールバックとスタックの状態(UPDATE_ROLLBACK_FAILED など)
- [x] cfn-init/cfn-signal/CreationPolicy(WaitCondition)
- [x] UpdatePolicy(Auto Scalingグループの更新)
- [x] 終了保護

## 9. Lambda(src/services/lambda.html)
- [x] 呼び出し方式3種(同期/非同期/イベントソースマッピング)と、再試行・DLQ・送信先(デスティネーション)の関係
- [x] 実行ロール(とリソースベースのポリシー)
- [x] VPC接続するとインターネットに出るにはNATゲートウェイが必要

## 10. EBS(src/services/ebs.html)
- [x] スナップショットは増分であること
- [x] Data Lifecycle Manager(DLM)
- [x] ごみ箱(Recycle Bin)
- [x] 既存の暗号化されていないボリュームを暗号化する手順
- [x] Elastic Volumes(オンラインでのサイズ・タイプ変更とファイルシステムの拡張)
- [x] ボリュームタイプごとの性能値(gp3のベースラインなど)

# 残タスク(デザインの問題点)※完了

PC幅(1000px)とスマホ幅(375px)で表示を確認して見つけた、デザイン上の問題点。対応したら `[x]` にする。

## 読みやすさ・ナビゲーション
- [x] 長いページ(S3・EC2・CloudFormationなど、2章の小見出しが10〜20個)にページ内目次がない。ページ冒頭に h3 へのリンク一覧を build.py で自動生成する
- [x] h2・h3 にアンカー(id)がなく、特定の節へのリンクを共有できない。見出しに id を自動で付ける
- [x] 長いページで先頭に戻る手段がない(「ページの先頭へ」リンクや、ヘッダーの固定表示を検討)
- [x] 6章「試験・実務でのポイント」が長くなり(S3は約20項目)、一覧で見渡しにくい。テーマごとに小見出しで分けるか、2章の各節の末尾に分散させる
- [x] サイト全体の検索がない(絞り込みはサービス一覧のみ)。用語・ユースケースの一覧にも絞り込みを付けるか、全ページ横断の検索を作る
- [x] サービスの一覧(チップ表示)では lead が見えず、知らないサービスが何かを判断できない。ホバー時の title 属性や、カテゴリ説明の追加を検討
- [x] ページ上部のカテゴリ表示(例:「ストレージ」)がリンクになっておらず、同じカテゴリの一覧に戻れない
- [x] トップページがカード4枚だけで、下半分が空白。試験分野ごとの学習の入口や、最近更新したページの一覧を置く

## スマホでの表示
- [x] 図(SVG)の最小幅が520pxのため、スマホでは図の右側が切れ、横スクロールできることが分かりにくい。スクロールできることを示す影やヒントを付けるか、図を縦長にする
- [x] 図が縮小されると文字が小さくなる(12pxの補足行がスマホでは約8pxになる)。補足行の文字を大きくするか、横に長い図(ノード5個以上の横並び)を2段に組み直す
- [x] 表の最小幅が480px・見出しセルが折り返し禁止のため、列の多い表(EBSの性能値、Lambdaの呼び出し方式など)はスマホで大きく横スクロールが必要。列の多い表は縦並びのカード表示に切り替える
- [x] ヘッダーのナビゲーションが4項目(サービス・用語・ユースケース・リンク集)になり、スマホではサイト名と2段に折り返す。短い表記や折りたたみメニューを検討

## 見た目の一貫性
- [x] `strong.em`(赤字の強調)の色がCSS変数ではなく直書きで、エラー・NGを表す赤(--danger)と同じ色のため「注意」と「誤り」の区別がつかない。強調用の色を別の変数で定義する
- [x] 太字(strong)が1段落に何か所もあり、強調が多すぎてどこが重要か分かりにくいページがある。1段落あたりの強調を絞るルールを決める
- [x] 表の列幅が表ごとに内容任せで、同じ種類の表が並ぶと列の位置がずれる(リンク集の表は対応済み)
- [x] 図の配色の意味(accent=中心、ok=成功・推奨、ng=失敗・非推奨、blue=外部・利用者)が決まっておらず、ページによって使い方がばらつく。CLAUDE.md に配色のルールを書く
- [x] キャプションの文字(13px・薄い灰色)がダークモードで読みにくい。コントラストを上げる

## アクセシビリティ・その他
- [x] リンクやボタンにキーボード操作時のフォーカス表示(:focus-visible)のスタイルがない
- [x] `<meta name="theme-color">` が暗い色に固定で、ライトモードでもブラウザのアドレスバーが暗くなる。ライト用・ダーク用を media 属性で出し分ける
- [x] 印刷用のスタイル(@media print)がなく、ダークモードの背景色のまま印刷される・図や表がページの途中で切れる
- [x] ページの説明(`<meta name="description">`)がなく、共有時や検索結果に説明が出ない。lead を使って出力する
- [x] 各ページに最終更新日がなく、情報がいつ時点のものか分からない(AWSは仕様の変更が多い)。git の更新日を build.py で表示する

# 残タスク(SOA-C03の対象サービスのページ追加)※完了

試験ガイド(SOA-C03)の In-Scope AWS Services にあり、ページがなかったサービスを追加する。
- [x] 分析:Amazon Data Firehose
- [x] クラウド財務管理:AWS Cost Explorer、AWS Cost and Usage Reports、Savings Plans
- [x] コンピューティング:Amazon EC2 Image Builder
- [x] ストレージ:AWS Storage Gateway
- [x] ネットワーク:Amazon VPC IP Address Manager(IPAM)、AWS Client VPN、Route 53 Resolver DNS Firewall、Amazon Application Recovery Controller(ARC)
- [x] セキュリティ:Amazon GuardDuty、Amazon Inspector、AWS WAF、AWS Shield、AWS Network Firewall、AWS Security Agent
- [x] マネジメントとガバナンス:AWS Control Tower、AWS DevOps Agent
- [x] デベロッパーツール:Kiro
- [x] 機械学習と人工知能:Amazon Bedrock

# 残タスク(ユースケースを各グループ10件に増やす)※完了

SOA-C03の出題範囲(タスクステートメント)に沿った、運用担当者の視点のユースケースを追加する。
- [x] 監視・ログ・自動修復:外形監視と誤報の少ないアラーム、AWS Healthイベントへの対応、コンテナの監視、分散トレース、EC2・EBSの性能改善、RDSの性能改善
- [x] 信頼性・事業継続:SQSによる分離、キャッシュ、AZの切り離し(ゾーンシフト)、DynamoDBのスケーリングとPITR、RDSのPITR、S3のデータ保護
- [x] デプロイ・自動化:State Managerによる構成管理、ゴールデンAMI、CloudFormationの安全な更新、ドリフト検出、ECSの安全なデプロイ、定時の停止・起動
- [x] セキュリティ・コンプライアンス:Identity CenterによるSSO、AccessDeniedの調査と最小権限、脆弱性管理、GuardDutyによる自動隔離、WAFによるWebの保護
- [x] ネットワーク・コンテンツ配信:IPAMによるCIDRの払い出し、VPCエンドポイント、外向き通信の制限、ハイブリッドDNS、Client VPN、Route 53のルーティングポリシー

# 残タスク(SOA-C03の前提知識の用語ページ追加)※完了

多くの問題で前提になるのに説明がなかった概念を、用語ページとして追加する。関連するサービスページの「関連する用語」からもリンクする。
- [x] CloudWatchアラームの状態と評価(cloudwatch-alarm-states)
- [x] IAMロールと一時的な認証情報(iam-roles-credentials)
- [x] iam:PassRoleとサービスにリンクされたロール(iam-passrole)
- [x] TerraformとGit(terraform-git)
- [x] スロットリングとリトライ(throttling-retry)
- [x] イベント駆動の自動修復(event-driven-remediation)
- [x] cron式とrate式(cron-rate-expressions)
- [x] HTTPステータスコードと切り分け(http-status-codes)
- [x] TLS終端と証明書の配置(tls-termination)
- [x] IOPS・スループット・レイテンシ(performance-metrics)
- [x] よく使うポート番号(port-numbers)
- [x] JSONとYAMLの読み方(json-yaml)

# 残タスク(「AWSの基礎」カテゴリの用語ページ追加)※完了

最初に読む基礎知識を、用語の「AWSの基礎」カテゴリに追加する(別のセクションには分けない)。
- [x] 責任共有モデル(shared-responsibility)
- [x] デフォルトVPC(default-vpc)
- [x] ルートユーザーとアカウントの保護(root-user)
- [x] AWSの操作方法(コンソール・CLI・SDK・API)(access-methods)
- [x] タグ(tags)
- [x] 料金の基本(pricing-basics)
- [x] サポートプラン(support-plans)。Health Dashboard・Trusted Advisor・Shield などの旧プラン名も更新
- [x] SLAと可用性(sla-availability)
- [x] マネージドサービスとサーバーレス(managed-serverless)
- [x] AWS Well-Architected フレームワーク(well-architected)
- [x] コンプライアンスとAWS Artifact(compliance-artifact)
- [x] リージョンとAZのページに Local Zones・Wavelength・Outposts を追記

# 残タスク(構成演習)※完了

AWSアカウントを使わずに、要件を満たす構成を組み立てる演習(src/exercises/、book/js/sim.js)。
- [x] ルールの変更(CLAUDE.md に構成演習のページ構成と書き方を追加、JavaScriptの利用範囲に sim.js を追加)
- [x] ①穴埋め(構成)+②穴埋め(設定)の試作:各グループ1件ずつ5件(EC2のメモリ監視・Auto Scaling・定時の停止・Configの自動修復・VPCエンドポイント)
- [x] ビルド時の検査(正解が1つ、図の空欄と問いの対応、図に出す名前の幅)
- [x] 試作を使ってみて、問題の形式・画面を見直す(選択肢を横に並ぶボタンにし、解説は答え合わせのあとに問いの下へまとめて表示)
- [x] 残りの45件の運用シナリオに演習を追加する(各グループ10件、計50件)
- [x] ③自由構成(部品を図に置いて矢印でつなぎ、正解の構成と比べて判定する)。正解は build.py が2章の図から自動で作る
- [x] ヘッダーに構成演習とニュースを追加(スマホは2段で、ナビは横スクロール)
