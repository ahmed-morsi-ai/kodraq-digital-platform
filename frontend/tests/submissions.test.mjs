import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createServer } from "vite";
import { createServer as createHttpServer } from "node:http";

let server;
let helpers;
let service;
let api;
let originalAdapter;
before(async () => {
  server = await createServer({ server: { middlewareMode: true }, appType: "custom" });
  helpers = await server.ssrLoadModule("/src/lib/submissions.ts");
  service = (await server.ssrLoadModule("/src/services/submission.service.ts")).submissionService;
  api = (await server.ssrLoadModule("/src/services/api.ts")).api;
  originalAdapter = api.defaults.adapter;
  globalThis.localStorage = { getItem: () => "test-token" };
});
after(async () => { await server?.close(); delete globalThis.localStorage; });

test("repository validation rejects deceptive hosts, credentials, profiles and subpaths", () => {
  for (const url of ["https://github.com", "https://github.com/user", "http://github.com/user/repo", "https://github.com.evil/user/repo", "https://evil@github.com/user/repo", "https://github.com:443/user/repo", "https://github.com/user/repo/tree/main", "https://github.com/user/repo?x=1", "https://github.com/user/repo#x", "https://github.com/user/..", "https://github.com/user/.git", "https://github.com/user/repo\n", "https://github.com/K/repo"]) {
    assert.equal(helpers.isRepositoryUrl(url), false, url);
  }
  for (const url of ["https://github.com/user/repo", "HTTPS://GITHUB.COM/my-org/repo.git/"]) assert.equal(helpers.isRepositoryUrl(url), true);
});

test("history retains two submission attempts and both review decisions in chronological order", () => {
  const timeline = helpers.submissionTimeline({ created_at: "2026-01-01T00:00:00Z", attempts: [{ id: 2, submitted_at: "2026-01-04T00:00:00Z" }, { id: 1, submitted_at: "2026-01-02T00:00:00Z" }], reviews: [{ id: "r2", created_at: "2026-01-05T00:00:00Z", status_transition: "APPROVED", feedback_text: "Good", grade: 90 }, { id: "r1", created_at: "2026-01-03T00:00:00Z", status_transition: "CHANGES_REQUIRED", feedback_text: "Revise", grade: 40 }] });
  assert.deepEqual(timeline.map((event) => event.id), ["created", "attempt-1", "r1", "attempt-2", "r2"]);
  assert.equal(timeline[2].feedback, "Revise");
  assert.equal(timeline[4].grade, 90);
});

test("submission service sends canonical endpoints, owner filters, authenticated multipart and blob downloads", async () => {
  const calls = [];
  api.defaults.adapter = async (config) => {
    calls.push(config);
    return { data: { id: 7 }, status: 200, statusText: "OK", headers: {}, config };
  };
  await service.listMine(3, 100);
  await service.listForAssignment(3);
  await service.get(7);
  await service.create(3, { github_url: "https://github.com/user/repo" });
  await service.update(7, { status: "SUBMITTED" });
  await service.review(7, { feedback_text: "Revise", grade: 40, status_transition: "CHANGES_REQUIRED" });
  await service.upload(7, [new File(["work"], "work.txt", { type: "text/plain" })]);
  await service.download(7, "file-id");
  await service.removeFile(7, "file-id");
  assert.deepEqual(calls.map((call) => `${call.method} ${call.url}`), ["get /api/v1/submissions/me", "get /api/v1/assignments/3/submissions", "get /api/v1/submissions/7", "post /api/v1/submissions", "patch /api/v1/submissions/7", "post /api/v1/submissions/7/review", "post /api/v1/submissions/7/files", "get /api/v1/submissions/7/files/file-id/download", "delete /api/v1/submissions/7/files/file-id"]);
  assert.deepEqual(calls[0].params, { assignment_id: 3, skip: 100, limit: 100 });
  assert.equal(JSON.parse(calls[3].data).assignment_id, 3);
  assert.equal(JSON.parse(calls[4].data).status, "SUBMITTED");
  assert.ok(calls[6].data instanceof FormData);
  assert.equal(await calls[6].data.get("files").text(), "work");
  assert.notEqual(calls[6].headers.getContentType(), "application/json");
  assert.equal(calls[7].responseType, "blob");
  for (const call of calls) assert.equal(call.headers.get("Authorization"), "Bearer test-token");
});

test("HTTP validation errors remain readable to students", () => {
  assert.equal(helpers.submissionError({ isAxiosError: true, response: { data: { detail: [{ msg: "Invalid URL" }, { msg: "File too large" }] } } }), "Invalid URL. File too large");
});

test("real HTTP transport supplies a multipart boundary and preserves uploaded bytes", async () => {
  let received;
  const endpoint = createHttpServer(async (request, response) => {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    received = { headers: request.headers, body: Buffer.concat(chunks).toString() };
    response.writeHead(201, { "Content-Type": "application/json" });
    response.end("[]");
  });
  await new Promise((resolve) => endpoint.listen(0, "127.0.0.1", resolve));
  const previousBase = api.defaults.baseURL;
  api.defaults.baseURL = `http://127.0.0.1:${endpoint.address().port}`;
  api.defaults.adapter = originalAdapter;
  try {
    await service.upload(7, [new File(["uploaded work bytes"], "work.txt", { type: "text/plain" })]);
    assert.match(received.headers["content-type"], /^multipart\/form-data; boundary=/);
    assert.equal(received.headers.authorization, "Bearer test-token");
    assert.match(received.body, /name="files"; filename="work.txt"/);
    assert.match(received.body, /uploaded work bytes/);
  } finally {
    api.defaults.baseURL = previousBase;
    await new Promise((resolve, reject) => endpoint.close((error) => error ? reject(error) : resolve()));
  }
});
