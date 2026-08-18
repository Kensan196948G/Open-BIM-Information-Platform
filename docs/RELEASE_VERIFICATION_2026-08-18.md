# リリース検証レポート（2026-08-18）

> DeepSeek Harness 自律ラウンド 1〜3 の検証結果を統合した報告。
> 対象: MVP（`open-bim-mvp.mirai-dx-platform.com`）と本番公開（`open-bim.mirai-dx-platform.com`）。

## 1. 実行環境

| 項目 | 状態 |
|---|---|
| 本番 URL | https://open-bim.mirai-dx-platform.com（Cloudflare Tunnel・production モード・HTTP 200） |
| MVP URL | https://open-bim-mvp.mirai-dx-platform.com（Cloudflare Tunnel・HTTP 200） |
| 常駐化 | systemd(user) ユニット 6 本（backend/frontend/tunnel × MVP/本番・Linger=yes）+ 5 分間隔死活監視タイマー |
| 本番 DB | ローカル PostgreSQL 16 `bim_prod`（alembic head `5e4d3c2b1a09`・シード済み・架空データのみ） |
| Neon 検証 DB | `open-bim-information-platform`（noisy-paper-35107522・us-west-2）— Migration + Seed 実証済み |
| バックアップ | `backups/backup-20260818-201244.tar.gz.enc`（AES-256-CBC・復元演習済み） |

## 2. 完了条件の検証結果

| # | 完了条件 | 結果 | 証拠 |
|---|---|---|---|
| 1 | 主要業務フローが OpenDesign の目的と整合し実際に操作可能 | ✅ | ログイン→ダッシュボード→プロジェクト→コンテナ→承認→通知→監査の 12 フロー（MVP_DEMO.md）を実 API で確認。E2E（Playwright・実 DB）全成功 |
| 2 | ダミーデータで正常・空・エラー・権限別状態を確認可能 | ✅ | 正常（ダッシュボード/一覧）、エラー（不正ログイン、未認証 401）、権限差（member approve 403 / reviewer 200）、空状態 UI（EmptyState コンポーネント） |
| 3 | Neon Migration と Seed を空の検証 DB へ再実行可能 | ✅ | Neon 実プロジェクトで `alembic upgrade head`（22 テーブル）→ `seed_mvp.py`（users=6/orgs=2/projects=3/containers=11）。ローカル空 DB では冪等性（2 回実行で重複なし）も確認 |
| 4 | 型検査・Lint・主要テスト・E2E・ビルド成功 | ✅ | main CI 9 ジョブ green（Backend Tests 292 件・Frontend Tests・E2E Playwright・Lint/型・ビルド・SBOM・Security Scan・pip-audit） |
| 5 | レスポンシブ・キーボード操作・主要 a11y 確認済み | ✅ | 実ブラウザ 11/11（375px/1440px 横スクロールなし・Tab 巡回・ラベル・ボタン名・h1・コンソールエラー 0）。focus-visible スタイル実装済み |
| 6 | Cloudflare Preview で画面・API・認証・DB 接続確認済み | ✅ | Tunnel 経由で画面（SPA 200）・API（ログイン/タスク/プロジェクト/通知/監査）・認証（JWT/RBAC）・DB 接続（/health database=ok・Neon 接続実証） |
| 7 | README・要件・設計・API・DB・テスト・運用・復旧手順を更新済み | ✅ | README、PRODUCTION_DEPLOYMENT.md（Neon/バックアップ/復旧）、MVP_DEMO.md（systemd 運用）、OPS_LEDGER.md（インシデント・検証実績）、state.json |
| 8 | Critical/High 問題が解消され残存リスクが記録済み | ✅ | HTTP 530 障害（High）解消＋再発防止。Ruleset の改行混入バグ（自動マージ恒久 BLOCKED）解消。残存リスクは §4 に記録 |

## 3. GitHub 運用実績（中央ポリシー準拠）

| PR | 内容 | CI | マージ |
|---|---|---|---|
| #44 | サービス復旧・systemd 常駐化・運用文書 | 9/9 PASS | Squash Merge（3d5f93b） |
| #45 | Neon 検証・バックアップ/復元演習の記録 | 9/9 PASS | Squash Merge（994e717） |

- Ruleset `central-auto-merge` の必須チェック名に混入していた末尾改行（`"Security Scan\n"`）を修正し、自動マージ経路を正常化
- Issue #31 に進捗と残依頼をコメント

## 4. 残存リスク（記録済み）

| リスク | 重大度 | 状態・対応 |
|---|---|---|
| SSH 経由デプロイ（deploy.yml）未実行 | High（運用） | GitHub Actions Secrets（PROD_HOST/PROD_USER/PROD_SSH_KEY/PROD_DIR）未提供 → **Human Gate** |
| 本番 DB の Neon 移行未実施 | Medium | 検証・手順は完了済み。承認後に `.env.production` の DATABASE_URL 差し替え＋Migration 適用 |
| 監視通知先（Webhook/メール）未設定 | Medium | ホスト内死活監視は稼働中。外部通知は通知先 URL 提供待ち |
| Visual regression（スクリーンショット比較）未導入 | Low | Storybook/スクリーンショット基盤なし。機能・a11y は CI＋実ブラウザ検証で代替 |
| 実データなし（架空データのみ） | — | 本番データ投入方針は人間の判断待ち |
| Node 20 非推奨警告（actions/cache@v4） | Low | GitHub 管理の移行待ち。機能影響なし |

## 5. 結論

- **MVP としての完了条件は全て達成**（本レポート §2 の 8 項目）。
- 本番 URL は Tunnel 経由で公開・稼働中であり、リリース後確認（ヘルス・画面・API・認証・DB・ログ・エラー率）も完了。
- 残るは **SSH デプロイ・Neon 本番移行・監視通知の Human Gate**（認証情報と承認）のみ。提供・承認を受けた時点で残工程を実行できる準備が整っている。
