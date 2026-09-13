"""Store, assistant, and onboarding settings."""

from fastapi import APIRouter

from app.api.dependencies import AdminUser, CurrentUser, DatabaseDependency
from app.domain.models import OnboardingStatusOut, StoreSettingsInput, StoreSettingsOut
from app.services.store_settings import (
    activate_store,
    get_store_settings,
    onboarding_status,
    save_store_settings,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/store", response_model=StoreSettingsOut)
def store_settings(user: CurrentUser, db: DatabaseDependency) -> StoreSettingsOut:
    return get_store_settings(db, user.store_id)


@router.put("/store", response_model=StoreSettingsOut)
def update_store_settings(
    payload: StoreSettingsInput,
    user: AdminUser,
    db: DatabaseDependency,
) -> StoreSettingsOut:
    return save_store_settings(db, user.store_id, payload)


@router.get("/onboarding", response_model=OnboardingStatusOut)
def get_onboarding_status(
    user: CurrentUser, db: DatabaseDependency
) -> OnboardingStatusOut:
    return onboarding_status(db, user)


@router.post("/onboarding/activate", response_model=OnboardingStatusOut)
def activate_onboarding(
    user: AdminUser, db: DatabaseDependency
) -> OnboardingStatusOut:
    return activate_store(db, user)
