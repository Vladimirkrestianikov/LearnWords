import pytest
from learnwords.database.models import UserRole, UserStatus
from learnwords.database.repositories.user_repo import UserRepository
from learnwords.database.repositories.admin_repo import AdminRepository
from learnwords.database.repositories.word_repo import WordRepository


@pytest.mark.asyncio
async def test_admin_repository_and_actions(test_session):
    user_repo = UserRepository(test_session)
    admin, _ = await user_repo.create_or_get_user(telegram_id=11111, is_admin=True)
    student, _ = await user_repo.create_or_get_user(telegram_id=22222, is_admin=False)

    admin_repo = AdminRepository(test_session)
    word_repo = WordRepository(test_session)
    await word_repo.get_or_create_word("Apple", "Яблоко")

    # 1. Global stats check
    stats = await admin_repo.get_global_stats()
    assert stats["total_users"] == 2
    assert stats["total_words"] == 1
    assert stats["banned_users"] == 0

    # 2. Ban student
    await user_repo.update_status(student.id, UserStatus.BANNED)
    stats_after_ban = await admin_repo.get_global_stats()
    assert stats_after_ban["banned_users"] == 1

    # 3. Promote / demote
    await user_repo.update_role(student.id, UserRole.ADMIN)
    promoted = await user_repo.get_by_id(student.id)
    assert promoted.role == UserRole.ADMIN

    # 4. System settings
    await admin_repo.set_system_setting("OPENAI_MODEL", "gpt-4o", "Target Model")
    val = await admin_repo.get_system_setting("OPENAI_MODEL")
    assert val == "gpt-4o"

    # 5. Activity log
    await admin_repo.log_activity(admin.id, "TEST_ACTION", "Testing logs")
    logs = await admin_repo.get_recent_logs(limit=5)
    assert len(logs) >= 1
    assert logs[0].action == "TEST_ACTION"

