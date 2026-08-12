#!/usr/bin/env python3
"""Seed deterministic E2E data for Playwright tests (idempotent).

Run after `alembic upgrade head` against the E2E PostgreSQL:

    cd backend && DATABASE_URL=postgresql+asyncpg://... python ../scripts/seed_e2e.py

Creates:
  - org "E2E Org" (slug e2e-org)
  - project "E2E Project" (code E2E)
  - users: approver / initiator / e2euser (member of the org)
  - containers: C1 (Shared), C2 (WIP), C3 (Published)
  - two pending approval workflows on C1 assigned to the approver
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.models.container import (  # noqa: E402
    ContainerState,
    ContainerStateHistory,
    InformationContainer,
)
from app.models.organization import Organization  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.models.user import User, UserOrganization  # noqa: E402
from app.models.workflow import Approval, WorkflowInstance, WorkflowStatus  # noqa: E402

E2E_PASSWORD = "TestPass123!"


async def main() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://bim_user:bim_password@localhost:5432/bim_e2e",
    )
    engine = create_async_engine(url)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # Remove previous seed (idempotent re-runs).
        org = (
            await db.execute(select(Organization).where(Organization.slug == "e2e-org"))
        ).scalar_one_or_none()
        if org:
            project_ids = select(Project.id).where(Project.organization_id == org.id)
            container_ids = select(InformationContainer.id).where(
                InformationContainer.project_id.in_(project_ids)
            )
            workflow_ids = select(WorkflowInstance.id).where(
                WorkflowInstance.project_id.in_(project_ids)
            )
            await db.execute(
                Approval.__table__.delete().where(
                    Approval.workflow_id.in_(workflow_ids)
                )
            )
            await db.execute(
                WorkflowInstance.__table__.delete().where(
                    WorkflowInstance.project_id.in_(project_ids)
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
                Project.__table__.delete().where(Project.organization_id == org.id)
            )
            await db.execute(
                UserOrganization.__table__.delete().where(
                    UserOrganization.organization_id == org.id
                )
            )
            await db.execute(
                Organization.__table__.delete().where(Organization.id == org.id)
            )

        for email in (
            "approver@e2e.local",
            "initiator@e2e.local",
            "e2e@test.example.com",
        ):
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user:
                await db.delete(user)
        await db.commit()

        org = Organization(id=str(uuid.uuid4()), name="E2E Org", slug="e2e-org")
        db.add(org)
        await db.flush()

        approver = User(
            id=str(uuid.uuid4()),
            email="approver@e2e.local",
            username="approver",
            full_name="E2E Approver",
            hashed_password=hash_password(E2E_PASSWORD),
        )
        initiator = User(
            id=str(uuid.uuid4()),
            email="initiator@e2e.local",
            username="initiator",
            full_name="E2E Initiator",
            hashed_password=hash_password(E2E_PASSWORD),
        )
        viewer = User(
            id=str(uuid.uuid4()),
            email="e2e@test.example.com",
            username="e2euser",
            full_name="E2E Test User",
            hashed_password=hash_password(E2E_PASSWORD),
        )
        db.add_all([approver, initiator, viewer])
        await db.flush()
        db.add_all(
            [
                UserOrganization(
                    id=str(uuid.uuid4()),
                    user_id=approver.id,
                    organization_id=org.id,
                    role_in_org="member",
                ),
                UserOrganization(
                    id=str(uuid.uuid4()),
                    user_id=initiator.id,
                    organization_id=org.id,
                    role_in_org="member",
                ),
                UserOrganization(
                    id=str(uuid.uuid4()),
                    user_id=viewer.id,
                    organization_id=org.id,
                    role_in_org="member",
                ),
            ]
        )
        project = Project(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            name="E2E Project",
            code="E2E",
            applied_standard="ISO 19650",
        )
        db.add(project)
        await db.flush()

        now = datetime.now(UTC).isoformat()
        containers = []
        for identifier, state in (
            ("E2E-ORG-ZZ-GF-DR-AR-0101", ContainerState.shared),
            ("E2E-ORG-ZZ-GF-DR-AR-0102", ContainerState.wip),
            ("E2E-ORG-ZZ-GF-DR-AR-0103", ContainerState.published),
        ):
            container = InformationContainer(
                id=str(uuid.uuid4()),
                project_id=project.id,
                owner_org_id=org.id,
                created_by=initiator.id,
                identifier=identifier,
                title=f"E2E Container {identifier[-4:]}",
                current_state=state,
                current_revision="P01",
                security_level="limited",
                naming_valid=True,
            )
            db.add(container)
            await db.flush()
            db.add(
                ContainerStateHistory(
                    container_id=container.id,
                    from_state=None,
                    to_state=state.value,
                    action="seed",
                    acted_by=initiator.id,
                    acted_at=now,
                )
            )
            containers.append(container)

        # Two pending approvals on the Shared container (C1).
        for stage in ("stage_1", "stage_2"):
            workflow = WorkflowInstance(
                id=str(uuid.uuid4()),
                project_id=project.id,
                target_type="container",
                target_id=containers[0].id,
                workflow_type="state_transition",
                status=WorkflowStatus.in_progress,
                initiated_by=initiator.id,
                comment="E2E seeded approval",
            )
            db.add(workflow)
            await db.flush()
            db.add(
                Approval(
                    id=str(uuid.uuid4()),
                    workflow_id=workflow.id,
                    target_type="container",
                    target_id=containers[0].id,
                    approval_stage=stage,
                    approver_id=approver.id,
                )
            )

        await db.commit()
        print(
            f"✅ E2E seed complete: org={org.id} project={project.id} "
            f"approver={approver.id}"
        )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
