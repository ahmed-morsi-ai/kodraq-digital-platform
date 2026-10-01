import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, helpers, service, saveSubmission, reviewSubmission, api, StudentWorkspace, ReviewPanel, Details;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  helpers = await server.ssrLoadModule("/src/lib/finalProjects.ts");
  const module = await server.ssrLoadModule("/src/services/finalProject.service.ts");
  service = module.finalProjectService;
  saveSubmission = module.saveProjectSubmission;
  reviewSubmission = module.reviewProjectSubmission;
  api = (await server.ssrLoadModule("/src/services/api.ts")).api;
  StudentWorkspace = (await server.ssrLoadModule("/src/pages/FinalProject.tsx")).StudentProjectWorkspace;
  ReviewPanel = (await server.ssrLoadModule("/src/components/InstructorReviewPanel.tsx")).default;
  Details = (await server.ssrLoadModule("/src/components/ProjectSubmissionDetails.tsx")).default;
  globalThis.localStorage = { getItem: () => "final-project-test-token" };
});
after(async () => { await server?.close(); delete globalThis.localStorage; });

const student = { id: "10", email: "student@example.test", is_active: true, is_superuser: false, role_name: "student" };
const instructor = { ...student, id: "20", role_name: "instructor" };
const project = { id: 3, track_id: 7, title: "Final project", description: null, passing_score: 75, is_active: true, requirements: [], created_at: "2026-09-28T10:00:00Z", updated_at: "2026-09-28T10:00:00Z" };
const payload = { github_url: "https://github.com/student/project", live_url: null, file_url: "https://files.example/project.zip", student_notes: "Implementation notes" };
const draft = { id: 5, project_id: 3, student_id: 10, ...payload, status: "DRAFT", submitted_at: null, created_at: project.created_at, updated_at: project.updated_at, reviews: [] };
const render = (component, props) => renderToStaticMarkup(createElement(component, props));
const response = (config, data) => ({ config, data, status: 200, statusText: "OK", headers: {} });
const panelProps = (submission, user = instructor) => ({ user, project, submissions: [submission], onUpdated: () => {}, hasMore: true, loadingMore: false, listError: null, onLoadMore: () => {} });

for (const [name, user, expected] of [
  ["student", student, "student"],
  ["legacy student without role", { ...student, role_name: null }, "student"],
  ["instructor", instructor, "manager"],
  ["admin", { ...student, role_name: "AdMiN" }, "manager"],
  ["superuser", { ...student, is_superuser: true }, "manager"],
  ["legacy instructor role", { ...student, role_name: null, role: "instructor" }, "manager"],
  ["employee", { ...student, role_name: "employee" }, null],
  ["inactive instructor", { ...instructor, is_active: false }, null],
  ["anonymous", null, null],
]) test(`workspace access: ${name}`, () => assert.equal(helpers.projectRole(user), expected));

for (const status of ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "CHANGES_REQUIRED", "APPROVED", "REJECTED"]) {
  test(`student editing and instructor review boundaries: ${status}`, () => {
    const submission = { ...draft, status };
    const editable = ["DRAFT", "CHANGES_REQUIRED"].includes(status);
    const reviewable = ["SUBMITTED", "UNDER_REVIEW"].includes(status);
    const studentHtml = render(StudentWorkspace, { user: student, project, submission, onSaved: () => {} });
    assert.equal(studentHtml.includes('aria-label="Final project submission"'), editable);
    assert.equal(helpers.canEditProject(submission), editable);
    assert.equal(helpers.canReviewProject(instructor, submission), reviewable);
    assert.equal(helpers.canReviewProject(student, submission), false);
    assert.equal(helpers.canReviewProject({ ...instructor, id: "10" }, submission), false);
    assert.equal(helpers.canReviewProject({ ...instructor, id: 10 }, submission), false);
    const instructorHtml = render(ReviewPanel, panelProps(submission));
    assert.equal(instructorHtml.includes('aria-label="Review final project"'), reviewable);
    if (status === "CHANGES_REQUIRED") {
      assert.match(studentHtml, /Resubmit for review/);
      assert.match(studentHtml, /Save changes/);
    }
    if (status === "REJECTED") {
      assert.match(studentHtml, /This submission is closed/);
      assert.doesNotMatch(studentHtml, /still a draft/);
    }
    if (status === "UNDER_REVIEW") assert.doesNotMatch(instructorHtml, /<option value="UNDER_REVIEW"/);
  });
}

test("student workspace hides foreign submissions, staff forms and inactive project editing", () => {
  for (const user of [instructor, { ...student, role_name: "admin" }, { ...student, is_active: false }, { ...student, id: "999" }]) {
    assert.equal(render(StudentWorkspace, { user, project, submission: draft, onSaved: () => {} }), "");
  }
  const html = render(StudentWorkspace, { user: { ...student, id: 10 }, project, submission: draft, onSaved: () => {} });
  assert.match(html, /Save draft/);
  assert.doesNotMatch(render(StudentWorkspace, { user: student, project: { ...project, is_active: false }, submission: draft, onSaved: () => {} }), /<form/);
  assert.match(render(StudentWorkspace, { user: student, project, submission: null, onSaved: () => {} }), /Save draft/);
});

test("only staff see review panel and nobody can grade their own work", () => {
  for (const user of [student, null, { ...instructor, is_active: false }]) assert.equal(render(ReviewPanel, panelProps(draft, user)), "");
  const submitted = { ...draft, status: "SUBMITTED" };
  const html = render(ReviewPanel, panelProps(submitted, { ...instructor, id: "10" }));
  assert.match(html, /cannot review your own submission/);
  assert.doesNotMatch(html, /<form/);
  const adminHtml = render(ReviewPanel, panelProps(submitted, { ...instructor, role_name: "admin" }));
  for (const decision of ["UNDER_REVIEW", "CHANGES_REQUIRED", "APPROVED", "REJECTED"]) assert.match(adminHtml, new RegExp(`<option value="${decision}"`));
});

test("reviewers can inspect files, repository, notes and older feedback before grading", () => {
  const html = render(ReviewPanel, panelProps({ ...draft, status: "SUBMITTED", reviews: [{ id: 1, submission_id: 5, reviewer_id: 20, score: 0, feedback: "Fix the tests <first>", status_decision: "CHANGES_REQUIRED", created_at: project.created_at }] }));
  assert.match(html, /href="https:\/\/github.com\/student\/project"/);
  assert.match(html, /href="https:\/\/files.example\/project.zip"/);
  assert.match(html, /Implementation notes/);
  assert.match(html, /Fix the tests &lt;first&gt;/);
  assert.match(html, /0\/100/);
  assert.match(html, /Load more submissions/);
});

test("review history preserves nullable grades, final grades, decisions and deterministic order", () => {
  const submission = { ...draft, status: "APPROVED", reviews: [
    { id: 1, reviewer_id: 20, score: null, feedback: "First review", status_decision: "UNDER_REVIEW", created_at: project.created_at },
    { id: 2, reviewer_id: 20, score: 88, feedback: "Final review", status_decision: "APPROVED", created_at: project.created_at },
  ] };
  const html = render(Details, { submission });
  assert.match(html, /88\/100/);
  assert.match(html, /Not graded/);
  assert.ok(html.indexOf("Final review") < html.indexOf("First review"));
  assert.deepEqual(submission.reviews.map((review) => review.id), [1, 2]);
});

for (const url of ["javascript:alert(1)", "data:text/html,hello", "//files.example/a.zip", "https:///files.example/a.zip", "https://user:password@files.example/file", "https://@files.example/file", "https://files.example:0/file", "https://files.example:65536/file", "https://files.example/has space", "https://files.example/a\\b", "https://files.example/a\u0001b"]) {
  test(`unsafe or invalid project URL rejected: ${JSON.stringify(url)}`, () => {
    assert.equal(helpers.isProjectUrl(url), false);
    assert.notEqual(helpers.validateProjectLinks({ file_url: url }, true), null);
    const html = render(Details, { submission: { ...draft, file_url: url } });
    assert.match(html, /Project files: invalid saved link/);
    assert.doesNotMatch(html, /href="(?:javascript:|data:|\/\/files)/);
  });
}

test("drafts may be empty; submission requires valid links and max URL length", () => {
  assert.equal(helpers.validateProjectLinks({}, false), null);
  assert.match(helpers.validateProjectLinks({}, true), /at least|Add/);
  assert.equal(helpers.validateProjectLinks(payload, true), null);
  assert.equal(helpers.validateProjectLinks({ live_url: "http://localhost:8080/project" }, true), null);
  assert.match(helpers.validateProjectLinks({ github_url: "https://github.com/student/project/issues" }, true), /repository URL/);
  assert.match(helpers.validateProjectLinks({ file_url: `https://files.example/${"a".repeat(512)}` }, true), /512/);
});

for (const decision of ["UNDER_REVIEW", "CHANGES_REQUIRED", "REJECTED"]) {
  test(`${decision} permits ungraded feedback without coercing blank grade to zero`, () => {
    assert.deepEqual(helpers.projectReviewPayload(decision, "", "  Fix tests  ", 75), { status_decision: decision, score: null, feedback: "Fix tests" });
    assert.equal(helpers.projectReviewPayload(decision, "0", "Feedback", 75).score, 0);
  });
}

test("approval requires threshold grade and reviews reject blank feedback or invalid grades", () => {
  for (const score of ["", "74"]) assert.throws(() => helpers.projectReviewPayload("APPROVED", score, "Feedback", 75), /at least 75/);
  assert.deepEqual(helpers.projectReviewPayload("APPROVED", "75", "Approved", 75), { status_decision: "APPROVED", score: 75, feedback: "Approved" });
  for (const score of ["-1", "101", "74.5", "NaN", "Infinity"]) assert.throws(() => helpers.projectReviewPayload("REJECTED", score, "Feedback", 75), /whole-number/);
  assert.throws(() => helpers.projectReviewPayload("APPROVED", "100", "  ", 75), /Feedback/);
});

test("HTTP validation details and permissions remain readable", () => {
  const error = (detail) => ({ isAxiosError: true, response: { data: { detail } } });
  assert.equal(helpers.projectError(error([{ msg: "Invalid URL" }, { msg: "Grade must be an integer" }])), "Invalid URL. Grade must be an integer");
  assert.equal(helpers.projectError(error("Instructor is not assigned to this track.")), "Instructor is not assigned to this track.");
});

test("service uses canonical authenticated endpoints, filtered student lookup, pagination and cancellation", async () => {
  const calls = [];
  api.defaults.adapter = async (config) => { calls.push(config); return response(config, draft); };
  const signal = new AbortController().signal;
  await service.getByTrack(7, signal);
  await service.getMySubmissions({ project_id: 3, limit: 1 }, signal);
  await service.getByProject(3, 50, signal);
  await service.getSubmission(5, signal);
  await service.createSubmission(3, payload);
  await service.updateSubmission(5, { ...payload, status: "SUBMITTED" });
  const review = { score: null, feedback: "Please revise", status_decision: "CHANGES_REQUIRED" };
  await service.createReview(5, review);
  assert.deepEqual(calls.map((call) => `${call.method} ${call.url}`), [
    "get /api/v1/tracks/7/final-project", "get /api/v1/final-projects/submissions/me", "get /api/v1/final-projects/3/submissions", "get /api/v1/final-projects/submissions/5", "post /api/v1/final-projects/3/submissions", "patch /api/v1/final-projects/submissions/5", "post /api/v1/final-projects/submissions/5/reviews",
  ]);
  assert.deepEqual(calls[1].params, { project_id: 3, limit: 1 });
  assert.deepEqual(calls[2].params, { skip: 50, limit: 50 });
  assert.deepEqual(JSON.parse(calls[4].data), payload);
  assert.deepEqual(JSON.parse(calls[5].data), { ...payload, status: "SUBMITTED" });
  assert.deepEqual(JSON.parse(calls[6].data), review);
  for (const call of calls) {
    assert.equal(call.headers.get("Authorization"), "Bearer final-project-test-token");
    if (call.method === "get") assert.equal(call.signal, signal);
  }
});

test("existing unfiltered service consumer remains compatible", async () => {
  api.defaults.adapter = async (config) => { assert.deepEqual(config.params, {}); return response(config, [draft]); };
  assert.deepEqual(await service.getMySubmissions(), [draft]);
});

test("saving a new draft only creates once and never submits", async () => {
  const calls = [], saved = [];
  api.defaults.adapter = async (config) => { calls.push(config.method); return response(config, draft); };
  await saveSubmission(3, null, payload, false, (value) => saved.push(value));
  assert.deepEqual(calls, ["post"]);
  assert.deepEqual(saved, [draft]);
});

test("first submission persists draft identity before sending submit transition", async () => {
  const events = [];
  api.defaults.adapter = async (config) => { events.push(config.method); return response(config, { ...draft, status: config.method === "post" ? "DRAFT" : "SUBMITTED" }); };
  await saveSubmission(3, null, payload, true, (value) => events.push(value.status));
  assert.deepEqual(events, ["post", "DRAFT", "patch", "SUBMITTED"]);
});

for (const submit of [false, true]) test(`rework ${submit ? "resubmits" : "saves without a status change"} using the existing submission`, async () => {
  api.defaults.adapter = async (config) => {
    assert.equal(config.method, "patch");
    const data = JSON.parse(config.data);
    assert.deepEqual(data, submit ? { ...payload, status: "SUBMITTED" } : payload);
    return response(config, { ...draft, status: submit ? "SUBMITTED" : "CHANGES_REQUIRED" });
  };
  const saved = [];
  await saveSubmission(3, { ...draft, status: "CHANGES_REQUIRED" }, payload, submit, (value) => saved.push(value));
  assert.equal(saved[0].status, submit ? "SUBMITTED" : "CHANGES_REQUIRED");
});

test("failed submit keeps created draft and retry only patches it", async () => {
  const failure = new Error("Submit failed");
  const calls = [];
  let saved;
  api.defaults.adapter = async (config) => {
    calls.push(config.method);
    if (config.method === "patch") throw failure;
    return response(config, draft);
  };
  await assert.rejects(saveSubmission(3, null, payload, true, (value) => { saved = value; }), (error) => error === failure);
  assert.deepEqual(saved, draft);
  assert.deepEqual(calls, ["post", "patch", "get"]);
  api.defaults.adapter = async (config) => { assert.equal(config.method, "patch"); return response(config, { ...draft, status: "SUBMITTED" }); };
  await saveSubmission(3, saved, payload, true, (value) => { saved = value; });
  assert.equal(saved.status, "SUBMITTED");
});

for (const operation of ["create", "submit"]) test(`lost ${operation} response reloads authoritative state without replaying the write`, async () => {
  const failure = new Error("Connection lost after commit"), calls = [];
  let saved;
  api.defaults.adapter = async (config) => {
    calls.push(config.method);
    if (config.method !== "get") throw failure;
    if (operation === "create") {
      assert.deepEqual(config.params, { project_id: 3, limit: 1 });
      return response(config, [draft]);
    }
    return response(config, { ...draft, status: "SUBMITTED" });
  };
  await assert.rejects(saveSubmission(3, operation === "create" ? null : draft, payload, true, (value) => { saved = value; }), (error) => error === failure);
  assert.equal(saved.status, operation === "create" ? "DRAFT" : "SUBMITTED");
  assert.deepEqual(calls, [operation === "create" ? "post" : "patch", "get"]);
});

test("failed state lookup preserves original error and does not overwrite local state", async () => {
  const failure = new Error("Update failed");
  api.defaults.adapter = async (config) => { throw config.method === "get" ? new Error("Read also failed") : failure; };
  await assert.rejects(saveSubmission(3, draft, payload, true, () => assert.fail("No saved response")), (error) => error === failure);
});


test("review refresh includes concurrent review history and trusts returned server state", async () => {
  const review = { id: 2, score: 80, feedback: "Approved", status_decision: "APPROVED", updated_at: project.updated_at };
  const calls = [];
  const authoritative = { ...draft, status: "APPROVED", reviews: [{ id: 1, status_decision: "UNDER_REVIEW" }, review] };
  api.defaults.adapter = async (config) => {
    calls.push(config.method);
    return response(config, config.method === "post" ? review : authoritative);
  };
  assert.deepEqual(await reviewSubmission({ ...draft, status: "SUBMITTED" }, { score: 80, feedback: "Approved", status_decision: "APPROVED" }), authoritative);
  assert.deepEqual(calls, ["post", "get"]);
});

test("committed review remains successful if history refresh fails", async () => {
  const review = { id: 1, score: null, feedback: "Revise", status_decision: "CHANGES_REQUIRED", updated_at: project.updated_at };
  api.defaults.adapter = async (config) => {
    if (config.method === "get") throw new Error("Refresh unavailable");
    return response(config, review);
  };
  const result = await reviewSubmission({ ...draft, status: "SUBMITTED" }, { feedback: "Revise", status_decision: "CHANGES_REQUIRED" });
  assert.equal(result.status, "CHANGES_REQUIRED");
  assert.deepEqual(result.reviews, [review]);
});

test("rejected review write never fabricates success or replays the review", async () => {
  const failure = new Error("Not assigned to this track");
  let calls = 0;
  api.defaults.adapter = async () => { calls++; throw failure; };
  await assert.rejects(reviewSubmission(draft, { feedback: "Review", status_decision: "REJECTED" }), (error) => error === failure);
  assert.equal(calls, 1);
});
