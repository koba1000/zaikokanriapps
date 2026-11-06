# 喫茶店 在庫管理アプリ（CI/CD × AI駆動開発 × 多層防御）

毎朝の在庫把握と発注を楽にするWebアプリ。Flask（Render）＋PostgreSQL（Neon）。VPNなし、HTTPS＋認証＋多層防御で安全性を確保する。

## ドキュメント
| 文書 | 内容 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | **構成説明（講義用）**：ディレクトリ構成と各層の役割 |
| [docs/requirements.md](docs/requirements.md) | 要件定義書（機能/非機能/情報分類/未決事項） |
| [docs/defense-in-depth.md](docs/defense-in-depth.md) | 多層防御設計（ガードレール・ハーネス、CI、ロードマップ） |
| [docs/ai-development-rules.md](docs/ai-development-rules.md) | Copilotに守らせる開発ルール・PRチェックリスト |

## 構成
Flask+Jinja2(SSR) → Render → Neon(PostgreSQL) / CI: GitHub Actions / AI: GitHub Copilot

## 実装状況
アプリ・テスト・CI・ガードレール・発注状態管理・Alembicマイグレーションを実装済み。起動方法は [docs/architecture.md](docs/architecture.md) の「動かし方」を参照。GitHub/Render/Neon の手動設定は [docs/defense-in-depth.md](docs/defense-in-depth.md) の §5。
