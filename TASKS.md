# 残タスク(サービスページの加筆)

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
- [ ] DBサブネットグループ
- [ ] パラメータグループ/オプショングループ
- [ ] メンテナンスウィンドウ
- [ ] 暗号化(作成時のみ。後からはスナップショットのコピーで)
- [ ] ストレージの自動スケーリング
- [ ] Multi-AZのDNS切り替え(エンドポイントは変わらない)
- [ ] Performance Insights(と拡張モニタリング)
- [ ] Blue/Green Deployments
- [ ] 停止は最大7日(過ぎると自動で起動)

## 7. CloudFront(src/services/cloudfront.html)
- [ ] ビヘイビア(パスごとのオリジン・設定)
- [ ] キャッシュキーとキャッシュポリシー(オリジンリクエストポリシーも)
- [ ] 無効化(Invalidation)
- [ ] 署名付きURL/署名付きCookie
- [ ] 地理的制限
- [ ] オリジンフェイルオーバー(オリジングループ)
- [ ] CloudFront FunctionsとLambda@Edgeの比較

## 8. CloudFormation(src/services/cloudformation.html)
- [ ] 組み込み関数(!Ref・!GetAtt・!Sub・!FindInMap・!Join など)
- [ ] Export/ImportValue(スタック間の参照)
- [ ] ロールバックとスタックの状態(UPDATE_ROLLBACK_FAILED など)
- [ ] cfn-init/cfn-signal/CreationPolicy(WaitCondition)
- [ ] UpdatePolicy(Auto Scalingグループの更新)
- [ ] 終了保護

## 9. Lambda(src/services/lambda.html)
- [ ] 呼び出し方式3種(同期/非同期/イベントソースマッピング)と、再試行・DLQ・送信先(デスティネーション)の関係
- [ ] 実行ロール(とリソースベースのポリシー)
- [ ] VPC接続するとインターネットに出るにはNATゲートウェイが必要

## 10. EBS(src/services/ebs.html)
- [ ] スナップショットは増分であること
- [ ] Data Lifecycle Manager(DLM)
- [ ] ごみ箱(Recycle Bin)
- [ ] 既存の暗号化されていないボリュームを暗号化する手順
- [ ] Elastic Volumes(オンラインでのサイズ・タイプ変更とファイルシステムの拡張)
- [ ] ボリュームタイプごとの性能値(gp3のベースラインなど)
