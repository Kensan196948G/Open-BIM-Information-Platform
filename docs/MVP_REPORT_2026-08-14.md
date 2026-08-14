# MVP / Prototype 完了報告（2026-08-14）

## 判定

**GO（MVP / Prototype として操作・評価可能）**

## 総合評価

- 既存の Phase 0/1 実装（IDOR修正・実API化・RBAC強制・通知・検索・版管理）を検証し、
  主要ユースケースが実 API・実 DB で動作することを確認。
- バックエンド 298 tests / 3 skipped / 72% カバレッジ、フロント 27 tests、
  E2E（実 DB）全成功、CI 9 ジョブ全 green（PR・main とも）。
- 公開レビュー URL を用意し、実ブラウザでログイン→ダッシュボード→承認タスクの
  操作を確認（コンソールエラー 0）。

## 本ラウンドの変更（PR #40 → main マージ済み a2e88e1）

| 区分 | 内容 |
|---|---|
| ダミーデータ | `scripts/seed_mvp.py` 新規（架空データ・冪等） |
| 機能追加 | `POST /api/v1/auth/change-password`（現在P検証・監査記録）+ テスト4件 |
| UI 是正 | 設定画面: パスワード変更を実 API 接続、セキュリティ/通知タブの偽データを実態表示へ、ロール管理を専用ページに一本化 |
| インフラ | vite preview `allowedHosts` に MVP 公開ドメイン追加、nanoid 3.3.18（high 脆弱性解消） |
| 文書 | `docs/MVP_DEMO.md` 新規・README 更新 |

## 公開 URL

- MVP: **https://open-bim-mvp.mirai-dx-platform.com**（Cloudflare Tunnel、稼働中）
- 本番: `open-bim.mirai-dx-platform.com`（未提供・Issue #31）

## ダミーデータ構成（bim_mvp DB・保持中）

orgs:2 / projects:3 / containers:11 / users:6 / workflows:6 / notifications:3 / req_docs:6 / audit_logs:50
（すべて架空。未来建設株式会社・おおぞら設計株式会社、未来橋架替工事・臨海部護岸整備工事・宮ヶ丘複合開発計画）

## デモユーザー（パスワード: DemoPass123!）

platform-admin@example.jp / admin@mirai.example.jp / reviewer@mirai.example.jp /
engineer@mirai.example.jp / chief@ozora.example.jp / designer@ozora.example.jp

## 残バックログ

- メール通知（SMTP/Exchange Online）・全文検索（pg_trgm）・リビジョン確定 UI（Phase 1）
- 本番環境・ドメイン・Secrets 提供（Issue #31、人間の環境提供待ち）
- 監査ログ外部 WORM・電子署名（Phase 4）、フロント単体テストのローカル実行制約（環境依存）
