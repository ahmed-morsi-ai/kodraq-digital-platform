# Final Project backend (EPIC 5.4)

The existing final-project tables and canonical routes have been retained and
hardened. Frontend implementation is a separate task. A Master Roadmap v2 file was
not found in this checkout; this work follows the supplied EPIC 5.4 requirements.

## Models and migration

- `TrainingProject`: one per track, enforced by `uq_training_projects_track_id`.
  Passing score is an integer from 0 to 100; title is nonblank. Projects cascade
  from track deletion.
- `ProjectRequirement`: nonblank description, mandatory flag, nonnegative order.
  Ordering is `(order, id)`. Project deletion cascades to requirements.
- `ProjectSubmission`: one per student/project, six existing states, submission
  URLs, notes and timestamps. Project/student deletion cascades to submissions.
- `ProjectReview`: reviewer, numeric score, feedback, decision and timestamps.
  Submission/reviewer deletion retains the existing cascade behavior. Review
  history is ordered by `(created_at, id)`. Historical rubric JSON is preserved.

Revision `f15400000001` follows `f15300000002`. Run `python -m alembic upgrade head`
before deploying this backend. The migration rejects invalid historical scores,
decisions, blank titles/requirements, negative ordering and null requirement
text. An operator must correct invalid records deliberately before retrying;
this migration does not silently rewrite or discard academic records.

The older EPIC 5.4 submission-alignment revision `d5c8e1a3f7b2` had a downgrade
index-order bug. Its downgrade now restores `user_id` before recreating that
column's index. Both that migration and the new constraints have round-trip tests.

## API contract

All paths below are under `/api/v1` and require an active authenticated user.

| Method | Path | Access |
| --- | --- | --- |
| POST | /tracks/{track_id}/final-project | Admin or assigned instructor |
| GET | /tracks/{track_id}/final-project | Enrolled student, admin, assigned instructor |
| GET/PATCH/DELETE | /final-projects/{project_id} | GET follows track access; writes require manager access |
| POST | /final-projects/{project_id}/submissions | Enrolled student, creates DRAFT |
| GET | /final-projects/submissions/me | Student's own work; optional project_id, skip, limit |
| GET | /final-projects/{project_id}/submissions | Admin or assigned instructor |
| GET/PATCH | /final-projects/submissions/{submission_id} | GET owner or scoped manager; PATCH owner only |
| GET | /final-projects/submissions/{submission_id}/reviews | Owner or scoped manager |
| POST | /final-projects/submissions/{submission_id}/reviews | Admin or assigned instructor; self-grading denied |

Students can edit only `DRAFT` and `CHANGES_REQUIRED`. Each write rechecks current
active enrollment and project availability. Existing own work/reviews remain
readable after enrollment ends or a project is deactivated. An instructor who
formerly owned a student submission still needs current track authorization.

Submission input: `github_url`, `live_url`, `file_url`, `student_notes`.
PATCH also accepts `status: "SUBMITTED"`. Identity, project, grade, reviewer and
other status fields cannot be supplied by students. Drafts may be empty; submitting
requires at least one valid work URL. `github_url` must identify a GitHub repository;
other work links must be absolute HTTP(S) URLs without credentials or whitespace.
`file_url` references an existing file; no new final-project upload endpoint is
introduced here. Omitted PATCH fields remain unchanged; nullable URLs/notes can
be cleared explicitly. `submitted_at` records the latest submit/resubmit time.

Review input: `score` (strict integer 0..100), nonblank `feedback`, optional
`status_decision`. Existing `{score, feedback}` calls continue to work: meeting
the project's passing score approves; a lower score requests changes.

| Current state | Allowed review decision |
| --- | --- |
| SUBMITTED | UNDER_REVIEW, CHANGES_REQUIRED, APPROVED, REJECTED |
| UNDER_REVIEW | CHANGES_REQUIRED, APPROVED, REJECTED |
| DRAFT, CHANGES_REQUIRED, APPROVED, REJECTED | None |

Explicit approval requires a passing score. UNDER_REVIEW, CHANGES_REQUIRED and
REJECTED may omit a score but require feedback. Students resubmit changes-required
work with `status: "SUBMITTED"`; earlier reviews remain intact. Approved/rejected
work is terminal. Review responses include `status_decision`, nullable `score`, and
nullable historical `feedback` (new feedback is mandatory).

Role, enrollment and state checks also run in CRUD, not only in HTTP handlers.
PostgreSQL row locks serialize competing creates, edits and reviews. Review insertion
and submission-state changes commit together or roll back together. Pagination
filters by authorized owner/project before applying stable ordering and offsets.

## Cleanup and next-step audit note

Removed unused legacy POST `/final-projects/submissions` and POST
`/final-projects/submissions/{id}/review`, their duplicate Pydantic module
`app/schemas/project_submission.py`, the unsafe legacy `review` CRUD method and
six unused submission CRUD wrappers/exports. Repository callers use the canonical
routes above. Existing frontend code was inspected for callers and left unchanged.

The graduation engine now reads `ProjectSubmission.student_id` and the latest
numeric `ProjectReview.score` and decision. See `GRADUATION_ENGINE.md` for strict
gate thresholds, eligibility reads, and authorized finalization.
