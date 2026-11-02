# 多層防御設計：ガードレール＆ハーネス

方針：AIが誤った／危険なコードを書く前提で、**1つの層が破られても次の層で止める**。
- **ガードレール**＝逸脱を防ぐ制約（ルール、権限、ブロック）
- **ハーネス**＝AI出力を機械的に検証する仕組み（テスト、スキャン、CI）

## 1. 層の全体像
| 層 | 目的 | 実装 | 種別 |
|---|---|---|---|
| L0 設計 | 攻撃面を減らす | SSR中心、データ分類、脅威モデル | 設計 |
| L1 AI指示 | AIに規約を守らせる | `.github/copilot-instructions.md`、禁止事項 | ガードレール |
| L2 ローカル | コミット前に検出 | pre-commit（ruff, gitleaks, bandit） | ハーネス |
| L3 PR | 人間レビューの強制 | ブランチ保護、CODEOWNERS、PRテンプレ | ガードレール |
| L4 CI | 機械検証 | lint/型/テスト/SAST/依存/シークレット/設定検査 | ハーネス |
| L5 デプロイ | 安全な出荷 | CI成功後のみRender自動デプロイ、環境変数管理 | ガードレール |
| L6 実行時 | 攻撃の緩和 | 認証・RBAC・CSRF・レート制限・CSP・暗号化・最小権限DBロール | ガードレール |
| L7 監視/復旧 | 検知と回復 | 監査ログ、アラート、Neonバックアップ、ロールバック | 検知 |

## 2. 各層の詳細
### L0 設計
- 脅威モデル（STRIDE簡易版）を `docs/threat-model.md` として作成（次ステップ）
- VPNなしの代替：ログイン・ヘルスチェック以外は全て認証必須、レート制限、MFA（フェーズ2）
- データ最小化：従業員住所は必要項目のみ、店長のみ閲覧

### L1 AI指示（Copilot）
- `.github/copilot-instructions.md` に [ai-development-rules.md](./ai-development-rules.md) の要点を置く
- 禁止：SQL文字列連結、`eval/exec`、`|safe`、`debug=True`、秘密情報のハードコード、認可なしのルート、個人情報のログ出力、依存の無断追加
- 必須：新規ルートに認可デコレータとテスト、入力検証、パラメータ化クエリ
- 限界：指示に強制力はない。**以降の層で必ず検証**する

### L2 ローカル
- pre-commit：`ruff`、`gitleaks`、`bandit`
- ローカルはバイパス可能なので、同じ検査をL4で再実行（正はCI）

### L3 PR
- main保護：直接push禁止、PR必須、必須ステータスチェック、1名以上承認、force push禁止、会話解決必須
- CODEOWNERSで次は人間承認必須：`app/auth/`、`app/authz/`、`app/crypto/`、`migrations/`、`.github/`、`requirements*.txt`、`render.yaml`
- PRテンプレにセキュリティチェックリスト
- AI（Copilotエージェント）は自分のPRを承認できない

### L4 CI（GitHub Actions）
| ジョブ | ツール | ブロック条件 |
|---|---|---|
| lint/format | ruff | 違反 |
| 型検査 | （フェーズ2: mypy） | - |
| テスト | pytest + coverage | 失敗、カバレッジ80%未満 |
| 認可テスト | pytest（全ルートのロール別アクセス網羅） | 失敗、未登録ルートの追加も検知 |
| SAST | CodeQL、bandit、semgrep | 高/重大 |
| 依存脆弱性 | pip-audit、Dependabot、dependency-review-action | 高/重大 |
| シークレット | gitleaks、Secret Scanning＋Push Protection | 検出 |
| 設定検査 | actionlint、zizmor | 違反 |
| DB | 一時Postgresでのマイグレーション適用テスト | 失敗 |
| 動的検査 | OWASP ZAP baseline（ステージング） | 中以上（フェーズ2） |

- Actionsは最小権限の `permissions`、サードパーティActionはコミットSHAで固定
- forkからのPRにシークレットを渡さない

### L5 デプロイ
- Renderはmainのみ自動デプロイ。Auto-Deploy は「After CI Checks Pass」
- `DATABASE_URL`、`SECRET_KEY`、`ENCRYPTION_KEY` はRenderの環境変数で保持
- 環境分離：本番Neonブランチと開発/テスト用ブランチを分離。本番データを開発に流用しない
- ロールバック：Renderの前デプロイへ戻す手順をrunbookに記載

### L6 実行時（アプリ）
- 認証：Argon2id、レート制限（Flask-Limiter）、セッション期限
- 認可：デフォルト拒否。ルートにロール要求を明示
- CSRF：Flask-WTF CSRFProtect
- ヘッダ：Flask-Talisman（CSP、HSTS等）
- 入力検証：WTForms等、出力はJinja2自動エスケープ
- DB：SQLAlchemy（パラメータ化）、アプリ用ロールはDMLのみ、マイグレーション用ロール分離、`sslmode=require`
- 暗号化：住所はAES-GCM（`cryptography`）で列暗号化、鍵は環境変数。ローテーション手順を用意
- 本番でスタックトレースを返さない

### L7 監視・復旧
- 監査ログ（ログイン成否、権限変更、住所/売上閲覧、在庫更新）。個人情報は記録せずIDのみ
- 失敗ログイン多発・5xx増加のアラート
- Neonのポイントインタイムリストア確認を定期実施
- インシデント手順：鍵漏えい時のローテーション、セッション全失効、通知

## 3. AI特有リスクと対策
| リスク | 対策（層） |
|---|---|
| 存在しない/悪意あるパッケージの提案 | 依存追加はCODEOWNERS承認、pip-audit（L3/L4） |
| 認可漏れのルート生成 | 全ルート網羅の認可テスト、デフォルト拒否（L4/L6） |
| 秘密情報のハードコード | push protection、gitleaks、ダミー値のみ使用（L1/L2/L4） |
| テストを緩めて通す | テスト/CI設定の変更はCODEOWNERS承認、カバレッジ閾値（L3/L4） |
| プロンプトインジェクション（Issue/外部文書経由） | AI権限の最小化、外部入力を指示として扱わない、人間レビュー（L1/L3） |
| 本番データのAIへの送信 | 本番データ・住所をAI文脈に含めない、ダミーデータ使用（L0/L5） |

## 4. 実装ロードマップ
1. 本ドキュメントと要件の合意（現在）
2. リポジトリ雛形：`pyproject.toml`、Flask app factory、`.gitignore`、`.env.example`
3. `.github/`：copilot-instructions、CODEOWNERS、PRテンプレ、CIワークフロー、dependabot
4. pre-commit設定
5. 認証/認可/監査ログの基盤とテスト（機能開発より先）
6. 在庫機能 → 発注候補 → 売上/従業員
7. Render/Neon設定、ブランチ保護、Secret Scanning有効化
8. 脅威モデル、runbook、ZAP追加（フェーズ2）

## 5. 手動設定が必要な項目
- GitHub：ブランチ保護（Rulesets）、Secret Scanning/Push Protection、Dependabot alerts、CodeQL有効化、2FA必須
- Render：Auto-Deploy をCI成功後に設定、環境変数登録
- Neon：アプリ用/マイグレーション用ロール作成
