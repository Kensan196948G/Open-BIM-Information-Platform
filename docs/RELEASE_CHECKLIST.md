# 🚀 リリースチェックリスト (Gate-3) — Open BIM 情報基盤 v0.1.0

> Sprint 1 / Production Release 準備完了判定 — 人間サインオフ用チェックリスト

---

## 📌 リリース概要

| 項目           | 内容                                                                                                                     |
| -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 🏷️ バージョン  | v0.1.0 (Sprint 1 MVP)                                                                                                    |
| 📅 準備完了日  | 2026-06-17                                                                                                               |
| 🔢 最終 CI Run | [27687383766](https://github.com/Kensan196948G/Open-BIM-Information-Platform/actions/runs/27687383766) (全7ジョブ green) |
| 🌿 ブランチ    | main (commit c09e1ae — PR #26 squash merge)                                                                              |
| 👤 サインオフ  | **未取得（人間承認待ち）**                                                                                               |

---

## ✅ Gate-3 チェックリスト

### 品質ゲート

- [x] **全テスト通過**: backend 28 + frontend 8 + E2E (Playwright ライブ統合)
- [x] **CI 全ジョブ green**: 7/7 (lint×2, test×2, build, e2e, security)
- [x] **STABLE 達成**: 機能変更コミット 5 回連続 green (cf4571d→d7e6c0a)
- [x] **Lint エラー 0**: ruff (backend) + eslint (frontend)
- [x] **ビルド成功**: vite production build (271KB / gzip 89KB)

### セキュリティゲート

- [x] **gitleaks**: シークレット検出 0
- [x] **npm audit (high+)**: 脆弱性 0
- [x] **pip-audit**: アプリ依存の脆弱性 0
- [x] **対抗レビュー実施**: 認証/認可/並列処理を独立サブエージェントでレビュー
- [x] **セキュリティ修正完了**: 13件 (IDOR×3, DoS, Stored XSS, Path Traversal, Race Condition 他)
- [x] **Critical/High 未解決**: 0 件

### 機能ゲート

- [x] 認証 (JWT + bcrypt)
- [x] CDE 状態遷移 (WIP→Shared→Published→Archived) + 排他制御
- [x] 命名規則検証 (ISO 19650-2 Annex A)
- [x] ファイルアップロード (MinIO + SHA-256 + MIME allowlist)
- [x] 承認ワークフロー (FOR UPDATE 排他制御)
- [x] 監査ログ (immutable トリガー)

### ドキュメントゲート

- [x] README.md (表・アイコン・ダイアグラム・セットアップ手順)
- [x] ARCHITECTURE.md (設計・状態機械・認可・並列処理)
- [x] OPERATIONS.md (デプロイ・**ロールバック**・監視・バックアップ・障害対応)
- [x] 要件定義書・詳細仕様書

### パフォーマンスゲート

- [x] パフォーマンスベースライン測定 (latency budget テスト)
  - /health < 0.5s, login < 3.0s, naming/project-list < 1.0s

---

## ⚠️ 既知の制約・次スプリント対応事項

| 項目                                   | 状態                 | 対応予定               |
| -------------------------------------- | -------------------- | ---------------------- |
| OIDC/SAML 連携                         | 準備済み（未実装）   | Sprint 2               |
| 命名規則プロジェクト別カスタム設定 API | デフォルトルールのみ | Sprint 2 (#3)          |
| 通知システム                           | 未実装               | Sprint 2               |
| MinIO 本番容量設計                     | 開発設定             | デプロイ前に要設定     |
| パフォーマンス負荷試験                 | smoke レベルのみ     | 本番相当環境で実施推奨 |

---

## 👤 人間サインオフ欄

本リリースの本番デプロイには、以下の人間承認が必須です（全 Trust Level 共通）。

```
□ 技術責任者承認:  ________________  日付: __________
□ セキュリティ承認: ________________  日付: __________
□ 本番デプロイ実行: ________________  日付: __________
```

> 📋 **デプロイ手順**: [docs/OPERATIONS.md](OPERATIONS.md#-デプロイ手順) 参照
> ⏪ **ロールバック手順**: [docs/OPERATIONS.md](OPERATIONS.md#-ロールバック手順) 参照

---

## 🤖 CTO 判断記録

**CTO 判断: Release Ready（技術的リリース可能）**

Sprint 1 の全品質ゲート・セキュリティゲート・ドキュメントゲートを充足。
CI 全7ジョブ green、STABLE 達成、Critical/High 脆弱性 0。
`deploy.ready=true` を設定し、**人間サインオフ待ち状態**に到達。

実障の本番デプロイは人間（ユーザー）が手動で実行する（CTO はデプロイを自動実行しない）。

_判断日: 2026-05-31 / CTO (ClaudeOS v9.0)_
