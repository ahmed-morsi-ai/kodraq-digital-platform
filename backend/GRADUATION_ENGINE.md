# Graduation eligibility and finalization

The engine uses the existing backend thresholds because Master Roadmap v2 is not
present in the repository. The retained calculation weights curriculum completion,
mandatory-assignment approval rate, quiz average, and final-project score equally.
All mandatory gates must pass independently; rounding is applied only for display,
never before a pass/fail comparison.

| Gate | Requirement |
| --- | --- |
| Enrollment | Active student, active track, and active enrollment |
| Curriculum | Every track lesson has completed status and 100% progress |
| Assignments | Every active mandatory assignment has the student's approved submission |
| Quizzes | Every active quiz has a completed attempt meeting its own passing score; average of best completed scores is at least 70% |
| Final project | Active project, approved student submission, latest review approved by another user with numeric score at least max(75, project passing score) |
| Overall | Equal-weight average of the four academic components is at least 75% |

Track, module, and lesson assignment/quiz ownership are resolved consistently with
curriculum CRUD. Inconsistent legacy references fail the relevant gate. Work from
other students/tracks and unfinished quiz attempts earns no credit. Invalid legacy
quiz scores are ignored. A track with no lessons, mandatory assignments, or quizzes
has 100% for that empty component; a missing/inactive/unreviewed final project fails.
An anti-cheating quiz flag is not automatically an academic failure: no adjudicated
critical-failure domain exists. The previous unconditional critical-failure pass was
removed; configured unsupported mandatory rules fail closed.

`graduation_rules` supports stricter thresholds through recognized codes:
`ENROLLMENT`, `CURRICULUM_COMPLETION`, `MANDATORY_ASSIGNMENTS`, `QUIZ_AVERAGE`,
`FINAL_PROJECT`, `OVERALL_SCORE`, with `rule_type=THRESHOLD`. Lowered thresholds,
optional flags, or disabled rules cannot waive the mandatory floors. Unsupported
active mandatory rule codes/types block eligibility. Default rules are created
only during staff finalization; reading status does not write rules or results.
Rule administration APIs are outside this task.

## API

All paths have `/api/v1/graduation` prefix and require an active authenticated user.

- `GET /status?track_id=...&user_id=...`: current eligibility, each gate's actual and
  required values, missing work and reasons, plus the historical finalized result.
  Students omit user_id or specify themselves. Instructors require track assignment;
  admins have global access. A track ID is required; there is no unscoped latest-record fallback.
- `POST /evaluate/{user_id}?track_id=...`: staff-only preview, with no persistence.
- `POST /finalize/{user_id}?track_id=...`: assigned instructor/admin only. Recalculates
  from database evidence and atomically stores `graduation_results` and
  `graduation_checks`. Request body may be omitted or `{}`; score/status/identity
  overrides are rejected. Self-finalization is forbidden.
- `GET /results?track_id=...&skip=0&limit=100`: staff-only scoped, stable result list.
- `GET /results/{id}`: stored result and checks, owner or assigned manager only.

Live status is `NOT_GRADUATED` if any gate fails, `ELIGIBLE` if all gates pass while
awaiting finalization, and `GRADUATED` only after verified staff finalization.
A failed finalization attempt stores `NOT_GRADUATED`, with no finalizer/time; it can
be re-evaluated after rework. A passed snapshot records the actor, time, precise
score, thresholds, and every check. Repeat finalization is idempotent and serialized
by a track row lock. If requirements later change, live eligibility reflects them;
a previously passed snapshot remains historical. Re-finalizing while current gates
fail returns 409, never a new successful decision. Source assessment edits are not
locked globally; the result is evidence captured during evaluation, not a promise
that curriculum will never change.

Existing certificate endpoints now require the same instructor track isolation and
a verified finalized result with all required checks. A fabricated/legacy bare
`GRADUATED` status alone cannot issue a new certificate. Certificate grades retain
fractional precision. Certificate generation/delivery UI is outside this task.
The frontend graduation page at `/tracks/:trackId/graduation` uses read-only
eligibility for students and explicit finalization for assigned instructors/admins.
The obsolete frontend self-claim call has been removed. See `frontend/README.md`
for the gate views, historical records, and verification commands.

## Migration f15500000001

Apply `alembic upgrade head` before deployment. This task applied migrations only to
local PostgreSQL; production Supabase was not changed.

- Canonical ORM models now live in `app/models/graduation.py`: rules, checks, results.
- Result/check/certificate scores preserve fractional precision. Evaluation/finalization
  timestamps use timezone-aware datetimes. DB constraints enforce ranges and valid statuses.
- Legacy `graduation_evaluations` and `graduation_gate_checks` are renamed with an
  `_archive` suffix and removed from active ORM/API code. Their rows and internal
  relationship are preserved. They no longer reference live users/tracks, so account
  deletion cannot accidentally cascade through historical archives. They need no app writes.
- Existing result/check/certificate rows are preserved. Text check details are wrapped
  in `{ "legacy_text": ... }`; rollback restores the original text. Existing graduated
  rows retain their historical date but must be revalidated before issuing certificates
  when they lack the complete current gate snapshot.
- Invalid historical scores/statuses or timestamp strings abort the migration atomically.
  Correct the offending source data explicitly before retrying.
- Downgrade restores archived table names and foreign keys. It intentionally refuses
  to truncate fractional grades into the old integer columns. Preserve/export such
  records before rolling back. Restoring archived foreign keys also requires referenced
  users/tracks to remain present. Ordinary added snapshot columns are removed on downgrade.

Tests cover each gate independently failing while overall remains high, score boundaries,
foreign/unfinished evidence, unknown rules, RBAC and forgery, repeat finalization,
transaction rollback, certificate bypass prevention, populated migration round trips,
legacy-data preservation, and refusal of lossy downgrade.
