"""Idempotent demo store, catalog, policy, and search-index seed."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.models import (
    BackgroundJobModel,
    ConversationModel,
    MembershipModel,
    OrganizationModel,
    PolicyModel,
    ProductModel,
    StoreModel,
    UserModel,
)
from app.db.session import create_database_engine, create_session_factory
from app.domain.enums import ChannelType, MemberRole, MessageSenderType, ProductStatus
from app.domain.models import PolicyExcerpt, ProductRecord
from app.integrations.sql_search_store import SQLSearchStore
from app.repositories.product_repository import ProductRepository
from app.services.conversations import (
    add_internal_note,
    ingest_inbound_message,
    queue_outbound_message,
)
from app.services.search_index import SearchStore

SEED_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "seeds"
DEMO_ORGANIZATION_ID = "org_demo"
DEMO_USER_ID = "usr_demo_merchant"


def _ensure_demo_tenant(session: Session, settings: Settings) -> None:
    organization = session.get(OrganizationModel, DEMO_ORGANIZATION_ID)
    if organization is None:
        session.add(
            OrganizationModel(
                id=DEMO_ORGANIZATION_ID, name="Commerce AI Demo Organization", plan="growth"
            )
        )
    user = session.get(UserModel, DEMO_USER_ID)
    password_hash = settings.demo_merchant_password_hash.get_secret_value()
    if user is None:
        session.add(
            UserModel(
                id=DEMO_USER_ID,
                email=settings.demo_merchant_email.casefold(),
                password_hash=password_hash,
                full_name="Demo Merchant",
                email_verified_at=datetime.now(UTC),
            )
        )
    elif password_hash and user.password_hash != password_hash:
        user.password_hash = password_hash
    if user is not None and user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
    session.flush()
    membership = session.scalar(
        select(MembershipModel).where(
            MembershipModel.organization_id == DEMO_ORGANIZATION_ID,
            MembershipModel.user_id == DEMO_USER_ID,
        )
    )
    if membership is None:
        session.add(
            MembershipModel(
                organization_id=DEMO_ORGANIZATION_ID,
                user_id=DEMO_USER_ID,
                role=MemberRole.OWNER.value,
            )
        )
    session.flush()


def _load_json(name: str) -> list[dict[str, Any]]:
    payload = json.loads((SEED_DIRECTORY / name).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Seed file {name} must contain a JSON array")
    return [dict(item) for item in payload]


DEMO_CONVERSATIONS: list[dict[str, Any]] = [
    {
        "external_id": "web-demo-mona",
        "name": "منى عادل",
        "channel": ChannelType.WEBCHAT,
        "inbound": (
            "السلام عليكم، عايزة سماعة للمذاكرة والمكالمات وميزانيتي 1500 جنيه. في حاجة كويسة؟"
        ),
        "reply": (
            "أهلًا بيكِ! عندنا Study Wireless Headphones بسعر 1299 جنيه — "
            "عزل ضوضاء ممتاز وميكروفون واضح للمكالمات، ومتوفرة حاليًا. "
            "تحبي أجهزلك أوردر؟"
        ),
        "note": "عميلة مهتمة فعلًا — متابعة لو ما ردتش خلال يوم.",
    },
    {
        "external_id": "web-demo-karim",
        "name": "كريم مصطفى",
        "channel": ChannelType.WEBCHAT,
        "inbound": "ما هي سياسة الاسترجاع عندكم؟ ولو المنتج وصل تالف بعمل إيه؟",
        "reply": None,
        "note": None,
    },
    {
        "external_id": "web-demo-sara",
        "name": "سارة حسن",
        "channel": ChannelType.WEBCHAT,
        "inbound": "شاحن السيارة اللي شفته عندكم خلص من المخزن؟ في بديل بنفس السعر تقريبًا؟",
        "reply": None,
        "note": None,
    },
]


def _seed_demo_conversations(session: Session, settings: Settings) -> int:
    """Idempotent realistic Arabic conversations on the demo webchat channel."""

    existing = session.scalar(
        select(ConversationModel.id).where(ConversationModel.store_id == settings.demo_store_id)
    )
    if existing is not None:
        return 0
    created = 0
    for item in DEMO_CONVERSATIONS:
        conversation, _ = ingest_inbound_message(
            session,
            store_id=settings.demo_store_id,
            channel_type=item["channel"],
            external_user_id=str(item["external_id"]),
            text=str(item["inbound"]),
            display_name=str(item["name"]),
        )
        if item["reply"]:
            message = queue_outbound_message(
                session,
                store_id=settings.demo_store_id,
                conversation=conversation,
                text=str(item["reply"]),
                sender_type=MessageSenderType.AGENT,
                sender_user_id=DEMO_USER_ID,
            )
            # Demo channel delivery is local; mark it sent without waiting for a worker.
            message.status = "sent"
            message.external_id = f"demo-seed-{conversation.id}"
            queued = session.scalar(
                select(BackgroundJobModel).where(
                    BackgroundJobModel.dedup_key == f"send-message-{message.id}"
                )
            )
            if queued is not None:
                queued.status = "succeeded"
                queued.finished_at = datetime.now(UTC)
        if item["note"]:
            add_internal_note(
                session,
                conversation=conversation,
                text=str(item["note"]),
                sender_user_id=DEMO_USER_ID,
            )
        created += 1
    session.flush()
    return created


def seed_database(
    settings: Settings,
    factory: sessionmaker[Session],
    vector_store: SearchStore,
) -> dict[str, int]:
    if settings.app_env == "production" or not settings.demo_mode:
        raise RuntimeError("Demo seed is disabled unless DEMO_MODE=true outside production")
    created_products = 0
    created_policies = 0
    with factory.begin() as session:
        _ensure_demo_tenant(session, settings)
        store = session.get(StoreModel, settings.demo_store_id)
        if store is None:
            session.add(
                StoreModel(
                    id=settings.demo_store_id,
                    organization_id=DEMO_ORGANIZATION_ID,
                    slug="demo-store",
                    name="Commerce AI Demo Store",
                    default_language="ar",
                )
            )
            session.flush()
        elif store.organization_id is None:
            store.organization_id = DEMO_ORGANIZATION_ID
            session.flush()
        products = ProductRepository(session)
        now = datetime.now(UTC)
        for item in _load_json("products.json"):
            product_id = str(item["product_id"])
            existing = session.scalar(
                select(ProductModel.id).where(
                    ProductModel.store_id == settings.demo_store_id,
                    ProductModel.product_id == product_id,
                )
            )
            if existing is None:
                image_url = f"/placeholders/{item['image']}"
                products.add(
                    ProductRecord(
                        product_id=product_id,
                        store_id=settings.demo_store_id,
                        name=str(item["name"]),
                        category=str(item["category"]),
                        price=Decimal(str(item["price"])),
                        stock=int(item["stock"]),
                        features=[str(value) for value in item["features"]],
                        customer_benefits=[str(value) for value in item["benefits"]],
                        description=str(item["description"]),
                        image_summary=f"Demo placeholder for {item['name']}",
                        original_image_url=image_url,
                        public_image_url=None,
                        status=ProductStatus.ACTIVE,
                        created_at=now,
                        updated_at=now,
                    )
                )
                created_products += 1
        for item in _load_json("policies.json"):
            source_ref = str(item["source_ref"])
            existing_policy = session.scalar(
                select(PolicyModel.id).where(
                    PolicyModel.store_id == settings.demo_store_id,
                    PolicyModel.source_ref == source_ref,
                )
            )
            if existing_policy is None:
                session.add(
                    PolicyModel(
                        store_id=settings.demo_store_id,
                        policy_type=str(item["policy_type"]),
                        title=str(item["title"]),
                        body=str(item["body"]),
                        source_ref=source_ref,
                    )
                )
                created_policies += 1
        session.flush()
        created_conversations = _seed_demo_conversations(session, settings)
        all_products = products.list(settings.demo_store_id)
        all_policies = list(
            session.scalars(
                select(PolicyModel).where(PolicyModel.store_id == settings.demo_store_id)
            )
        )

    for product in all_products:
        vector_store.upsert_product(product)
    for policy in all_policies:
        vector_store.upsert_policy(
            settings.demo_store_id,
            PolicyExcerpt(
                source_ref=policy.source_ref,
                title=policy.title,
                body=policy.body,
                score=1.0,
            ),
        )
    return {
        "products_created": created_products,
        "policies_created": created_policies,
        "conversations_created": created_conversations,
    }


def main() -> None:
    settings = get_settings()
    engine = create_database_engine(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle_seconds,
    )
    factory = create_session_factory(engine)
    vector_store: SearchStore
    if settings.search_provider == "chroma":
        from app.integrations.chroma_store import ChromaStore

        vector_store = ChromaStore(settings.chroma_directory)
    else:
        vector_store = SQLSearchStore(factory)
    result = seed_database(
        settings,
        factory,
        vector_store,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
