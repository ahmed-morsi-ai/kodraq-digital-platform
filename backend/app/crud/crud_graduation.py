from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.graduation import GraduationEvaluation, GraduationGateCheck
from app.schemas.graduation import GraduationEvaluationResponse
from app.services.graduation import calculate_graduation


class CRUDGraduationEvaluation(
    CRUDBase[
        GraduationEvaluation,
        GraduationEvaluationResponse,
        GraduationEvaluationResponse,
    ]
):
    def _get_with_gates(
        self,
        db: Session,
        *,
        evaluation_id: int,
    ) -> GraduationEvaluation | None:
        stmt = (
            select(GraduationEvaluation)
            .options(selectinload(GraduationEvaluation.gate_checks))
            .where(GraduationEvaluation.id == evaluation_id)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get(
        self,
        db: Session,
        id: int,
    ) -> GraduationEvaluation | None:
        return self._get_with_gates(db, evaluation_id=id)

    def get_by_user_track(
        self,
        db: Session,
        *,
        user_id: int,
        track_id: int,
    ) -> GraduationEvaluation | None:
        stmt = (
            select(GraduationEvaluation)
            .options(selectinload(GraduationEvaluation.gate_checks))
            .where(
                GraduationEvaluation.user_id == user_id,
                GraduationEvaluation.track_id == track_id,
            )
            .order_by(GraduationEvaluation.evaluated_at.desc())
        )
        return db.execute(stmt).scalars().first()

    def get_latest_for_user(
        self,
        db: Session,
        *,
        user_id: int,
    ) -> GraduationEvaluation | None:
        stmt = (
            select(GraduationEvaluation)
            .options(selectinload(GraduationEvaluation.gate_checks))
            .where(GraduationEvaluation.user_id == user_id)
            .order_by(
                GraduationEvaluation.evaluated_at.desc(),
                GraduationEvaluation.id.desc(),
            )
        )
        return db.execute(stmt).scalars().first()

    def evaluate(
        self,
        db: Session,
        *,
        user_id: int,
        track_id: int,
    ) -> GraduationEvaluation:
        calculation = calculate_graduation(
            db,
            user_id=user_id,
            track_id=track_id,
        )
        evaluation = self.get_by_user_track(
            db,
            user_id=user_id,
            track_id=track_id,
        )
        if evaluation is None:
            evaluation = GraduationEvaluation(
                user_id=user_id,
                track_id=track_id,
            )
            db.add(evaluation)
            db.flush()

        evaluation.overall_score = calculation.overall_score
        evaluation.is_eligible = calculation.is_eligible
        evaluation.status = calculation.status
        evaluation.evaluated_at = datetime.now(UTC)
        evaluation.gate_checks.clear()
        db.flush()
        evaluation.gate_checks.extend(
            [
            GraduationGateCheck(
                gate_key=gate.gate_key,
                passed=gate.passed,
                actual_value=gate.actual_value,
                required_value=gate.required_value,
                failure_reason=gate.failure_reason,
                details=gate.details,
            )
            for gate in calculation.gates
            ]
        )
        db.add(evaluation)
        db.commit()
        return self._get_with_gates(db, evaluation_id=evaluation.id)  # type: ignore[return-value]


graduation_evaluation = CRUDGraduationEvaluation(GraduationEvaluation)


def get_graduation_evaluation(
    db: Session,
    user_id: int,
    track_id: int,
) -> GraduationEvaluation | None:
    return graduation_evaluation.get_by_user_track(
        db,
        user_id=user_id,
        track_id=track_id,
    )


def get_latest_graduation_evaluation(
    db: Session,
    user_id: int,
) -> GraduationEvaluation | None:
    return graduation_evaluation.get_latest_for_user(db, user_id=user_id)


def evaluate_graduation(
    db: Session,
    user_id: int,
    track_id: int,
) -> GraduationEvaluation:
    return graduation_evaluation.evaluate(
        db,
        user_id=user_id,
        track_id=track_id,
    )
