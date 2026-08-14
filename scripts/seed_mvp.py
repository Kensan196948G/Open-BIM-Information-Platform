#!/usr/bin/env python3
"""Seed deterministic MVP demo data (fictional) for the Open BIM Platform.

Run after `alembic upgrade head` against the MVP PostgreSQL:

    cd backend && DATABASE_URL=postgresql+asyncpg://... python ../scripts/seed_mvp.py

What it creates (all values are FICTIONAL — no real persons/companies/addresses):
  - Orgs:     未来建設株式会社 (mirai-kensetsu) / おおぞら設計株式会社 (ozora-sekkei)
  - Projects: 未来橋架替工事 (FUT-BR-2026) / 臨海部護岸整備工事 (RNK-2026)
              宮ヶ丘複合開発計画 (MGM-2027) — across orgs and statuses
  - Users:    org_admin / reviewer / member for each org, plus a platform admin.
              Password for every demo user: DemoPass123!
  - Containers: WIP / Shared / Published / Archived in ISO-19650-ish identifiers
                across document / drawing / model / ifc types and security levels
  - Revisions + a few dummy files (checksum placeholders, no real payload)
  - Approvals: one pending workflow per project (assigned to the reviewer)
               and one completed workflow (for history)
  - Notifications: assigned-approval notices for reviewers
  - Requirements docs: EIR / BEP with items
  - Naming rules: ISO 19650 default per project (JSON segments)
  - Audit log rows for the seeded operations (append-only)

Idempotent: safe to re-run. Existing demo users are reused; orgs/projects
are deleted and re-created keyed on fixed slugs/codes, and the audit log is
append-only so re-runs add new rows rather than mutating old ones.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import hash_password  # noqa: E402
from app.models.container import (  # noqa: E402
    ContainerFile,
    ContainerRevision,
    ContainerState,
    ContainerStateHistory,
    ContainerType,
    InformationContainer,
    SecurityLevel,
)
from app.models.naming_rule import ProjectNamingRule  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.organization import Organization  # noqa: E402
from app.models.project import Project, ProjectMember, ProjectStatus  # noqa: E402
from app.models.requirements import (  # noqa: E402
    DocumentStatus,
    DocumentType,
    ItemStatus,
    RequirementItem,
    RequirementsDocument,
)
from app.models.user import User, UserOrganization  # noqa: E402
from app.models.workflow import (  # noqa: E402
    Approval,
    ApprovalResult,
    WorkflowInstance,
    WorkflowStatus,
)
from app.services.audit import record_audit  # noqa: E402

DEMO_PASSWORD = "DemoPass123!"
ORG_SLUGS = ("mirai-kensetsu", "ozora-sekkei")


def _iso_now() -> str:
    return datetime.now(UTC).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())


async def _wipe(org: Organization, db: AsyncSession) -> None:
    """Delete org-scoped demo rows (users are reused, never deleted)."""
    project_ids = select(Project.id).where(Project.organization_id == org.id)
    container_ids = select(InformationContainer.id).where(
        InformationContainer.project_id.in_(project_ids)
    )
    workflow_ids = select(WorkflowInstance.id).where(
        WorkflowInstance.project_id.in_(project_ids)
    )
    doc_ids = select(RequirementsDocument.id).where(
        RequirementsDocument.project_id.in_(project_ids)
    )
    await db.execute(
        Approval.__table__.delete().where(Approval.workflow_id.in_(workflow_ids))
    )
    await db.execute(
        ProjectMember.__table__.delete().where(ProjectMember.project_id.in_(project_ids))
    )
    await db.execute(
        ContainerFile.__table__.delete().where(
            ContainerFile.container_id.in_(container_ids)
        )
    )
    await db.execute(
        ContainerRevision.__table__.delete().where(
            ContainerRevision.container_id.in_(container_ids)
        )
    )
    await db.execute(
        ContainerStateHistory.__table__.delete().where(
            ContainerStateHistory.container_id.in_(container_ids)
        )
    )
    await db.execute(
        InformationContainer.__table__.delete().where(
            InformationContainer.project_id.in_(project_ids)
        )
    )
    await db.execute(
        RequirementItem.__table__.delete().where(
            RequirementItem.document_id.in_(doc_ids)
        )
    )
    await db.execute(
        RequirementsDocument.__table__.delete().where(
            RequirementsDocument.project_id.in_(project_ids)
        )
    )
    await db.execute(
        WorkflowInstance.__table__.delete().where(
            WorkflowInstance.project_id.in_(project_ids)
        )
    )
    await db.execute(
        ProjectNamingRule.__table__.delete().where(
            ProjectNamingRule.project_id.in_(project_ids)
        )
    )
    await db.execute(Project.__table__.delete().where(Project.organization_id == org.id))
    await db.execute(
        UserOrganization.__table__.delete().where(
            UserOrganization.organization_id == org.id
        )
    )


async def main() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://bim_user:bim_password@localhost:5432/bim_mvp",
    )
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # ─── 1. Organizations ───────────────────────────────────────────────────
        orgs: dict[str, Organization] = {}
        for slug, name, desc in (
            (
                "mirai-kensetsu",
                "未来建設株式会社",
                "架空の総合建設会社（デモ用）: 土木・建築の設計・施工を担う",
            ),
            (
                "ozora-sekkei",
                "おおぞら設計株式会社",
                "架空の設計事務所（デモ用）: 意匠・構造・設備設計を担う",
            ),
        ):
            org = (
                await db.execute(select(Organization).where(Organization.slug == slug))
            ).scalar_one_or_none()
            if org:
                await _wipe(org, db)
                await db.execute(
                    Organization.__table__.delete().where(Organization.id == org.id)
                )
            org = Organization(id=_uuid(), name=name, slug=slug, description=desc)
            db.add(org)
            await db.flush()
            orgs[slug] = org

        # ─── 2. Users (reused across runs; password reset every run) ───────────
        existing_users: dict[str, User] = {}
        for email in (
            "admin@mirai.example.jp",
            "director@mirai.example.jp",
            "reviewer@mirai.example.jp",
            "engineer@mirai.example.jp",
            "chief@ozora.example.jp",
            "designer@ozora.example.jp",
            "platform-admin@example.jp",
        ):
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            existing_users[email] = user

        async def _user(email: str, username: str, full_name: str) -> User:
            user = existing_users.get(email)
            if user is not None:
                user.username = username
                user.full_name = full_name
                user.hashed_password = hash_password(DEMO_PASSWORD)
                user.is_active = True
                return user
            user = User(
                id=_uuid(),
                email=email,
                username=username,
                full_name=full_name,
                hashed_password=hash_password(DEMO_PASSWORD),
            )
            db.add(user)
            await db.flush()
            return user

        mirai_admin = await _user(
            "admin@mirai.example.jp", "mirai-admin", "青木 大輔"
        )
        mirai_reviewer = await _user(
            "reviewer@mirai.example.jp", "mirai-reviewer", "井上 美咲"
        )
        mirai_engineer = await _user(
            "engineer@mirai.example.jp", "mirai-engineer", "加藤 健一"
        )
        ozora_chief = await _user(
            "chief@ozora.example.jp", "ozora-chief", "小林 直樹"
        )
        ozora_designer = await _user(
            "designer@ozora.example.jp", "ozora-designer", "高橋 さくら"
        )
        platform_admin = await _user(
            "platform-admin@example.jp", "platform-admin", "システム管理者"
        )
        platform_admin.is_platform_admin = True
        await db.flush()

        # Memberships (roles: org_admin / reviewer / member)
        db.add_all(
            [
                UserOrganization(
                    id=_uuid(),
                    user_id=mirai_admin.id,
                    organization_id=orgs["mirai-kensetsu"].id,
                    role_in_org="org_admin",
                    is_org_admin=True,
                ),
                UserOrganization(
                    id=_uuid(),
                    user_id=mirai_reviewer.id,
                    organization_id=orgs["mirai-kensetsu"].id,
                    role_in_org="reviewer",
                ),
                UserOrganization(
                    id=_uuid(),
                    user_id=mirai_engineer.id,
                    organization_id=orgs["mirai-kensetsu"].id,
                    role_in_org="member",
                ),
                UserOrganization(
                    id=_uuid(),
                    user_id=ozora_chief.id,
                    organization_id=orgs["ozora-sekkei"].id,
                    role_in_org="org_admin",
                    is_org_admin=True,
                ),
                UserOrganization(
                    id=_uuid(),
                    user_id=ozora_designer.id,
                    organization_id=orgs["ozora-sekkei"].id,
                    role_in_org="member",
                ),
            ]
        )

        # ─── 3. Projects ────────────────────────────────────────────────────────
        now = datetime.now(UTC)
        project_specs: list[tuple[str, str, str, str, ProjectStatus, str, date, date]] = [
            (
                "FUT-BR-2026",
                "未来橋架替工事",
                "架空の橋梁架替プロジェクト（デモ用）。施工・設計の情報連携を実演する。",
                "mirai-kensetsu",
                ProjectStatus.active,
                "ISO 19650",
                date(2026, 4, 1),
                date(2027, 9, 30),
            ),
            (
                "RNK-2026",
                "臨海部護岸整備工事",
                "架空の護岸整備プロジェクト（デモ用）。港湾土木の情報管理フローを実演する。",
                "mirai-kensetsu",
                ProjectStatus.active,
                "ISO 19650",
                date(2026, 6, 15),
                date(2028, 3, 31),
            ),
            (
                "MGM-2027",
                "宮ヶ丘複合開発計画",
                "架空の複合開発プロジェクト（デモ用）。設計フェーズの要求文書管理を実演する。",
                "ozora-sekkei",
                ProjectStatus.active,
                "ISO 19650",
                date(2026, 8, 1),
                date(2029, 12, 31),
            ),
        ]
        projects: dict[str, Project] = {}
        for code, name, desc, org_key, status, std, start, end in project_specs:
            project = Project(
                id=_uuid(),
                organization_id=orgs[org_key].id,
                name=name,
                code=code,
                description=desc,
                status=status,
                start_date=start,
                end_date=end,
                applied_standard=std,
            )
            db.add(project)
            await db.flush()
            projects[code] = project
            # Project members
            if org_key == "mirai-kensetsu":
                lead = mirai_engineer
                reviewer = mirai_reviewer
                admin = mirai_admin
            else:
                lead = ozora_designer
                reviewer = ozora_chief
                admin = ozora_chief
            db.add_all(
                [
                    ProjectMember(
                        id=_uuid(),
                        project_id=project.id,
                        user_id=lead.id,
                        contract_role="設計担当",
                        is_lead=True,
                    ),
                    ProjectMember(
                        id=_uuid(),
                        project_id=project.id,
                        user_id=reviewer.id,
                        contract_role="レビュー担当",
                    ),
                    ProjectMember(
                        id=_uuid(),
                        project_id=project.id,
                        user_id=admin.id,
                        contract_role="プロジェクト管理者",
                    ),
                ]
            )
            # Naming rule (ISO 19650 default segments)
            db.add(
                ProjectNamingRule(
                    id=_uuid(),
                    project_id=project.id,
                    separator="-",
                    segments=[
                        {
                            "key": "project",
                            "label": "Project",
                            "required": True,
                            "min_length": 2,
                            "max_length": 20,
                            "pattern": "^[A-Z0-9]+$",
                            "description": "Project code (uppercase alphanumeric)",
                        },
                        {
                            "key": "originator",
                            "label": "Originator",
                            "required": True,
                            "min_length": 2,
                            "max_length": 10,
                            "pattern": "^[A-Z0-9]+$",
                            "description": "Organization code of the originator",
                        },
                        {
                            "key": "volume_system",
                            "label": "Volume/System",
                            "required": False,
                            "max_length": 6,
                            "pattern": "^[A-Z0-9]+$",
                            "description": "Volume or building system (e.g. ZZ)",
                        },
                        {
                            "key": "level_location",
                            "label": "Level/Location",
                            "required": False,
                            "max_length": 6,
                            "pattern": "^[A-Z0-9]+$",
                            "description": "Floor or location code",
                        },
                        {
                            "key": "type",
                            "label": "Type",
                            "required": True,
                            "min_length": 2,
                            "max_length": 4,
                            "allowed_values": [
                                "DR", "M3", "MO", "MS", "WD", "RP", "SK", "SP", "XX",
                            ],
                            "description": "Information type code",
                        },
                        {
                            "key": "role",
                            "label": "Role",
                            "required": True,
                            "max_length": 4,
                            "pattern": "^[A-Z]{1,4}$",
                            "description": "Discipline/role code (e.g. AR, ST)",
                        },
                        {
                            "key": "number",
                            "label": "Number",
                            "required": True,
                            "min_length": 4,
                            "max_length": 6,
                            "pattern": "^\\d+$",
                            "description": "Sequential number",
                        },
                    ],
                )
            )
            # Requirements documents (EIR + BEP for each project)
            eir = RequirementsDocument(
                id=_uuid(),
                project_id=project.id,
                owner_user_id=admin.id,
                doc_type=DocumentType.eir,
                title=f"{name} 交換用情報要求事項（EIR）",
                revision="02",
                status=DocumentStatus.approved,
                effective_from=(now - timedelta(days=30)).strftime("%Y-%m-%d"),
                description="架空のEIR（デモ用）。情報交換の要求事項を定める。",
            )
            bep = RequirementsDocument(
                id=_uuid(),
                project_id=project.id,
                owner_user_id=lead.id,
                doc_type=DocumentType.bep,
                title=f"{name} BIM実行計画書（BEP）",
                revision="01",
                status=DocumentStatus.under_review,
                description="架空のBEP（デモ用）。BIMの活用方針と納品物を定める。",
            )
            db.add_all([eir, bep])
            await db.flush()
            db.add_all(
                [
                    RequirementItem(
                        id=_uuid(),
                        document_id=eir.id,
                        item_no="EIR-01",
                        what="設計段階の構造モデル（IFC）を提供する",
                        when_required="基本設計完了時",
                        how_required="IFC 4.0 / 座標系は平面直角座標系",
                        for_whom="発注者・設計者",
                        acceptance_criteria="干渉チェック結果を含む",
                        responsible_user_id=lead.id,
                        status=ItemStatus.met,
                        notes="デモ用の架空要求項目",
                    ),
                    RequirementItem(
                        id=_uuid(),
                        document_id=eir.id,
                        item_no="EIR-02",
                        what="施工段階の施工モデル（IFC）を提供する",
                        when_required="着工前",
                        how_required="IFC 4.0 / LOD 350 以上",
                        for_whom="施工者",
                        acceptance_criteria="品質チェックレポート添付",
                        responsible_user_id=lead.id,
                        status=ItemStatus.not_met,
                        notes="デモ用の架空要求項目",
                    ),
                    RequirementItem(
                        id=_uuid(),
                        document_id=bep.id,
                        item_no="BEP-01",
                        what="プロジェクトのBIM活用目標と役割分担を定める",
                        when_required="プロジェクト開始時",
                        how_required="BEP本文に記載",
                        for_whom="全関係者",
                        acceptance_criteria="関係者全員の合意",
                        responsible_user_id=admin.id,
                        status=ItemStatus.met,
                    ),
                    RequirementItem(
                        id=_uuid(),
                        document_id=bep.id,
                        item_no="BEP-02",
                        what="共有データ環境（CDE）の運用ルールを定める",
                        when_required="情報共有開始前",
                        how_required="CDE運用ガイドとして記載",
                        for_whom="全関係者",
                        acceptance_criteria="命名規則・状態遷移の定義",
                        responsible_user_id=admin.id,
                        status=ItemStatus.partial,
                        notes="デモ用の架空要求項目",
                    ),
                ]
            )

        # ─── 4. Containers (per project, all CDE states) ───────────────────────
        container_specs = {
            "FUT-BR-2026": [
                # (identifier, title, type, state, security, revision, branch)
                (
                    "FUT-BR-MRK-ZZ-GF-DR-AR-0001",
                    "一般図_橋梁一般図（全体）",
                    ContainerType.drawing,
                    ContainerState.published,
                    SecurityLevel.public,
                    "P01",
                    None,
                ),
                (
                    "FUT-BR-MRK-ZZ-01-DR-ST-0002",
                    "下部工_橋台構造図",
                    ContainerType.drawing,
                    ContainerState.shared,
                    SecurityLevel.limited,
                    "P02",
                    "P02.01",
                ),
                (
                    "FUT-BR-MRK-ZZ-02-M3-ST-0003",
                    "上部工_主桁モデル（IFC）",
                    ContainerType.model,
                    ContainerState.wip,
                    SecurityLevel.confidential,
                    "P01",
                    "P01.02",
                ),
                (
                    "FUT-BR-MRK-ZZ-GF-WD-SP-0004",
                    "特記仕様書_塗装仕様書",
                    ContainerType.document,
                    ContainerState.archived,
                    SecurityLevel.limited,
                    "C01",
                    None,
                ),
                (
                    "FUT-BR-MRK-ZZ-GF-RP-GE-0005",
                    "調査報告書_地質調査報告書",
                    ContainerType.document,
                    ContainerState.published,
                    SecurityLevel.limited,
                    "P01",
                    None,
                ),
            ],
            "RNK-2026": [
                (
                    "RNK-MRK-ZZ-GF-DR-CV-0101",
                    "平面図_護岸工事平面図",
                    ContainerType.drawing,
                    ContainerState.shared,
                    SecurityLevel.limited,
                    "P01",
                    "P01.01",
                ),
                (
                    "RNK-MRK-ZZ-01-M3-CV-0102",
                    "断面モデル_護岸断面モデル",
                    ContainerType.model,
                    ContainerState.wip,
                    SecurityLevel.confidential,
                    "P01",
                    "P01.03",
                ),
                (
                    "RNK-MRK-ZZ-GF-WD-SP-0103",
                    "特記仕様書_捨石工仕様書",
                    ContainerType.document,
                    ContainerState.published,
                    SecurityLevel.public,
                    "P01",
                    None,
                ),
            ],
            "MGM-2027": [
                (
                    "MGM-OZK-ZZ-B1-DR-AR-0201",
                    "計画図_地下1階平面計画図",
                    ContainerType.drawing,
                    ContainerState.wip,
                    SecurityLevel.confidential,
                    "P01",
                    "P01.01",
                ),
                (
                    "MGM-OZK-ZZ-03-M3-ST-0202",
                    "構造モデル_3階躯体モデル",
                    ContainerType.model,
                    ContainerState.shared,
                    SecurityLevel.limited,
                    "P01",
                    None,
                ),
                (
                    "MGM-OZK-ZZ-GF-RP-PM-0203",
                    "報告書_要求事項整理メモ",
                    ContainerType.document,
                    ContainerState.published,
                    SecurityLevel.public,
                    "P01",
                    None,
                ),
            ],
        }

        creators = {
            "FUT-BR-2026": (mirai_engineer, mirai_reviewer, mirai_admin),
            "RNK-2026": (mirai_engineer, mirai_reviewer, mirai_admin),
            "MGM-2027": (ozora_designer, ozora_chief, ozora_chief),
        }

        for code, specs in container_specs.items():
            project = projects[code]
            engineer, reviewer, admin = creators[code]
            for identifier, title, ctype, state, seclvl, rev, branch in specs:
                created_by = (
                    reviewer if state == ContainerState.shared else engineer
                )
                container = InformationContainer(
                    id=_uuid(),
                    project_id=project.id,
                    owner_org_id=project.organization_id,
                    created_by=created_by.id,
                    identifier=identifier,
                    title=title,
                    container_type=ctype,
                    current_state=state,
                    current_revision=rev,
                    current_branch=branch,
                    security_level=seclvl,
                    naming_valid=True,
                )
                db.add(container)
                await db.flush()
                # State history: a plausible linear path to the current state
                history_flow: list[tuple[ContainerState | None, ContainerState]] = []
                if state == ContainerState.wip:
                    history_flow = [(None, ContainerState.wip)]
                elif state == ContainerState.shared:
                    history_flow = [
                        (None, ContainerState.wip),
                        (ContainerState.wip, ContainerState.shared),
                    ]
                elif state == ContainerState.published:
                    history_flow = [
                        (None, ContainerState.wip),
                        (ContainerState.wip, ContainerState.shared),
                        (ContainerState.shared, ContainerState.published),
                    ]
                elif state == ContainerState.archived:
                    history_flow = [
                        (None, ContainerState.wip),
                        (ContainerState.wip, ContainerState.shared),
                        (ContainerState.shared, ContainerState.published),
                        (ContainerState.published, ContainerState.archived),
                    ]
                for from_state, to_state in history_flow:
                    db.add(
                        ContainerStateHistory(
                            id=_uuid(),
                            container_id=container.id,
                            from_state=from_state.value if from_state else None,
                            to_state=to_state.value,
                            action="seed",
                            acted_by=created_by.id,
                            acted_at=_iso_now(),
                            comment="デモ用シード投入",
                        )
                    )
                # Revisions + dummy files (published/shared containers)
                revision = ContainerRevision(
                    id=_uuid(),
                    container_id=container.id,
                    revision_code=rev.split(".")[0],
                    version_code=rev,
                    change_reason="デモ用の初期登録",
                    change_summary="架空データの初期版",
                    created_by=created_by.id,
                )
                db.add(revision)
                await db.flush()
                if state in (ContainerState.shared, ContainerState.published):
                    db.add(
                        ContainerFile(
                            id=_uuid(),
                            container_id=container.id,
                            revision_id=revision.id,
                            original_filename=f"{identifier}.{'ifc' if ctype in (ContainerType.model, ContainerType.ifc) else 'pdf'}",
                            storage_key=f"demo/{project.code}/{container.id}/{identifier}",
                            content_type=(
                                "application/octet-stream"
                                if ctype in (ContainerType.model, ContainerType.ifc)
                                else "application/pdf"
                            ),
                            file_size_bytes=2048,
                            checksum_sha256=(
                                "d" * 64
                            ),  # placeholder checksum for demo rows
                            uploaded_by=created_by.id,
                        )
                    )

            # ─── 5. Workflows / approvals ─────────────────────────────────────
            # One pending approval (reviewer) + one completed approval each
            shared_container = None
            published_container = None
            for c in (await db.execute(
                select(InformationContainer).where(
                    InformationContainer.project_id == project.id
                )
            )).scalars().all():
                if c.current_state == ContainerState.shared and shared_container is None:
                    shared_container = c
                if (
                    c.current_state == ContainerState.published
                    and published_container is None
                ):
                    published_container = c

            if shared_container is not None:
                wf = WorkflowInstance(
                    id=_uuid(),
                    project_id=project.id,
                    target_type="container",
                    target_id=shared_container.id,
                    workflow_type="state_transition",
                    status=WorkflowStatus.in_progress,
                    initiated_by=engineer.id,
                    comment="デモ用: Shared → Published の承認依頼",
                )
                db.add(wf)
                await db.flush()
                db.add(
                    Approval(
                        id=_uuid(),
                        workflow_id=wf.id,
                        target_type="container",
                        target_id=shared_container.id,
                        approval_stage="stage_1",
                        approver_id=reviewer.id,
                    )
                )
                db.add(
                    Notification(
                        id=_uuid(),
                        user_id=reviewer.id,
                        event_type="workflow.assigned",
                        title="承認依頼が届きました",
                        body=f"「{shared_container.title}」の承認依頼です（デモ用シード）",
                        link=f"/approvals?workflow={wf.id}",
                    )
                )

            if published_container is not None:
                wf_done = WorkflowInstance(
                    id=_uuid(),
                    project_id=project.id,
                    target_type="container",
                    target_id=published_container.id,
                    workflow_type="state_transition",
                    status=WorkflowStatus.completed,
                    initiated_by=engineer.id,
                    comment="デモ用: 完了済みの承認フロー",
                )
                db.add(wf_done)
                await db.flush()
                db.add(
                    Approval(
                        id=_uuid(),
                        workflow_id=wf_done.id,
                        target_type="container",
                        target_id=published_container.id,
                        approval_stage="stage_1",
                        approver_id=reviewer.id,
                        result=ApprovalResult.approved,
                        acted_at=_iso_now(),
                        comment="デモ用に承認済み",
                    )
                )

            # ─── 6. Audit log (append-only; one row per seeded object type) ────
            record_audit(
                db,
                event_type="seed.mvp",
                operation="seed",
                target_type="project",
                target_id=project.id,
                actor_id=admin.id,
                after_json={
                    "code": project.code,
                    "name": project.name,
                    "containers": len(specs),
                },
                reason="MVPデモ用シード投入（架空データ）",
                result="success",
            )

        record_audit(
            db,
            event_type="seed.mvp",
            operation="seed",
            target_type="platform",
            actor_id=platform_admin.id,
            after_json={"orgs": list(ORG_SLUGS)},
            reason="MVPデモ用シード投入（架空データ）",
            result="success",
        )
        await db.commit()

        counts = {
            "orgs": len(orgs),
            "projects": len(projects),
            "users": len(existing_users) + 1,
            "containers": sum(len(v) for v in container_specs.values()),
        }
        print(
            f"✅ MVP seed complete: {counts} | "
            f"login demo users with password '{DEMO_PASSWORD}' "
            f"(admin@mirai.example.jp / reviewer@mirai.example.jp / "
            f"engineer@mirai.example.jp / chief@ozora.example.jp / "
            f"designer@ozora.example.jp / platform-admin@example.jp)"
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
