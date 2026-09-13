from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.db.models import AuditEventModel, BackgroundJobModel, ContentItemModel
from app.domain.errors import ContentNotApprovedError
from app.services.content_studio import publish_content_job
from app.services.external_operations import begin_external_operation


@pytest.mark.parametrize("delivery_status", ["publishing", "publish_retrying", "publish_unknown"])
def test_unresolved_delivery_cannot_be_reset_by_edit_or_approval(
    authenticated, delivery_status
) -> None:
    context, headers = authenticated
    response = context.client.post(
        "/api/v1/studio/content/generate",
        headers=headers,
        json={
            "product_id": "A101",
            "content_format": "sales_post",
            "platform": "facebook",
            "tone": "friendly",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    with context.session_factory() as session:
        row = session.get(ContentItemModel, item["id"])
        assert row is not None
        row.status = delivery_status
        session.commit()
    path = f"/api/v1/studio/content/{item['id']}"
    for result in (
        context.client.patch(path, headers=headers, json={"caption": "Replacement"}),
        context.client.post(f"{path}/regenerate", headers=headers, json={"section": "caption"}),
        context.client.post(f"{path}/approve", headers=headers),
        context.client.post(f"{path}/publish", headers=headers),
    ):
        assert result.status_code == 409, result.text
    with context.session_factory() as session:
        row = session.get(ContentItemModel, item["id"])
        assert row is not None
        assert (row.status, row.caption, row.current_version) == (
            delivery_status,
            item["caption"],
            item["current_version"],
        )


def test_content_schedule_keeps_its_instant_after_reload_and_edit(authenticated) -> None:
    context, headers = authenticated
    generated = context.client.post(
        "/api/v1/studio/content/generate",
        headers=headers,
        json={
            "product_id": "A101",
            "content_format": "sales_post",
            "platform": "instagram",
            "tone": "friendly",
            "scheduled_for": "2030-01-31T12:00:00+02:00",
        },
    )
    assert generated.status_code == 201, generated.text
    item_id = generated.json()["id"]

    def instant(value: str) -> datetime:
        result = datetime.fromisoformat(value)
        assert result.tzinfo is not None, "API timestamps must identify their timezone"
        return result.astimezone(UTC)

    listed = context.client.get("/api/v1/studio/content", headers=headers).json()
    saved = next(item for item in listed if item["id"] == item_id)
    assert instant(saved["scheduled_for"]) == datetime(2030, 1, 31, 10, tzinfo=UTC)
    edited = context.client.patch(
        f"/api/v1/studio/content/{item_id}",
        headers=headers,
        json={"scheduled_for": "2030-02-01T09:00:00-05:00"},
    )
    assert edited.status_code == 200, edited.text
    listed = context.client.get("/api/v1/studio/content", headers=headers).json()
    saved = next(item for item in listed if item["id"] == item_id)
    assert instant(saved["scheduled_for"]) == datetime(2030, 2, 1, 14, tzinfo=UTC)
    approved = context.client.post(f"/api/v1/studio/content/{item_id}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "scheduled"
    with context.session_factory() as session:
        job = session.scalar(
            select(BackgroundJobModel).where(
                BackgroundJobModel.dedup_key
                == f"content-publish:{item_id}:{approved.json()['current_version']}"
            )
        )
        assert job is not None
        assert job.run_at.replace(tzinfo=UTC) == datetime(2030, 2, 1, 14, tzinfo=UTC)
    assert (
        context.client.post(
            f"/api/v1/studio/content/{item_id}/publish", headers=headers
        ).status_code
        == 200
    )


def test_content_studio_versions_approval_and_demo_publish(authenticated) -> None:
    context, headers = authenticated
    brand = context.client.put(
        "/api/v1/studio/brand",
        headers=headers,
        json={
            "tone": "friendly",
            "audience": "طلاب وموظفون",
            "guidelines": "لغة عربية واضحة دون مبالغة",
            "primary_color": "#12B981",
        },
    )
    assert brand.status_code == 200, brand.text
    generated = context.client.post(
        "/api/v1/studio/content/generate",
        headers=headers,
        json={
            "product_id": "A101",
            "content_format": "reel_script",
            "platform": "instagram",
            "tone": "",
        },
    )
    assert generated.status_code == 201, generated.text
    item = generated.json()
    assert item["tone"] == "friendly"
    assert item["current_version"] == 1
    regenerated = context.client.post(
        f"/api/v1/studio/content/{item['id']}/regenerate",
        headers=headers,
        json={"section": "cta"},
    )
    assert regenerated.status_code == 200, regenerated.text
    assert regenerated.json()["current_version"] == 2
    versions = context.client.get(f"/api/v1/studio/content/{item['id']}/versions", headers=headers)
    assert [entry["version"] for entry in versions.json()] == [2, 1]

    blocked = context.client.post(f"/api/v1/studio/content/{item['id']}/publish", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "content_not_approved"

    approved = context.client.post(f"/api/v1/studio/content/{item['id']}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_by"] == "merchant@example.com"
    assert approved.json()["approved_at"]

    invalidated = context.client.patch(
        f"/api/v1/studio/content/{item['id']}",
        headers=headers,
        json={"caption": "Reviewed merchant caption"},
    )
    assert invalidated.status_code == 200, invalidated.text
    assert invalidated.json()["status"] == "draft"
    assert invalidated.json()["approved_by"] is None
    assert invalidated.json()["approved_at"] is None
    assert (
        context.client.post(
            f"/api/v1/studio/content/{item['id']}/publish", headers=headers
        ).status_code
        == 409
    )

    reapproved = context.client.post(
        f"/api/v1/studio/content/{item['id']}/approve", headers=headers
    )
    assert reapproved.status_code == 200, reapproved.text

    with context.session_factory() as session:
        row = session.get(ContentItemModel, item["id"])
        assert row is not None
        row.caption = "Unapproved database mutation"
        session.flush()
        with pytest.raises(ContentNotApprovedError):
            publish_content_job(
                session,
                {
                    "content_item_id": row.id,
                    "content_version": row.current_version,
                    "approval_hash": row.approved_content_hash,
                },
            )
        session.rollback()

    queued = context.client.post(f"/api/v1/studio/content/{item['id']}/publish", headers=headers)
    assert queued.status_code == 200, queued.text
    assert context.container.job_queue.run_due_jobs() >= 1
    published = context.client.get("/api/v1/studio/content", headers=headers)
    actual = next(row for row in published.json() if row["id"] == item["id"])
    assert actual["status"] == "published"
    assert actual["external_id"].startswith("demo-instagram-")


def test_unfinished_publish_attempt_requires_manual_reconciliation(authenticated) -> None:
    context, headers = authenticated
    generated = context.client.post(
        "/api/v1/studio/content/generate",
        headers=headers,
        json={
            "product_id": "A101",
            "content_format": "sales_post",
            "platform": "facebook",
            "tone": "friendly",
        },
    )
    assert generated.status_code == 201, generated.text
    item = generated.json()
    approved = context.client.post(f"/api/v1/studio/content/{item['id']}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    version = int(approved.json()["current_version"])

    with context.session_factory() as session:
        attempt = begin_external_operation(
            session,
            store_id=context.container.settings.demo_store_id,
            operation_key=f"content-item:{item['id']}:{version}",
            operation_type="content.publish",
            entity_type="content_item",
            entity_id=str(item["id"]),
        )
        assert attempt.should_execute is True

    queued = context.client.post(f"/api/v1/studio/content/{item['id']}/publish", headers=headers)
    assert queued.status_code == 200, queued.text
    assert context.container.job_queue.run_due_jobs() >= 1

    rows = context.client.get("/api/v1/studio/content", headers=headers).json()
    actual = next(row for row in rows if row["id"] == item["id"])
    assert actual["status"] == "publish_unknown"
    assert actual["external_id"] is None

    with context.session_factory() as session:
        audits = session.scalars(
            select(AuditEventModel).where(
                AuditEventModel.action == "content_item.publish_unknown",
                AuditEventModel.entity_id == str(item["id"]),
            )
        ).all()
    assert len(audits) == 1
    assert audits[0].metadata_json["attempt_id"] == attempt.attempt_id


def test_worker_crash_after_publish_call_stops_before_a_second_provider_call(
    authenticated, monkeypatch
) -> None:
    context, headers = authenticated
    generated = context.client.post(
        "/api/v1/studio/content/generate",
        headers=headers,
        json={
            "product_id": "A101",
            "content_format": "sales_post",
            "platform": "facebook",
            "tone": "friendly",
        },
    )
    assert generated.status_code == 201, generated.text
    item = generated.json()
    approved = context.client.post(f"/api/v1/studio/content/{item['id']}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    provider_calls: list[str] = []

    class CrashingPublisher:
        def publish(self, image_url: str, message: str):
            del image_url, message
            provider_calls.append("publish")
            raise RuntimeError("worker disappeared after an ambiguous provider call")

    monkeypatch.setattr("app.services.content_studio._FACEBOOK", CrashingPublisher())
    queued = context.client.post(f"/api/v1/studio/content/{item['id']}/publish", headers=headers)
    assert queued.status_code == 200, queued.text
    assert context.container.job_queue.run_due_jobs() >= 1
    assert provider_calls == ["publish"]

    with context.session_factory.begin() as session:
        job = session.scalar(
            select(BackgroundJobModel).where(
                BackgroundJobModel.dedup_key
                == f"content-publish:{item['id']}:{approved.json()['current_version']}"
            )
        )
        assert job is not None
        assert job.status == "pending"
        job.run_at = datetime.now(UTC) - timedelta(seconds=1)

    assert context.container.job_queue.run_due_jobs() >= 1
    assert provider_calls == ["publish"]
    rows = context.client.get("/api/v1/studio/content", headers=headers).json()
    actual = next(row for row in rows if row["id"] == item["id"])
    assert actual["status"] == "publish_unknown"


def test_campaign_generator_creates_grounded_content(authenticated) -> None:
    context, headers = authenticated
    response = context.client.post(
        "/api/v1/studio/campaigns/generate",
        headers=headers,
        json={
            "name": "Back to study",
            "goal": "زيادة طلبات سماعات الدراسة",
            "budget": "3000.00",
            "product_ids": ["A101", "A103"],
            "audience": "طلاب الجامعات",
            "offer": "مساعدة مجانية في الاختيار",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["budget"] == "3000.00"
    assert body["product_ids"] == ["A101", "A103"]
    content = context.client.get("/api/v1/studio/content", headers=headers).json()
    assert sum(item["campaign_id"] == body["id"] for item in content) == 2
