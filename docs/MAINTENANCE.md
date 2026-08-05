# 定期保守手順

> 依存更新・証明書・シークレット・ライフサイクル管理の手順。実績は運用台帳に記録する。

## 1. 依存・脆弱性管理（月次）

```bash
# バックエンド
cd backend && pip install -e ".[dev]" && pip-audit

# フロントエンド
cd frontend && npm audit --audit-level=high

# SBOM 再生成（依存変更時）
./scripts/sbom.sh
```

- Critical/High は即対応（更新→テスト→CI確認）
- 依存のメジャー更新は専用PRで実施
- 利用しているOSSのライセンス・EOLを月次で確認

## 2. 証明書・ドメイン（月次確認 / 更新時）

- TLS証明書: `openssl x509 -enddate -noout -in certs/fullchain.pem` で期限確認
- 更新は Let's Encrypt 等の自動更新を推奨（ACMEチャレンジは nginx の
  `/.well-known/acme-challenge/` 経由）
- ドメイン・DNSレコードは Cloudflare ダッシュボードで確認

## 3. シークレット・APIキー（四半期ローテーション）

| 対象 | 保管場所 | ローテーション手順 |
|---|---|---|
| `SECRET_KEY` | 本番 `.env`（/ シークレット管理基盤） | 新値を生成→再起動→旧値を破棄 |
| `POSTGRES_PASSWORD` | 本番 `.env` | 新値生成→DBユーザー更新→全接続元更新 |
| `MINIO_ROOT_PASSWORD` | 本番 `.env` | 新値生成→MinIO設定更新→再起動 |
| `BACKUP_ENCRYPTION_KEY` | 別途安全保管 | 旧バックアップの再暗号化を伴うため計画的に実施 |
| Cloudflare/Neon APIキー | 環境変数・Secrets | 各コンソールで再発行→参照元更新→旧キー失効 |

## 4. ランタイム・OS・EOL

- Ubuntu 22.04 LTS（2027年4月まで標準サポート）→ 24.04 LTS 移行を計画
- Python 3.11（2027年10月 EOL）→ 3.12/3.13 移行を2026年度内に計画
- PostgreSQL 15（2027年11月 EOL）→ 16/17 移行を計画
- Node.js 22 LTS / React 19 / FastAPI 等はリリースノートを追跡

## 5. 容量・予算・課金

- Cloudflare: Pages/Workers 利用量、DNS・Tunnel のリクエスト量
- Neon: プロジェクト容量・compute時間・ストレージ・月次リセット
- ホスト: ディスク使用率（バックアップ含む）・メモリ・CPU
- 各サービスの予算アラートを設定し、月次で確認
