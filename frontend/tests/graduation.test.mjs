import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { createServer } from "vite";

let server, helpers, service, api, Gates, Record, Actions;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  helpers = await server.ssrLoadModule("/src/lib/graduation.ts");
  service = (await server.ssrLoadModule("/src/services/graduation.service.ts")).graduationService;
  api = (await server.ssrLoadModule("/src/services/api.ts")).api;
  const components = await server.ssrLoadModule("/src/components/GraduationGates.tsx");
  Gates = components.GraduationGates;
  Record = components.GraduationRecord;
  Actions = (await server.ssrLoadModule("/src/pages/Graduation.tsx")).GraduationActions;
  globalThis.localStorage = { getItem: () => "graduation-test-token" };
});
after(async () => { await server?.close(); delete globalThis.localStorage; });

const student = { id: "10", email: "student@example.test", is_active: true, is_superuser: false, role_name: "student" };
const instructor = { ...student, id: "20", role_name: "instructor" };
const timestamp = "2026-09-28T10:00:00Z";
const gates = [
  ["enrollment", 100, 100], ["curriculum_completion", 100, 100],
  ["mandatory_assignments", 100, 100], ["quiz_average", 80, 70],
  ["final_project_score", 80, 75], ["overall_score", 90, 75],
].map(([gate_key, actual_value, required_value]) => ({ gate_key, actual_value, required_value, passed: true, failure_reason: null, details: {} }));
const eligible = { user_id: 10, track_id: 7, overall_score: 90, is_eligible: true, status: "ELIGIBLE", evaluated_at: timestamp, gate_checks: gates, finalized_result: null };
const saved = {
  id: 30, student_id: 10, track_id: 7, overall_score: 90.125, eligible: true, status: "GRADUATED",
  evaluated_at: timestamp, finalized_at: timestamp, finalized_by: 20, created_at: timestamp, updated_at: timestamp,
  checks: gates.map((gate, index) => ({ id: index + 1, rule_id: index + 1, gate_key: gate.gate_key, passed: gate.passed, score: gate.actual_value, required_value: gate.required_value, failure_reason: null, details: {} })),
};
const render = (component, props) => renderToStaticMarkup(createElement(component, props));
const response = (config, data) => ({ config, data, status: 200, statusText: "OK", headers: {} });
const actions = (user, eligibility = eligible, busy = false) => render(Actions, { user, eligibility, busy, onFinalize: () => {} });

for (const [name, user, role] of [
  ["student", student, "student"], ["legacy student", { ...student, role_name: null }, "student"],
  ["instructor", instructor, "manager"], ["admin", { ...instructor, role_name: "AdMiN" }, "manager"],
  ["superuser", { ...student, is_superuser: true }, "manager"],
  ["legacy instructor", { ...instructor, role_name: null, role: "instructor" }, "manager"],
  ["inactive instructor", { ...instructor, is_active: false }, null],
  ["employee", { ...student, role_name: "employee" }, null], ["anonymous", null, null],
]) test(`graduation role boundary: ${name}`, () => {
  assert.equal(helpers.graduationRole(user), role);
  assert.equal(helpers.canFinalizeGraduation(user, eligible), role === "manager" && String(user.id) !== "10");
});

test("students have read-only guidance; staff have an explicit finalize control", () => {
  assert.doesNotMatch(actions(student), /<button|Finalize Graduation/);
  assert.match(actions(student), /instructor or administrator finalizes/);
  const html = actions(instructor);
  assert.match(html, /Finalize Graduation/);
  assert.doesNotMatch(html, /disabled=""/);
  assert.match(html, /student #10 in track #7/);
});

test("staff finalization is disabled for self, pending, failed, completed, and in-flight decisions", () => {
  for (const id of ["10", 10]) {
    const self = { ...instructor, id };
    assert.equal(helpers.canFinalizeGraduation(self, eligible), false);
    assert.match(actions(self), /cannot finalize your own/);
    assert.match(actions(self), /disabled=""/);
  }
  for (const status of ["PENDING", "NOT_GRADUATED", "GRADUATED"]) {
    assert.equal(helpers.canFinalizeGraduation(instructor, { ...eligible, status }), false);
    assert.match(actions(instructor, { ...eligible, status }), /disabled=""/);
  }
  assert.match(actions(instructor, { ...eligible, is_eligible: false }), /disabled=""/);
  assert.match(actions(instructor, eligible, true), /disabled=""/);
  assert.match(actions(instructor, eligible, true), /Finalizing/);
});

for (const key of gates.map((gate) => gate.gate_key)) {
  test(`one failed ${key} gate remains a failure even at a high overall score`, () => {
    const eligibility = {
      ...eligible, is_eligible: false, status: "NOT_GRADUATED", overall_score: 99.9,
      gate_checks: gates.map((gate) => gate.gate_key === key ? { ...gate, actual_value: 100, passed: false, failure_reason: "Required evidence is missing." } : gate),
    };
    const html = render(Gates, { eligibility });
    assert.match(html, /Not graduated/);
    assert.match(html, /99\.9%/);
    assert.match(html, /Fail/);
    assert.match(html, /Required evidence is missing/);
    assert.doesNotMatch(html, /All mandatory graduation gates passed/);
    assert.equal(helpers.canFinalizeGraduation(instructor, eligibility), false);
  });
}

test("gate rendering follows backend flags and stricter thresholds, without inferring eligibility from percentages", () => {
  const html = render(Gates, { eligibility: {
    ...eligible, is_eligible: false, status: "NOT_GRADUATED",
    gate_checks: [{ ...gates[4], actual_value: 79.9999, required_value: 85, passed: false, failure_reason: "Final project grade is below this track's minimum." }],
  } });
  assert.match(html, /79\.9999%/);
  assert.match(html, /85%/);
  assert.match(html, /Fail/);
  assert.match(html, /aria-label="Final project recorded progress"/);
  assert.match(html, /value="79\.9999"/);
});

test("unknown mandatory gates remain visible and untrusted reasons are escaped", () => {
  const html = render(Gates, { eligibility: { ...eligible, gate_checks: [
    { ...gates[0], gate_key: "ADDITIONAL_RULE", passed: false, failure_reason: "Contact staff <script>alert(1)</script>" },
  ] } });
  assert.match(html, /Additional requirement: ADDITIONAL_RULE/);
  assert.match(html, /Fail/);
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
});

test("progress reports completion counts without conflating completion and approval", () => {
  const html = render(Gates, { eligibility: { ...eligible, gate_checks: [
    { ...gates[1], details: { completed_lessons: 3, lessons: 8 } },
    { ...gates[2], details: { approved: 2, total: 4 } },
    { ...gates[3], details: { completed_quizzes: 1, quizzes: 3 } },
  ] } });
  assert.match(html, /3 of 8 completed/);
  assert.match(html, /2 of 4 approved/);
  assert.match(html, /1 of 3 completed/);
});

test("live failures remain separate from a graduated historical snapshot", () => {
  const eligibility = { ...eligible, is_eligible: false, status: "NOT_GRADUATED", finalized_result: saved };
  const current = render(Gates, { eligibility });
  const historical = render(Record, { result: saved });
  assert.match(current, /Not graduated/);
  assert.match(historical, /Historical snapshot/);
  assert.match(historical, /Current eligibility is evaluated separately/);
  assert.match(historical, /Graduated/);
  assert.match(historical, /90\.125%/);
  assert.match(historical, /by staff #20/);
  assert.equal(helpers.canFinalizeGraduation(instructor, eligibility), false);
});

test("historical records preserve null values, zero scores, and gate reasons", () => {
  const result = { ...saved, status: "NOT_GRADUATED", eligible: false, overall_score: null, finalized_at: null, finalized_by: null, evaluated_at: null,
    checks: [{ ...saved.checks[0], passed: false, score: null, required_value: null, details: null, failure_reason: "Missing evidence" }],
  };
  const html = render(Record, { result });
  assert.match(html, /Not recorded/);
  assert.match(html, /Not finalized/);
  assert.match(html, /Missing evidence/);
  assert.doesNotMatch(html, /by staff #null|Invalid Date/);
  assert.match(render(Record, { result: { ...result, overall_score: 0, checks: [] } }), /0%/);
  assert.match(render(Record, { result: { ...result, checks: [] } }), /No gate checks were saved/);
});

test("student lookup rejects malformed, nonpositive, and unsafe identifiers", () => {
  for (const value of ["", "0", "-1", "1.5", "1e2", "Infinity", "NaN", "10abc", "9007199254740992"]) assert.equal(helpers.studentIdInput(value), null);
  assert.equal(helpers.studentIdInput(" 10 "), 10);
});

test("services use scoped authenticated routes, bounded pagination, and cancellable reads", async () => {
  const calls = [];
  api.defaults.adapter = async (config) => { calls.push(config); return response(config, eligible); };
  const signal = new AbortController().signal;
  await service.getEligibility(7, undefined, signal);
  await service.getEligibility(7, 10, signal);
  await service.getResults(7, 25, signal);
  await service.getResult(30, signal);
  assert.deepEqual(calls.map((call) => `${call.method} ${call.url}`), [
    "get /api/v1/graduation/status", "get /api/v1/graduation/status",
    "get /api/v1/graduation/results", "get /api/v1/graduation/results/30",
  ]);
  assert.deepEqual(calls[0].params, { track_id: 7 });
  assert.deepEqual(calls[1].params, { track_id: 7, user_id: 10 });
  assert.deepEqual(calls[2].params, { track_id: 7, skip: 25, limit: 25 });
  for (const call of calls) {
    assert.equal(call.headers.get("Authorization"), "Bearer graduation-test-token");
    assert.equal(call.signal, signal);
  }
});

test("finalization sends no client-computed status, grades, or checks and preserves server decisions", async () => {
  const failed = { ...saved, status: "NOT_GRADUATED", eligible: false, finalized_by: null, finalized_at: null };
  api.defaults.adapter = async (config) => {
    assert.equal(config.method, "post");
    assert.equal(config.url, "/api/v1/graduation/finalize/10");
    assert.deepEqual(config.params, { track_id: 7 });
    assert.deepEqual(JSON.parse(config.data), {});
    assert.equal(config.headers.get("Authorization"), "Bearer graduation-test-token");
    return response(config, failed);
  };
  assert.deepEqual(await service.finalize(7, 10), failed);
});

test("an ambiguous finalization failure is never automatically replayed", async () => {
  let writes = 0;
  api.defaults.adapter = async () => { writes += 1; throw new Error("Connection lost after commit"); };
  await assert.rejects(service.finalize(7, 10), /Connection lost after commit/);
  assert.equal(writes, 1);
});

test("cancelled reads cannot yield data for an old student selection", async () => {
  const request = new AbortController();
  api.defaults.adapter = async (config) => { request.abort(); return response(config, eligible); };
  await assert.rejects(service.getEligibility(7, 10, request.signal), (error) => error.code === "ERR_CANCELED");
});

test("permission, missing-record, conflict, validation and network errors remain actionable", () => {
  const error = (status, detail) => ({ isAxiosError: true, response: { status, data: { detail } } });
  assert.match(helpers.graduationError(error(403)), /do not have access/);
  assert.match(helpers.graduationError(error(404)), /not found/);
  assert.match(helpers.graduationError(error(409)), /Refresh/);
  assert.equal(helpers.graduationError(error(403, "Instructor is not assigned to this track.")), "Instructor is not assigned to this track.");
  assert.equal(helpers.graduationError(error(422, [{ msg: "Invalid track ID" }, { msg: "Invalid student ID" }])), "Invalid track ID. Invalid student ID");
  assert.match(helpers.graduationError(new Error("offline")), /connection/);
});
