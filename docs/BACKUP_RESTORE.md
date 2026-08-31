# バックアップ・復元運用ガイド

## バックアップ

### 日次自動実行

```bash
# 環境変数（.env または systemd EnvironmentFile）
BACKUP_DIR=/mnt/backup/bim
BACKUP_ENCRYPTION_KEY=<openssl rand -hex 32 で生成した鍵>
POSTGRES_BACKUP_MODE=host  # Local PostgreSQL。Compose内DBは compose
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
PG_DUMP_BIN=/usr/lib/postgresql/16/bin/pg_dump  # source DB major versionと合わせる
PSQL_BIN=/usr/lib/postgresql/16/bin/psql
MINIO_BACKUP_MODE=host     # host上のMinIO。Compose内MinIOは compose
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

生成物と一時ファイルは `umask 077` で owner-only とする。`host` mode は
systemd で動く backend と同じ Local PostgreSQL / MinIO を対象にし、`compose` mode は
Compose network 内の service を対象にする。DB名・接続先・modeを実行前に必ず確認すること。
`PG_DUMP_BIN` と復元用 PostgreSQL image の major version は source DB と一致させる。
EnvironmentFile の `BACKUP_DIR` を一時的に変更せず出力先だけ切り替える場合は、
`BACKUP_DIR_OVERRIDE=/writable/path` を指定できる。

MinIO 障害時にDBの復旧点だけを緊急確保する場合は、明示的に
`MINIO_BACKUP_MODE=skip ALLOW_DB_ONLY_BACKUP=true` を指定する。生成物は
`backup-db-only-*` となり、MinIOを含まないため日次完全バックアップやRPO達成には数えない。
DB-only と完全バックアップの retention は分離され、DB-only 実行は完全バックアップを
削除しない。

完全バックアップでは暗号化前に、DBの全`container_files.storage_key`がmirror内に存在し、
DBレコード数とMinIO object数が一致することを検証する。不一致時はexit code 1で終了し、
完全バックアップ成果物を生成しない。DB-onlyはこの検査を意図的に省略するため、障害復旧時の
ファイル復元には使用できない。

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
- 全ファイルのSHA-256一致検証
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
