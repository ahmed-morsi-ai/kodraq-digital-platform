import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createServer } from "vite";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";

let server, helpers, service, api, ResultView;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  helpers = await server.ssrLoadModule("/src/lib/quizzes.ts");
  service = (await server.ssrLoadModule("/src/services/quiz.service.ts")).quizService;
  api = (await server.ssrLoadModule("/src/services/api.ts")).api;
  ResultView = (await server.ssrLoadModule("/src/pages/QuizResults.tsx")).QuizResultView;
  globalThis.localStorage = { getItem: () => "quiz-test-token" };
});
after(async () => { await server?.close(); delete globalThis.localStorage; });

const questions = [{ question_id: 1 }, { question_id: 2 }];
const payload = { answers: [{ question_id: 1, selected_option_id: 11 }, { question_id: 2, selected_option_id: null }], is_flagged: false, flag_reason: null };
function response(config, data) { return { data, status: 200, statusText: "OK", headers: {}, config }; }

test("only active students receive quiz-taking controls", () => {
  const user = { id: "1", is_active: true, is_superuser: false, role_name: "student" };
  assert.equal(helpers.canTakeQuiz(user), true);
  assert.equal(helpers.canTakeQuiz({ ...user, role_name: null }), true);
  for (const role of ["admin", "instructor", "employee"]) assert.equal(helpers.canTakeQuiz({ ...user, role_name: role }), false);
  assert.equal(helpers.canTakeQuiz({ ...user, is_superuser: true }), false);
  assert.equal(helpers.canTakeQuiz({ ...user, is_active: false }), false);
  assert.equal(helpers.canTakeQuiz(null), false);
});

test("timer uses the server deadline and does not expire a fractional second early", () => {
  const now = Date.parse("2026-09-27T00:00:00Z");
  assert.equal(helpers.remainingQuizSeconds(null, now), null);
  assert.equal(helpers.remainingQuizSeconds("2026-09-27T00:01:00.100Z", now), 61);
  assert.equal(helpers.remainingQuizSeconds("2026-09-26T23:59:59Z", now), 0);
  assert.equal(helpers.formatQuizTime(61), "01:01");
});

test("answer payload excludes foreign questions and all client grades", () => {
  assert.deepEqual(helpers.quizPayload(questions, { 1: 11, 999: 999, score: 100 }), payload);
  assert.deepEqual(helpers.quizPayload(questions, { 1: 11 }, "WINDOW_BLUR"), { ...payload, is_flagged: true, flag_reason: "WINDOW_BLUR" });
});

test("quiz API uses canonical endpoints, pagination, cancellation and authentication", async () => {
  const calls = [];
  api.defaults.adapter = async (config) => { calls.push(config); return response(config, { id: 7 }); };
  const signal = new AbortController().signal;
  await service.getAvailableQuizzes({ trackId: 2, moduleId: 3, lessonId: 4, skip: 100 }, signal);
  await service.getQuiz(7, signal);
  await service.startAttempt(7);
  await service.listAttempts(7, signal, 2, 1);
  await service.getAttempt(9, signal);
  await service.submitAttempt(9, payload);
  await service.getResult(9, signal);
  assert.deepEqual(calls.map((call) => `${call.method} ${call.url}`), ["get /api/v1/quizzes", "get /api/v1/quizzes/7", "post /api/v1/quizzes/7/attempts", "get /api/v1/quizzes/7/attempts", "get /api/v1/quiz-attempts/9", "post /api/v1/quiz-attempts/9/submit", "get /api/v1/quiz-attempts/9/results"]);
  assert.deepEqual(calls[0].params, { track_id: 2, module_id: 3, lesson_id: 4, skip: 100, limit: 100 });
  assert.deepEqual(calls[3].params, { skip: 2, limit: 1 });
  assert.deepEqual(JSON.parse(calls[5].data), payload);
  for (const call of calls) {
    assert.equal(call.headers.get("Authorization"), "Bearer quiz-test-token");
    if (call.method === "get") assert.equal(call.signal, signal);
  }
});

for (const failure of ["deadline HTTP 400", "lost response after commit"]) {
  test(`submission verifies completion after ${failure}`, async () => {
    const calls = [];
    api.defaults.adapter = async (config) => {
      calls.push(config.method);
      if (config.method === "post") throw new Error(failure);
      return response(config, { id: 9, status: "COMPLETED", score: failure.startsWith("deadline") ? 0 : 66.67 });
    };
    const result = await service.submitAndConfirm(9, payload);
    assert.equal(result.status, "COMPLETED");
    assert.deepEqual(calls, ["post", "get"]);
  });
}

test("a failed submit with an open attempt rejects so the UI keeps answers for retry", async () => {
  const failure = new Error("temporary submit failure");
  api.defaults.adapter = async (config) => {
    if (config.method === "post") throw failure;
    return response(config, { id: 9, status: "IN_PROGRESS" });
  };
  await assert.rejects(service.submitAndConfirm(9, payload), (error) => error === failure);
});

test("failed recovery lookup preserves the original submit error", async () => {
  const failure = new Error("submit rejected");
  api.defaults.adapter = async (config) => { throw config.method === "post" ? failure : new Error("offline"); };
  await assert.rejects(service.submitAndConfirm(9, payload), (error) => error === failure);
});

test("successful submission returns the server grade without a second request", async () => {
  let calls = 0;
  api.defaults.adapter = async (config) => { calls++; return response(config, { id: 9, status: "COMPLETED", score: 33.33, passed: false }); };
  assert.equal((await service.submitAndConfirm(9, payload)).score, 33.33);
  assert.equal(calls, 1);
});

test("HTTP field validation and permission errors stay readable", () => {
  assert.equal(helpers.quizError({ isAxiosError: true, response: { data: { detail: [{ msg: "Extra score field forbidden" }] } } }), "Extra score field forbidden");
  assert.equal(helpers.quizError({ isAxiosError: true, response: { data: { detail: "Instructor is not assigned" } } }), "Instructor is not assigned");
});

test("results render backend question_text, precise percentage and earned points", () => {
  const result = { attempt_id: 9, quiz_id: 7, score: 66.67, percentage: 66.67, max_score: 3, earned_points: 2, passed: false, time_taken_seconds: 65, is_flagged: false, flag_reason: null,
    questions: [{ question_id: 1, question_text: "Server question text <safe>", points: 2, selected_option_id: 11, selected_option_text: "Selected", correct_option_ids: [11], correct_option_texts: ["Selected"], is_correct: true }] };
  const html = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(ResultView, { result })));
  assert.match(html, /Server question text &lt;safe&gt;/);
  assert.match(html, /66.67%/);
  assert.match(html, /2 \/ 3/);
  assert.match(html, /Not passed/);
  assert.doesNotMatch(html, />67%/);
});
