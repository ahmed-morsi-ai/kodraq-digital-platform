from app.models.quiz import Question, QuestionOption
from app.models.track import Track


def _create_track(db_session):
    track = Track(
        name="Question Model Track",
        slug="question-model-track",
        description="Question model test track",
    )
    db_session.add(track)
    db_session.flush()
    return track


def test_question_creation_links_to_track(db_session):
    track = _create_track(db_session)
    question = Question(
        track_id=track.id,
        text="What is Python?",
        question_type="MULTIPLE_CHOICE",
        difficulty=3,
    )

    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    assert question.id is not None
    assert question.track_id == track.id
    assert question.track.id == track.id
    assert question.question_type == "MULTIPLE_CHOICE"
    assert question.difficulty == 3


def test_question_options_link_to_question(db_session):
    track = _create_track(db_session)
    question = Question(
        track=track,
        text="Is Python interpreted?",
        question_type="TRUE_FALSE",
    )
    question.options = [
        QuestionOption(text="True", is_correct=True),
        QuestionOption(text="False", is_correct=False),
    ]

    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)

    assert len(question.options) == 2
    assert all(option.question_id == question.id for option in question.options)
    assert question.options[0].is_correct is True
    assert question.options[1].is_correct is False
    assert question.difficulty == 1


def test_deleting_question_cascades_to_options(db_session):
    track = _create_track(db_session)
    question = Question(
        track=track,
        text="Which option is correct?",
        question_type="MULTIPLE_CHOICE",
        options=[
            QuestionOption(text="Correct", is_correct=True),
            QuestionOption(text="Incorrect", is_correct=False),
        ],
    )
    db_session.add(question)
    db_session.commit()
    option_ids = [option.id for option in question.options]

    db_session.delete(question)
    db_session.commit()

    assert db_session.get(Question, question.id) is None
    assert all(
        db_session.get(QuestionOption, option_id) is None
        for option_id in option_ids
    )
