import pytest
from learnwords.database.models import UserRole, UserStatus
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.settings_repo import SettingsRepository


@pytest.mark.asyncio
async def test_user_registration_and_roles(test_session):
    repo = UserRepository(test_session)

    # 1. Register student
    user, created = await repo.create_or_get_user(
        telegram_id=123456,
        username="teststudent",
        full_name="Test Student",
        is_admin=False
    )
    assert created is True
    assert user.telegram_id == 123456
    assert user.role == UserRole.STUDENT
    assert user.status == UserStatus.ACTIVE
    assert user.settings is not None
    assert user.settings.english_level == "B1"

    # 2. Existing user check
    same_user, created_again = await repo.create_or_get_user(
        telegram_id=123456,
        username="updated_name"
    )
    assert created_again is False
    assert same_user.id == user.id
    assert same_user.username == "updated_name"

    # 3. Register admin
    admin_user, admin_created = await repo.create_or_get_user(
        telegram_id=999999,
        username="admin_user",
        is_admin=True
    )
    assert admin_created is True
    assert admin_user.role == UserRole.ADMIN

    # 4. Update role and status
    await repo.update_role(user.id, UserRole.ADMIN)
    updated_user = await repo.get_by_id(user.id)
    assert updated_user.role == UserRole.ADMIN

    await repo.update_status(user.id, UserStatus.BANNED)
    banned_user = await repo.get_by_id(user.id)
    assert banned_user.status == UserStatus.BANNED


@pytest.mark.asyncio
async def test_user_settings_update(test_session):
    user_repo = UserRepository(test_session)
    settings_repo = SettingsRepository(test_session)

    user, _ = await user_repo.create_or_get_user(
        telegram_id=777777,
        username="settings_user"
    )

    # Update settings
    updated = await settings_repo.update_settings(
        user_id=user.id,
        english_level="C1",
        preferred_topics=["Technology", "Business"],
        daily_word_goal=20,
        difficulty="INTENSIVE"
    )

    assert updated.english_level == "C1"
    assert updated.daily_word_goal == 20
    assert updated.difficulty == "INTENSIVE"
    topics = settings_repo.parse_topics(updated)
    assert topics == ["Technology", "Business"]

