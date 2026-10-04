import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createServer } from "vite";

let server, parseLessonQuiz, trackService, lessonChatService, api;
const prompts = [
  { id: 7, question: "Synthetic question", options: ["First", "Second"] },
  { id: 2, question: "Another question", options: ["Yes", "No"] },
];
const result = {
  score: 1, total: 2, percentage: 50,
  answers: [
    { question_id: 2, selected_index: 0, correct_index: 1, is_correct: false, explanation: "Synthetic explanation two" },
    { question_id: 7, selected_index: 1, correct_index: 1, is_correct: true, explanation: "Synthetic explanation one" },
  ],
};
function response(config, data) {
  return { data, status: 200, statusText: "OK", headers: {}, config };
}

before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  ({ trackService, parseLessonQuiz } = await server.ssrLoadModule("/src/services/track.service.ts"));
  ({ lessonChatService } = await server.ssrLoadModule("/src/services/lessonChat.service.ts"));
  ({ api } = await server.ssrLoadModule("/src/services/api.ts"));
  globalThis.localStorage = { getItem: () => "synthetic-safe01-token" };
});
after(async () => { await server?.close(); delete globalThis.localStorage; });

test("redacted prompt-only curriculum remains usable as arrays and serialized JSON", () => {
  assert.deepEqual(parseLessonQuiz(prompts), prompts);
  assert.deepEqual(parseLessonQuiz(JSON.stringify(prompts)), prompts);
  assert.deepEqual(parseLessonQuiz(null), []);
  assert.deepEqual(parseLessonQuiz([null, { id: 3, question: "Invalid", options: [] }]), []);
});

test("lesson prompt parsing excludes keys and explanations from scoring and translation inputs", () => {
  const legacy = prompts.map((prompt) => ({ ...prompt, correct_index: 1, explanation: "Protected" }));
  assert.deepEqual(parseLessonQuiz(legacy), prompts);
  assert.equal(JSON.stringify(parseLessonQuiz(legacy)).includes("correct_index"), false);
  assert.equal(JSON.stringify(parseLessonQuiz(legacy)).includes("Protected"), false);
});

test("lesson submit sends selections only through the authenticated canonical endpoint and keeps server grades", async () => {
  let call;
  api.defaults.adapter = async (config) => { call = config; return response(config, result); };
  const answers = [{ question_id: 7, selected_index: 1 }, { question_id: 2, selected_index: 0 }];
  assert.deepEqual(await trackService.submitLessonQuiz(26, 17, answers), result);
  assert.equal(call.method, "post");
  assert.equal(call.url, "/api/v1/tracks/26/lessons/17/quiz/submit");
  assert.equal(call.headers.get("Authorization"), "Bearer synthetic-safe01-token");
  assert.deepEqual(JSON.parse(call.data), { answers });
  assert.equal(JSON.stringify(JSON.parse(call.data)).includes("correct_index"), false);
  assert.equal(JSON.stringify(JSON.parse(call.data)).includes("score"), false);
});

test("submit failure rejects instead of inventing a grade or completing the quiz", async () => {
  const failure = new Error("Synthetic forbidden response");
  api.defaults.adapter = async () => { throw failure; };
  await assert.rejects(trackService.submitLessonQuiz(26, 17, []), (error) => error === failure);
});

test("Arabic translation accepts keyless prompts and discards inferred keys and explanations", async () => {
  let call;
  api.defaults.adapter = async (config) => {
    call = config;
    return response(config, { content: JSON.stringify({ title: "Translated", content: "Translated content", quiz_data: prompts.map((prompt) => ({ ...prompt, correct_index: 1, explanation: "Inferred answer" })) }) });
  };
  const translated = await lessonChatService.translateToArabic({ title: "Synthetic lesson", content: "Synthetic content" }, prompts);
  assert.deepEqual(translated.quiz_data, prompts);
  const submittedContext = JSON.parse(JSON.parse(call.data).messages[1].content);
  assert.deepEqual(submittedContext.quiz_data, prompts);
  assert.equal(JSON.stringify(submittedContext).includes("correct_index"), false);
});

test("submitted explanations can be translated without sending answer keys", async () => {
  const explained = prompts.map((prompt) => ({ ...prompt, explanation: result.answers.find((answer) => answer.question_id === prompt.id).explanation }));
  api.defaults.adapter = async (config) => response(config, { content: JSON.stringify({ title: "Translated", content: "Translated content", quiz_data: explained.map((prompt) => ({ ...prompt, explanation: "Translated explanation" })) }) });
  const translated = await lessonChatService.translateToArabic({ title: "Synthetic lesson", content: "Synthetic content" }, explained);
  assert.deepEqual(translated.quiz_data.map((question) => question.id), [7, 2]);
  assert.equal(translated.quiz_data[0].explanation, "Translated explanation");
  assert.equal(JSON.stringify(translated).includes("correct_index"), false);
});

test("Arabic translation rejects altered question IDs or question ordering", async () => {
  api.defaults.adapter = async (config) => response(config, { content: JSON.stringify({ title: "Translated", content: "Translated content", quiz_data: [...prompts].reverse() }) });
  await assert.rejects(lessonChatService.translateToArabic({ title: "Synthetic lesson", content: "Synthetic content" }, prompts), /changed the quiz answer structure/);
});
