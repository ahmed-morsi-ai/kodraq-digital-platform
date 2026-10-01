# Kodraq frontend

React, TypeScript, Vite, and Tailwind CSS application for the Kodraq Digital Platform.

Run `npm ci`, set `VITE_API_URL` to the backend origin in `.env.local`
(defaults to `http://localhost:8000`), then run `npm run dev`.

`VITE_API_URL` is the backend **origin**, without `/api/v1`; each service already
includes that prefix. Development requests to `/api/v1` on the Vite origin are
also proxied to this backend without rewriting the path. The proxy is a Vite
development feature; production still needs the configured backend origin or a
deployment reverse proxy. Restart Vite after changing environment files.

If auth returns 404 locally, inspect `http://localhost:8000/api/v1/openapi.json`.
It must contain `POST /api/v1/login/access-token`, `POST /api/v1/users`, and
`GET /api/v1/users/me`. A healthy `/api/v1/health` response alone does not prove
the complete backend is running. An old local Docker image exposed only health
and root routes; rebuild and recreate just the backend from the repository root:

```sh
docker compose up -d --build --no-deps backend
```

No auth prefix rewrite or slash change is required: the canonical paths have no
trailing slash, and FastAPI redirects their trailing-slash variants with 307.
Unauthenticated profile/user-list requests return 401, empty registration/login
requests return 422, and incorrect credentials return 400 under the current API.
Successful registration returns 201; login and profile retrieval return 200.

Verification commands:

```sh
npx tsc --noEmit -p tsconfig.app.json
npx tsc --noEmit -p tsconfig.node.json
npm run lint
node --test --test-concurrency=1 tests/*.test.mjs
npm run build
```

Assignments appear on the track detail page with module filtering. Active students
can read assignment details; administrators and instructors see management controls.
The API enforces track authorization for every request. Assignment details open a
submission workspace: students save drafts, upload files, submit GitHub repository
links, read feedback, and resubmit when changes are requested. Instructors and
administrators can select submissions, download attachments, and post reviews.
Both views display submission attempts and review history. Review fields are shared
with the existing final-project instructor panel.

Apply backend migrations before opening the submission workspace. Local upload
storage is the development default; see `backend/SUBMISSION_STORAGE.md` for
configuration and the persistent-storage requirement for Vercel deployment.


Final projects appear at `/tracks/:trackId/final-project`. Active students can
save drafts, submit repository/live-project/hosted-file links, see every review
and grade, and resubmit only when changes are requested. Project files use the
backend `file_url` contract: provide an accessible hosted file/archive URL.
There is no direct final-project upload endpoint; assignment uploads belong to
assignment submissions and are not reused here.

Admins and assigned instructors receive a paginated submission list with project
links, student notes, and review history. Review decisions are explicit: start
review, request changes, approve, or reject. Feedback is required; grades are
whole numbers from 0 to 100 and approval requires the project's passing score.
The API enforces track isolation, ownership, and transitions. The UI reads roles
from AuthContext, hides student controls from staff, prevents self-review, and
locks completed work. Failed writes reconcile saved state without automatically
replaying a review or clearing entered values. The Refresh button reloads the
workspace and discards unsaved edits.

Graduation appears at `/tracks/:trackId/graduation`, linked from My Learning and
Track Detail. Students see their live eligibility and every server-reported gate:
active enrollment, 100% curriculum completion, approval of all mandatory assignments,
70% quiz average (and each quiz's passing score), 75% final project, and 75% overall.
Stricter track thresholds and additional mandatory gates are displayed as returned
by the API. Pass/fail and overall eligibility are never computed in the browser.
Saved decisions are shown separately from current progress, including their gate
checks, precise scores, evaluation time, and staff finalization details.

Admins and assigned instructors can look up an enrolled student by ID, browse
paginated track records, and explicitly finalize an eligible student. The existing
roster API is superuser-only, so this UI uses the scoped graduation API rather than
introducing an instructor roster endpoint. Student and self-finalization controls
are disabled or hidden. The backend remains responsible for track authorization,
fresh evaluation, and persistence; the finalize request contains no scores or status.
Switching students or tracks cancels pending reads. Failed writes are never replayed
automatically: refresh current eligibility before retrying. A successfully saved
record remains visible even if refreshing live eligibility fails.

The obsolete student certificate-claim component, self-graduation service call,
and legacy evaluation interfaces were removed. Certificate issuance is a separate
workflow. `tests/graduation.test.mjs` covers service contracts, rendered gate/status
views, role boundaries, historical snapshots, cancellation, and write error behavior;
these are Node/SSR regression tests, not browser end-to-end tests.
