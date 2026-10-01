# Quiz attempts and results (EPIC 5.3)

Apply `python -m alembic upgrade head` before deploying this backend. Revision
`f15300000002` adds per-attempt deadlines, passing thresholds, and stored result
details. Local migration verification includes upgrade, downgrade, and re-upgrade.
Production migration/deployment is separate from local implementation verification.

## Access and API

- Active enrolled students discover/read quizzes within their tracks. Inherited
  module/lesson ownership is resolved and inconsistent curriculum links are denied.
- `POST /api/v1/quizzes/{id}/attempts` starts or resumes the student's open attempt.
- `POST /api/v1/quiz-attempts/{id}/submit` accepts question/option IDs and optional
  integrity flags only. Grade, status, ownership and timestamps are server-owned.
- `GET /api/v1/quizzes/{id}/attempts` lists only the student's own attempts; assigned
  instructors see attempts in their tracks, and admins have global read access.
- `GET /api/v1/quiz-attempts/{id}` and `GET .../{id}/results` use the same ownership
  policy. Authorization runs before checking whether a result is available.
- Historical own results remain readable after enrollment ends. New starts and
  submissions require an active enrollment and active quiz.

## Grading

Single-choice multiple-choice and true/false questions require at least two options
and exactly one correct option. Every question contributes its positive point weight;
wrong or omitted answers receive zero. Percentage is earned points / total points
* 100, displayed with two decimal places (half-up rounding). Pass/fail compares the
unrounded ratio to the threshold stored when the attempt started.

Attempt start and finalization use PostgreSQL row locks. A repeated start resumes
one open attempt; competing submits can commit one grade only. Answers, grade and
final result details commit together, with rollback on persistence failure.

Deadline expiry and integrity flags retain the existing zero-score policy. Server
expiry does not depend on a browser flag. Expired submission returns HTTP 400 after
saving a completed zero-score result; the frontend confirms completion before
navigating. Client blur/visibility events are best-effort integrity signals, not
proof of cheating or a substitute for server authorization and scoring.

The final result snapshot preserves question/answer text and weights as graded,
even if the bank is later edited. Existing completed attempts keep their stored
grade; available legacy details are frozen on first authorized result read. Details
already removed before this migration cannot be reconstructed. Quiz content is not
versioned per start: authors should avoid changing a published paper during an active
assessment. Deadline and passing threshold changes affect future starts only.

## Frontend

`QuizList` offers student start/resume and latest-result links. `QuizTaker` sends
answer IDs only, uses the server deadline, prevents duplicate submits and retains
answers after a failed request. A retry checks whether a lost response followed a
successful commit. `QuizResults` renders the stored backend grade and question text.
Answers are held in page state until submission; refreshing an open attempt resets
unsent selections. There is no answer autosave endpoint in this scope.
