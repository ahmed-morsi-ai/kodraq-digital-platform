from decimal import Decimal, ROUND_HALF_UP

from app.models.quiz import Quiz
from app.schemas.quiz_attempt import QuizAnswerCreate


def validate_quiz(quiz: Quiz) -> None:
    if not quiz.question_links:
        raise ValueError("This quiz has no questions yet.")
    for link in quiz.question_links:
        question = link.question
        if question.question_type not in {"MULTIPLE_CHOICE", "TRUE_FALSE"}:
            raise ValueError("This quiz contains an unsupported question type.")
        if (
            len(question.options) < 2
            or sum(option.is_correct for option in question.options) != 1
        ):
            raise ValueError(
                "Each question needs options and exactly one correct answer."
            )
        if question.points <= 0:
            raise ValueError("Question points must be positive.")


def grade_quiz(
    quiz: Quiz, answers: list[QuizAnswerCreate], *, passing_score: int, flagged: bool
) -> dict:
    """Score exclusively from server-owned options and weights, including omissions."""
    validate_quiz(quiz)
    provided = {answer.question_id: answer for answer in answers}
    if len(provided) != len(answers):
        raise ValueError("Each quiz question may only be answered once")
    questions = {link.question_id: link.question for link in quiz.question_links}
    if provided.keys() - questions.keys():
        raise ValueError("An answer references a question outside this quiz")
    rows, results = [], []
    earned = 0
    maximum = sum(question.points for question in questions.values())
    for link in quiz.question_links:
        question = link.question
        answer = provided.get(question.id)
        option_id = answer.selected_option_id if answer else None
        selected = next(
            (option for option in question.options if option.id == option_id), None
        )
        if option_id is not None and selected is None:
            raise ValueError("Selected option does not belong to the answered question")
        correct = bool(selected and selected.is_correct)
        if correct:
            earned += question.points
        correct_options = [option for option in question.options if option.is_correct]
        rows.append(
            {
                "question_id": question.id,
                "selected_option_id": option_id,
                "is_correct": correct,
            }
        )
        results.append(
            {
                "question_id": question.id,
                "question_text": question.text,
                "points": question.points,
                "selected_option_id": option_id,
                "selected_option_text": selected.text if selected else None,
                "correct_option_ids": [option.id for option in correct_options],
                "correct_option_texts": [option.text for option in correct_options],
                "is_correct": correct,
            }
        )
    earned = 0 if flagged else earned
    percentage = float(
        (Decimal(earned) * 100 / Decimal(maximum)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )
    return {
        "rows": rows,
        "questions": results,
        "max_score": maximum,
        "earned_points": earned,
        "score": percentage,
        "percentage": percentage,
        "passed": earned * 100 >= passing_score * maximum and not flagged,
    }
