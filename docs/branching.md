# ブランチ運用・GitHub 設定

リポジトリ: https://github.com/koba1000/zaikokanriapps （Public）

> Public のためコード・履歴は誰でも閲覧できる。**秘密情報・実データ・従業員情報は絶対にコミットしない**（Secret Scanning / gitleaks が最後の砦）。

## 1. ブランチ戦略（GitHub Flow）
```
main ───●───────●───────●──▶  常にデプロイ可能。保護対象。直接pushしない
         \     / \     /
          feat/xxx  fix/yyy    作業ブランチ → PR → CI成功 + 承認 → squash merge
```
| ブランチ | 用途 | 寿命 |
|---|---|---|
| `main` | 本番（Renderが自動デプロイ） | 永続 |
| `feat/<内容>` | 新機能 | PRマージで削除 |
| `fix/<内容>` | バグ修正 | 同上 |
| `chore/<内容>` | 設定・文書 | 同上 |
| `ai/<内容>` | AI（Copilot）主体の作業 | 同上。人間のレビュー必須 |

- 1ブランチ = 1目的、小さなPR（目安400行以内）
- TDD：ブランチ内で「テストのみのコミット（レッド）→ 実装コミット（グリーン）→ 整理（リファクタ）」の順
- コミットメッセージ：`feat:` `fix:` `test:` `refactor:` `docs:` `chore:` `ci:`
- DBスキーマ変更は `/migrations/` と `alembic.ini` をCODEOWNERSレビュー対象にし、アプリ用DBロールでDDLを実行しない

## 2. main の保護（GitHub Rulesets）
Settings → Rules → Rulesets → New branch ruleset（対象: `main`、Enforcement: Active）

| 設定 | 値 | 理由 |
|---|---|---|
| Restrict deletions / Block force pushes | ON | 履歴の改ざん防止 |
| Require a pull request before merging | ON | 直接push禁止（D-01） |
| Required approvals | 下記「注意」参照 | レビュー強制 |
| Require review from Code Owners | ON | 認証・暗号・CI設定は人間承認（D-05） |
| Dismiss stale approvals on new commits | ON | 承認後の差し替え防止 |
| Require conversation resolution | ON | 指摘の放置防止 |
| Require status checks to pass | ON | 下記5件 + CodeQL を必須に |
| Require branches to be up to date | ON | 最新mainでCI通過 |
| Require linear history | ON | squash mergeに統一 |

必須ステータスチェック名（ci.yml のジョブ名）: `lint` / `test` / `sast` / `dependencies` / `secrets` / `workflow-lint` / `guardrail-integrity`（PRのみ。テスト削除・skip化・カバレッジ緩和・CI検査無効化を検知して失敗、保護対象の変更は警告。`scripts/guardrail_check.py`）、`CodeQL`（`analyze`）
※ 一度CIを走らせないと候補に表示されない。最初のPRで実行してから設定する。

### 注意：開発者が1人の場合
GitHubは**自分のPRを自分で承認できない**。Code Owners が `@koba1000` のみだと、必須承認でマージ不能になる。
- 学習/個人開発：Required approvals を 0 にし、「PR必須＋CI必須」で運用（Code Owners レビューは OFF）
- 本番運用：2人目のレビュアー（別アカウント）を Code Owners に追加して承認必須にする

## 3. リポジトリの有効化設定（Settings → Code security）
- [ ] Dependabot alerts / security updates
- [ ] Secret scanning ＋ **Push protection**（Publicは無料で利用可）
- [ ] Code scanning（CodeQL は codeql.yml で実行）
- [ ] Private vulnerability reporting
- [ ] アカウントの2FA必須化
- [ ] Settings → Actions → General：Workflow permissions を `Read repository contents` に、fork PRのワークフロー承認を要求

## 4. 日常の流れ
```powershell
git switch main; git pull
git switch -c feat/orders-csv        # 作業ブランチ
# テストを書く → コミット(test:) → 実装 → コミット(feat:)
git push -u origin feat/orders-csv
# GitHubでPR作成 → CI成功・レビュー → Squash and merge → ブランチ削除
git switch main; git pull; git branch -d feat/orders-csv
```
