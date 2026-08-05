# バックアップ・復元運用ガイド

## バックアップ

### 日次自動実行

```bash
# 環境変数（.env または systemd EnvironmentFile）
BACKUP_DIR=/mnt/backup/bim
BACKUP_ENCRYPTION_KEY=<openssl rand -hex 32 で生成した鍵>
```

```bash
./scripts/backup.sh
```

systemd timer の例（`/etc/systemd/system/bim-backup.service` + `.timer`）:

```ini
[Unit]
Description=Open BIM daily backup

[Service]
Type=oneshot
WorkingDirectory=/home/kensan/Projects/Open-BIM-Information-Platform
EnvironmentFile=/etc/bim-backup.env
ExecStart=/home/kensan/Projects/Open-BIM-Information-Platform/scripts/backup.sh
```

```ini
[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

### バックアップ内容

| 項目 | 方式 |
|---|---|
| PostgreSQL | pg_dump → gzip → AES-256-CBC暗号化 |
| MinIO | mc mirror（全オブジェクト）→ 暗号化バンドル |
| 設定 | .env・Compose・nginx.conf を同梱 |
| 世代 | 直近7日を保持（`RETENTION_DAYS`で変更） |

バックアップファイルは**アプリとは別の障害ドメイン**（NAS・別拠点・オブジェクトストレージ）へ
コピーしてください。

## 復元演習

```bash
BACKUP_ENCRYPTION_KEY='...' ./scripts/restore-drill.sh ./backups/backup-20260805-023000.tar.gz.enc
```

演習は隔離Compose（`docker-compose.restore.yml`）上で実施され、以下を検証します。

- PostgreSQLの全テーブル復元（件数表示）
- 監査ログ immutable トリガーの再適用確認
- MinIOオブジェクトの復元
- サンプル5件のSHA-256一致検証
- 所要時間の記録（RTO参考値）

## 目標値（初期）

| 指標 | 目標 |
|---|---|
| RPO | 24時間以内（日次バックアップ） |
| RTO | 8時間以内（手順＋スクリプト） |
| 演習頻度 | 四半期に1回以上＋構成変更時 |

## 注意

- `BACKUP_ENCRYPTION_KEY` を失うと復元できません。鍵は別途安全に保管してください。
- バックアップスクリプトの失敗検知は exit code とログで行います（監視基盤導入まで
  手動確認またはメール/通知の追加を推奨）。
