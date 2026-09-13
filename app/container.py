"""Composition root: concrete adapters are selected in one place."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.domain.enums import ChannelType
from app.integrations.ai_provider import AIProvider, build_ai_provider
from app.integrations.billing import (
    BillingProvider,
    DemoBillingProvider,
    DisabledBillingProvider,
    StripeBillingProvider,
)
from app.integrations.channels import register_live_adapter
from app.integrations.email import EmailSender, build_email_sender
from app.integrations.facebook import (
    DisabledFacebookPublisher,
    FacebookPublisher,
    FakeFacebookPublisher,
)
from app.integrations.image_storage import ImageStorage, build_image_storage
from app.integrations.instagram import (
    DisabledInstagramPublisher,
    FakeInstagramPublisher,
    InstagramPublisher,
)
from app.integrations.malware_scanner import MalwareScanner, build_malware_scanner
from app.integrations.meta_channels import MetaChannelAdapter
from app.integrations.payments import (
    CodPaymentProvider,
    DemoPaymentProvider,
    DisabledPaymentProvider,
    PaymentProvider,
    StripePaymentProvider,
)
from app.integrations.sql_search_store import SQLSearchStore
from app.integrations.stripe_api import StripeApi
from app.integrations.whatsapp import WhatsAppCloudAdapter
from app.services.commerce_connectors import configure_commerce_services
from app.services.content_studio import (
    configure_content_publishers,
    configure_content_services,
)
from app.services.credential_vault import configure_credential_vault
from app.services.job_queue import JobQueue
from app.services.search_index import SearchStore


@dataclass(frozen=True)
class AppContainer:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    ai_provider: AIProvider
    vector_store: SearchStore
    image_storage: ImageStorage
    facebook_publisher: FacebookPublisher
    instagram_publisher: InstagramPublisher
    job_queue: JobQueue
    payment_provider: PaymentProvider
    billing_provider: BillingProvider
    email_sender: EmailSender
    malware_scanner: MalwareScanner


def _publishers(settings: Settings) -> tuple[FacebookPublisher, InstagramPublisher]:
    if settings.demo_mode and settings.enable_fake_publishing:
        return FakeFacebookPublisher(), FakeInstagramPublisher()
    return DisabledFacebookPublisher(), DisabledInstagramPublisher()


def _payment_provider(settings: Settings) -> PaymentProvider:
    if settings.demo_mode and settings.payment_provider == "demo":
        return DemoPaymentProvider()
    if settings.payment_provider == "cod":
        return CodPaymentProvider()
    if settings.payment_provider == "stripe":
        return StripePaymentProvider(
            StripeApi(
                settings.stripe_secret_key.get_secret_value(),
                settings.stripe_payment_webhook_secret.get_secret_value(),
                timeout_seconds=settings.stripe_request_timeout_seconds,
            )
        )
    return DisabledPaymentProvider()


def _billing_provider(settings: Settings) -> BillingProvider:
    if settings.demo_mode and settings.billing_provider == "demo":
        return DemoBillingProvider()
    if settings.billing_provider == "stripe":
        return StripeBillingProvider(
            StripeApi(
                settings.stripe_secret_key.get_secret_value(),
                settings.stripe_webhook_secret.get_secret_value(),
                timeout_seconds=settings.stripe_request_timeout_seconds,
            ),
            {
                "starter": settings.stripe_price_starter,
                "growth": settings.stripe_price_growth,
                "pro": settings.stripe_price_pro,
            },
        )
    return DisabledBillingProvider()


def build_container(
    settings: Settings, engine: Engine, session_factory: sessionmaker[Session]
) -> AppContainer:
    facebook, instagram = _publishers(settings)
    configure_content_publishers(facebook, instagram)
    ai_provider = build_ai_provider(settings, Path(__file__).parent / "prompts")
    configure_content_services(
        ai_provider,
        settings.ai_provider,
        settings.openai_model,
        settings,
    )
    configure_commerce_services(settings)
    app_key = settings.effective_secret_key
    integration_key = settings.integration_encryption_key.get_secret_value() or app_key
    configure_credential_vault(
        integration_key,
        key_version=settings.integration_encryption_key_version,
        previous_keys=settings.integration_keyring,
        legacy_keys=(app_key,),
    )
    register_live_adapter(
        ChannelType.WHATSAPP,
        WhatsAppCloudAdapter(
            settings.meta_graph_api_base,
            settings.meta_graph_api_version,
            settings.meta_request_timeout_seconds,
        ),
    )
    for channel_type in (
        ChannelType.MESSENGER,
        ChannelType.INSTAGRAM_DM,
        ChannelType.FACEBOOK_COMMENTS,
        ChannelType.INSTAGRAM_COMMENTS,
    ):
        register_live_adapter(
            channel_type,
            MetaChannelAdapter(
                channel_type,
                settings.meta_graph_api_base,
                settings.meta_graph_api_version,
                settings.meta_request_timeout_seconds,
            ),
        )
    vector_store: SearchStore
    if settings.search_provider == "chroma":
        from app.integrations.chroma_store import ChromaStore

        vector_store = ChromaStore(settings.chroma_directory)
    else:
        vector_store = SQLSearchStore(session_factory)
    return AppContainer(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        ai_provider=ai_provider,
        vector_store=vector_store,
        image_storage=build_image_storage(settings, session_factory),
        facebook_publisher=facebook,
        instagram_publisher=instagram,
        job_queue=JobQueue(
            session_factory,
            lease_seconds=settings.worker_lease_seconds,
        ),
        payment_provider=_payment_provider(settings),
        billing_provider=_billing_provider(settings),
        email_sender=build_email_sender(settings),
        malware_scanner=build_malware_scanner(settings),
    )
