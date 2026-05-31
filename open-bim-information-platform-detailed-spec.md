# Open BIM 情報基盤 詳細仕様書

## 1. 文書概要
本書は「Open BIM 情報基盤」の詳細仕様を定める。要件定義書に基づき、画面、機能、データ、処理、権限、監査、通知、運用補完事項を含む実装仕様を記載する。

## 2. システム構成概要
システムはWebフロントエンド、アプリケーションAPI、ストレージ、メタデータDB、全文検索、監査ログ基盤から構成する。情報コンテナのメタデータ管理とファイル実体管理を分離する構成とする。

## 3. 画面一覧
| 画面ID | 画面名 | 主目的 |
|---|---|---|
| SCR-001 | ログイン | 利用者認証 |
| SCR-002 | ダッシュボード | 状況把握 |
| SCR-003 | プロジェクト一覧 | プロジェクト選択 |
| SCR-004 | プロジェクト詳細 | プロジェクト設定参照 |
| SCR-005 | 情報コンテナ一覧 | コンテナ検索・参照 |
| SCR-006 | 情報コンテナ詳細 | コンテナ詳細管理 |
| SCR-007 | アップロード | ファイル登録 |
| SCR-008 | 状態遷移申請 | 遷移申請・承認 |
| SCR-009 | 命名規則設定 | 命名ルール管理 |
| SCR-010 | 属性定義設定 | 必須属性管理 |
| SCR-011 | EIR/BEP文書一覧 | 要求文書管理 |
| SCR-012 | EIR/BEP文書詳細 | 文書参照・承認 |
| SCR-013 | 監査ログ検索 | 監査追跡 |
| SCR-014 | セキュリティ分類設定 | 情報分類設定 |
| SCR-015 | ロール・権限設定 | 責任と権限管理 |
| SCR-016 | 通知センター | 通知確認 |
| SCR-017 | レポート出力 | 監査・運用レポート |
| SCR-018 | 組織設定 | 組織共通設定 |
| SCR-019 | ユーザー管理 | ユーザーと所属管理 |
| SCR-020 | 承認タスク一覧 | レビュー・承認作業 |

## 4. 機能詳細仕様
### 4.1 認証・認可
- SSO/OIDC/SAMLを想定した外部認証連携に対応する。
- 認証成功時にユーザー、所属組織、所属プロジェクト、ロール、権限セットを解決する。
- 画面権限、API権限、データ権限、状態遷移権限を分離して制御する。
- 重要操作時には再認証または多要素認証を将来拡張可能とする。

### 4.2 プロジェクト管理
- プロジェクト基本情報を登録、更新、停止できる。
- プロジェクト単位で命名規則、分類、ロール、承認経路、文書テンプレートを設定できる。
- プロジェクトには開始日、終了日、状態、組織参加者、責任者、適用標準を保持する。

### 4.3 情報コンテナ管理
- コンテナは文書、図面、モデル、IFC、BCF、その他添付物を含む。
- コンテナ登録時に識別子、名称、種別、状態、改訂、分類、作成者、所属組織、関連文書、セキュリティ分類を保持する。[cite:67][cite:68]
- 状態はWIP、Shared、Published、Archivedを標準とする。[cite:1][cite:68]
- SharedまたはPublishedを経たコンテナはArchiveに格納し履歴保持する。[cite:68]

### 4.4 命名規則検証
- 命名規則はセグメント定義方式とし、区切り文字、順序、必須/任意、桁数、許容値を設定できる。[cite:67][cite:68]
- 例: Project-Originator-Volume-Level-Type-Role-Number
- 検証結果は「適合」「警告」「不適合」の3段階以上で返却する。
- 不適合時はアップロード完了を禁止または一時保留できる。
- メタデータがCDE外へ出る場合に識別子サフィックス化できるようにする。[cite:67]

### 4.5 属性・分類管理
- 標準メタデータはStatus、Revision、Classificationを必須とする。[cite:67]
- 任意属性としてOriginator、Volume/System、Level/Location、Type、Role、Number、Milestone、Discipline等を追加可能とする。[cite:68]
- 属性定義には型、必須、初期値、選択肢、参照マスタ、表示順、API公開可否を持つ。

### 4.6 改訂管理
- 改訂コードはPxx、Cxx形式を標準とする。[cite:67]
- WIP版はP01.01のような枝番形式を扱えるものとする。[cite:67]
- 改訂時は変更理由、変更概要、差分対象、関連承認を保持する。
- 過去改訂版は削除不可とし、論理無効化のみ可能とする。

### 4.7 状態遷移ワークフロー
- 遷移候補はWIP→Shared、Shared→Published、Shared→WIP差戻し、Published→Archived、Shared/Published→Archived、必要に応じた例外遷移を設定可能とする。[cite:68]
- 各遷移にはレビュー、承認、却下、差戻し、保留の処理を定義できる。[cite:68]
- 遷移記録にはユーザー名、日時、前状態、後状態、コメント、結果を記録する。[cite:68]
- 3つの主要承認点としてcheck/review/approve、review/authorise、必要に応じてreview/acceptに対応可能な構造とする。[cite:68]

### 4.8 EIR/BEP/要求文書管理
- 文書種別はOIR、AIR、PIR、EIR、BEP、MIDP、TIDP、情報プロトコル、補足要求文書を扱えるようにする。[cite:70][cite:72]
- 各文書に版、承認状態、有効期間、責任者、参照先文書、関連成果物、提出時点を保持する。[cite:72][cite:78]
- 要求事項単位のトラッキングを可能とするため、文書内要件を明細項目として登録できるようにする。
- 要求明細には「何を」「いつ」「どのように」「誰のために」を持たせる。[cite:72]

### 4.9 役割・責任・承認権限管理
- ロールマスタは組織共通ロールとプロジェクト個別ロールを分ける。
- 契約上の立場としてappointing party、lead appointed party、appointed party相当の役割概念を保持できるようにする。[cite:70]
- 承認権限は文書種別、状態、情報分類、組織、成果物種別ごとに条件設定できる。
- 差戻し権限、例外承認権限、閲覧のみ権限、ダウンロード権限を分離する。

### 4.10 セキュリティ統制
- 情報分類は公開、限定公開、機密、要保護等の段階設定を可能とする。
- 分類ごとに閲覧、ダウンロード、外部共有、印刷、API参照の可否を設定できる。
- 外部共有は申請・承認方式とし、期限、対象、理由を保持する。
- システムは機微情報取扱いの監査ログを強化記録する。[cite:34][cite:76]
- ただし比例的セキュリティ文化の醸成や教育はシステム外運用とする。[cite:34]

### 4.11 監査ログ
- 監査対象は認証、権限変更、コンテナ作成、更新、削除、状態遷移、承認、ダウンロード、共有、設定変更、エクスポートとする。
- ログ項目はイベントID、日時、利用者、組織、IP、対象種別、対象ID、操作種別、前値、後値、理由、結果、関連ワークフローIDとする。
- ログは検索、絞込、CSV出力に対応する。
- 監査ログは改ざん防止を考慮した保管方式を採用する。

### 4.12 通知
- 通知契機はアップロード完了、命名不適合、レビュー依頼、承認依頼、差戻し、公開完了、期限超過、監査指摘、権限変更とする。
- 通知チャネルはアプリ内通知とメールを基本とする。
- 重要通知には再通知条件を設定可能とする。

### 4.13 検索・一覧
- 検索対象はコンテナ、文書、監査ログ、ユーザー、プロジェクト、承認タスクとする。
- 検索条件はキーワード、状態、改訂、分類、期間、作成者、責任者、不適合有無、情報分類とする。
- 保存検索条件機能を提供する。

### 4.14 レポート
- 提出状況レポート
- 状態別件数レポート
- 不適合件数レポート
- 改訂履歴レポート
- 承認遅延レポート
- 機密情報アクセスレポート
- 監査証跡エビデンスレポート

## 5. データモデル概要
### 5.1 主要テーブル
- organizations
- users
- user_organizations
- projects
- project_members
- roles
- permissions
- role_permissions
- naming_rules
- naming_segments
- attribute_definitions
- classifications
- information_containers
- container_files
- container_metadata
- container_revisions
- container_state_histories
- workflow_instances
- workflow_tasks
- approvals
- requirements_documents
- requirement_items
- document_relations
- security_policies
- external_share_requests
- audit_logs
- notifications
- report_jobs

### 5.2 テーブル要点
| テーブル | 主な項目 | 説明 |
|---|---|---|
| information_containers | id, project_id, identifier, title, type, current_state, current_revision, classification_id, security_level, owner_org_id | 情報コンテナ本体 |
| container_revisions | id, container_id, revision_code, version_code, file_id, change_reason, created_by, created_at | 改訂履歴 |
| container_state_histories | id, container_id, from_state, to_state, action, acted_by, acted_at, comment | 状態遷移履歴 |
| requirements_documents | id, project_id, doc_type, title, revision, status, effective_from, effective_to, owner_user_id | 要求文書 |
| requirement_items | id, document_id, item_no, what, when_required, how_required, for_whom, acceptance_criteria | 要求事項明細 |
| approvals | id, target_type, target_id, approval_stage, approver_id, result, acted_at, comment | 承認結果 |
| audit_logs | id, event_type, actor_id, target_type, target_id, before_json, after_json, reason, result, occurred_at | 監査ログ |

## 6. API概要
### 6.1 代表API
- `POST /api/auth/login`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/containers`
- `POST /api/containers`
- `POST /api/containers/{id}/upload`
- `POST /api/containers/{id}/validate-name`
- `POST /api/containers/{id}/transition`
- `GET /api/containers/{id}/history`
- `GET /api/requirements-documents`
- `POST /api/requirements-documents`
- `POST /api/approvals/{id}/act`
- `GET /api/audit-logs`
- `POST /api/external-share-requests`

### 6.2 API共通仕様
- 認証はBearer Token方式を基本とする。
- すべての更新系APIは監査ログを出力する。
- バリデーションエラーは項目単位で返却する。
- 権限不足は403、入力不備は400、競合は409を返す。

## 7. 状態遷移仕様
| 現在状態 | 操作 | 次状態 | 前提条件 | 実行者 |
|---|---|---|---|---|
| WIP | 提出 | Shared | 命名適合、必須属性充足、レビュー依頼作成 | 作成者または担当者 |
| Shared | 承認公開 | Published | レビュー完了、承認完了 | 承認者 |
| Shared | 差戻し | WIP | 差戻し理由必須 | レビュー担当者 |
| Published | 保管 | Archived | 保管対象選定済み | 管理者 |
| Shared | 保管 | Archived | 保管理由記録 | 管理者 |

## 8. 権限仕様
| 権限コード | 内容 |
|---|---|
| PROJECT_VIEW | プロジェクト参照 |
| PROJECT_EDIT | プロジェクト更新 |
| CONTAINER_CREATE | コンテナ作成 |
| CONTAINER_EDIT | コンテナ更新 |
| CONTAINER_TRANSITION | 状態遷移実行 |
| CONTAINER_APPROVE | 承認実行 |
| CONTAINER_ARCHIVE | アーカイブ実行 |
| REQUIREMENT_DOC_MANAGE | 要求文書管理 |
| SECURITY_POLICY_MANAGE | セキュリティ設定管理 |
| AUDIT_LOG_VIEW | 監査ログ参照 |
| REPORT_EXPORT | レポート出力 |
| USER_MANAGE | ユーザー管理 |
| ROLE_MANAGE | ロール管理 |

## 9. 入出力仕様
### 9.1 入力
- ファイルアップロード
- メタデータ入力
- 要求文書登録
- 承認コメント入力
- 監査条件入力
- セキュリティ申請入力

### 9.2 出力
- 一覧表示
- 詳細表示
- 監査CSV
- レポートPDF/CSV相当の出力設計
- 通知メッセージ
- APIレスポンスJSON

## 10. バリデーション仕様
- 必須項目未入力チェック
- 命名規則適合チェック
- 属性値範囲チェック
- 状態遷移可否チェック
- 権限チェック
- 重複識別子チェック
- 改訂コード形式チェック
- 要求文書参照整合チェック
- 情報分類整合チェック

## 11. 監査・保管仕様
- ログ保管期間は組織ポリシーに従い設定可能とする。
- コンテナ履歴は物理削除せず論理管理を原則とする。
- 監査エビデンスは対象選択により時系列出力できるものとする。

## 12. エラー処理仕様
- バリデーションエラーは画面で項目別表示する。
- 遷移失敗時は失敗理由と是正案内を表示する。
- ファイル保存失敗時はメタデータとファイル整合を保つロールバックを行う。
- 外部連携失敗時は再試行キューへ登録する。

## 13. 非機能詳細
- UI言語は日本語を標準とする。
- 日時はタイムゾーン対応し、監査ログはUTC保持・表示時変換を基本とする。
- 添付ファイルの大容量対応を考慮し、分割アップロード方式を選択可能とする。
- 全文検索と属性検索を併用できる構成とする。
- 監査ログ、要求文書、状態履歴は検索性能を確保するため索引設計を行う。

## 14. 実装上の運用補完事項
以下は仕様書に記載するが、システム内設定または別文書運用で確定する。
- 状態遷移承認基準
- プロジェクト固有命名標準
- 分類体系マスタ
- EIR/BEPテンプレート
- 保管年限
- 機密区分定義
- 例外承認ルール
- 教育・訓練計画
- 定期監査手順
