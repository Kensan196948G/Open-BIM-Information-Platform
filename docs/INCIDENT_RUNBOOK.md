# インシデント対応 Runbook

> 実環境の連絡先・担当者は本番環境確定時に記入する。

## 1. 重大度定義

| レベル | 定義 | 初動 | 応答目標 |
|---|---|---|---|
| P1 | 全サービス停止・データ損失・セキュリティ侵害 | 即時切り分け・ロールバック | 30分以内 |
| P2 | 一部機能停止・性能劣化 | 該当サービス再起動→調査 | 2時間以内 |
| P3 | 軽微な不具合・監視アラート | 次リリースで対応 | 営業日内 |

## 2. 一次切り分けフロー

```
1. 症状確認: 全ユーザーか一部か / いつから / 変更直後か
2. ヘルスチェック: curl https://<host>/health
3. コンテナ状態: docker compose -f docker-compose.prod.yml ps
4. ログ確認: docker compose -f docker-compose.prod.yml logs --tail=200 backend frontend
5. リソース確認: docker stats / df -h / DB接続数
6. 直近変更の確認: git log --oneline -10 / リリース記録
```

## 3. 障害別対応

| 症状 | 原因候補 | 対処 |
|---|---|---|
| `/health` 503（database=error） | DB停止・接続不可 | `docker compose ... up -d postgres` → ログ確認 → 復旧不能ならDBリストア |
| ログイン不可・401連発 | SECRET_KEY不一致・トークン失効 | `.env` のSECRET_KEY確認・バックエンド再起動 |
| アップロード 503 | MinIO/ClamAV停止 | `docker compose ... up -d minio clamav` → healthcheck待ち |
| 画面が真っ白 | フロントビルド不整合 | nginxログ確認 → イメージ再ビルド |
| ディスク逼迫 | バックアップ/ログ肥大 | 不要ログ削除・容量追加・保持期間見直し |
| ウイルス検知 | 協力会社ファイル | アップロード遮断・検体隔離・関係者連絡（セキュリティインシデント手順） |

## 4. ロールバック

```bash
# コード: 前安定タグへ
git checkout <previous-stable-tag>
docker compose -f docker-compose.prod.yml build backend frontend
docker compose -f docker-compose.prod.yml up -d backend frontend

# DB: 1つ前のマイグレーションへ
docker compose -f docker-compose.prod.yml run --rm backend alembic downgrade -1

# データ: 暗号化バックアップから復元
BACKUP_ENCRYPTION_KEY='...' ./scripts/restore-drill.sh backups/backup-<ts>.tar.gz.enc
```

> 監査ログは immutable トリガーのため、ロールバック時も削除・更新されない（仕様）。

## 5. 復旧・連絡・記録

- 復旧確認: `/health` 200・主要機能スモーク・監査ログ記録
- 連絡: 影響範囲・復旧見込みを関係者へ（メール/Teams）
- 記録: 発生日時・影響・原因・対処・再発防止を運用台帳と Issue に残す

## 6. メンテナンス・データ訂正

- メンテナンス時間は事前通知し、可能ならバックアップ取得後に実施
- データ訂正は管理者限定で実施し、訂正前後の値を監査ログへ記録する
- 一括訂正はトランザクション内で行い、先にバックアップを取得する

## 7. セキュリティインシデント

1. アクセス遮断（ネットワーク/アカウント無効化）
2. 監査ログ・ログの保全（コピー取得）
3. 影響範囲調査（認証失敗、異常DL、設定変更履歴）
4. 復旧・再発防止・報告（組織のインシデント手順に従う）
