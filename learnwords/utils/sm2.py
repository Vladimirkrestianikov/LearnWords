import datetime
from dataclasses import dataclass
from typing import Tuple
from learnwords.database.models import WordProgressStatus


@dataclass
class SM2Result:
    repetitions: int
    ease_factor: float
    interval_days: float
    next_review_at: datetime.datetime
    status: str


def calculate_sm2(
    repetitions: int,
    ease_factor: float,
    interval_days: float,
    quality: int,  # 0 to 5
    now: datetime.datetime = None,
) -> SM2Result:
    """
    Computes updated SuperMemo SM-2 parameters for a flashcard review.
    
    quality scale:
    5 - perfect response
    4 - correct response with some hesitation
    3 - correct response with serious difficulty
    2 - incorrect response; correct one remembered
    1 - incorrect response; correct one seemed familiar
    0 - complete blackout
    """
    if now is None:
        now = datetime.datetime.now()

    # Minimum ease factor bound in SM-2 is 1.3
    if ease_factor < 1.3:
        ease_factor = 1.3

    # Calculate new ease factor: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, round(new_ef, 2))

    if quality >= 3:
        # Correct response
        if repetitions == 0:
            new_repetitions = 1
            # 1st successful repetition: ~10 minutes (0.007 days)
            new_interval_days = 0.007
        elif repetitions == 1:
            new_repetitions = 2
            # 2nd successful repetition: 1 day
            new_interval_days = 1.0
        elif repetitions == 2:
            new_repetitions = 3
            # 3rd successful repetition: 3 days
            new_interval_days = 3.0
        elif repetitions == 3:
            new_repetitions = 4
            # 4th successful repetition: 7 days
            new_interval_days = 7.0
        elif repetitions == 4:
            new_repetitions = 5
            # 5th successful repetition: 14 days
            new_interval_days = 14.0
        else:
            new_repetitions = repetitions + 1
            # Subsequent: interval * new_ef
            new_interval_days = round(interval_days * new_ef, 1)
            if new_interval_days < 14.0:
                new_interval_days = 30.0

        delta = datetime.timedelta(days=new_interval_days)
        next_review = now + delta

        if new_repetitions >= 5 and new_ef >= 2.0:
            status = WordProgressStatus.MASTERED
        elif new_repetitions >= 3:
            status = WordProgressStatus.FAMILIAR
        else:
            status = WordProgressStatus.LEARNING

    else:
        # Incorrect response: reset to learning/difficult
        new_repetitions = 0
        new_interval_days = 0.007  # Re-review in 10 minutes
        next_review = now + datetime.timedelta(minutes=10)
        status = WordProgressStatus.DIFFICULT if quality <= 1 else WordProgressStatus.NEEDS_REVIEW

    return SM2Result(
        repetitions=new_repetitions,
        ease_factor=new_ef,
        interval_days=new_interval_days,
        next_review_at=next_review,
        status=status,
    )

