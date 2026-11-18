import datetime
import pytest
from learnwords.utils.sm2 import calculate_sm2
from learnwords.database.models import WordProgressStatus


def test_sm2_perfect_progression():
    base_time = datetime.datetime(2026, 1, 1, 12, 0, 0)

    # 1st review (q=5)
    r1 = calculate_sm2(repetitions=0, ease_factor=2.5, interval_days=0.0, quality=5, now=base_time)
    assert r1.repetitions == 1
    assert r1.status == WordProgressStatus.LEARNING
    assert r1.interval_days == 0.007
    assert r1.ease_factor == 2.6

    # 2nd review (q=4)
    r2 = calculate_sm2(repetitions=r1.repetitions, ease_factor=r1.ease_factor, interval_days=r1.interval_days, quality=4, now=base_time)
    assert r2.repetitions == 2
    assert r2.interval_days == 1.0
    assert r2.status == WordProgressStatus.LEARNING

    # 3rd review (q=4)
    r3 = calculate_sm2(repetitions=r2.repetitions, ease_factor=r2.ease_factor, interval_days=r2.interval_days, quality=4, now=base_time)
    assert r3.repetitions == 3
    assert r3.interval_days == 3.0
    assert r3.status == WordProgressStatus.FAMILIAR

    # 4th review (q=4)
    r4 = calculate_sm2(repetitions=r3.repetitions, ease_factor=r3.ease_factor, interval_days=r3.interval_days, quality=4, now=base_time)
    assert r4.repetitions == 4
    assert r4.interval_days == 7.0

    # 5th review (q=4)
    r5 = calculate_sm2(repetitions=r4.repetitions, ease_factor=r4.ease_factor, interval_days=r4.interval_days, quality=4, now=base_time)
    assert r5.repetitions == 5
    assert r5.interval_days == 14.0
    assert r5.status == WordProgressStatus.MASTERED


def test_sm2_failure_reset():
    base_time = datetime.datetime(2026, 1, 1, 12, 0, 0)

    # Start from mature card (rep=4, interval=7.0)
    failed = calculate_sm2(repetitions=4, ease_factor=2.5, interval_days=7.0, quality=1, now=base_time)
    assert failed.repetitions == 0
    assert failed.interval_days == 0.007
    assert failed.status == WordProgressStatus.DIFFICULT
    assert failed.ease_factor < 2.5
    # Scheduled for 10 minutes from now
    assert failed.next_review_at == base_time + datetime.timedelta(minutes=10)

