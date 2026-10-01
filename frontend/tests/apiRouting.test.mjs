import assert from "node:assert/strict";
import { createServer as createHttpServer } from "node:http";
import { after, before, test } from "node:test";
import { createServer } from "vite";

let backend, vite, frontendOrigin, backendOrigin, auth, api, token;
const originalApiUrl = process.env.VITE_API_URL;
const requests = [];

before(async () => {
  backend = createHttpServer(async (request, response) => {
    const bytes = [];
    for await (const chunk of request) bytes.push(chunk);
    const body = Buffer.concat(bytes).toString();
    requests.push({ method: request.method, path: request.url, headers: request.headers, body });
    let status = 404, data = { detail: "Not Found" };
    if (request.url === "/api/v1/users" && request.method === "POST") {
      const payload = JSON.parse(body || "{}");
      status = payload.email && payload.full_name && payload.password ? 201 : 422;
      data = status === 201 ? { id: 10, email: payload.email, full_name: payload.full_name } : { detail: "Missing fields" };
    } else if (request.url === "/api/v1/login/access-token" && request.method === "POST") {
      const payload = new URLSearchParams(body);
      status = payload.get("username") && payload.get("password") ? 200 : 422;
      data = status === 200 ? { access_token: "routing-test-token", token_type: "bearer" } : { detail: "Missing credentials" };
    } else if (request.url === "/api/v1/users/me" && request.method === "GET") {
      status = request.headers.authorization === "Bearer routing-test-token" ? 200 : 401;
      data = status === 200 ? { id: 10, email: "student@example.test", role_name: "student" } : { detail: "Not authenticated" };
    }
    response.writeHead(status, { "Content-Type": "application/json" });
    response.end(JSON.stringify(data));
  });
  await new Promise((resolve) => backend.listen(0, "127.0.0.1", resolve));
  backendOrigin = `http://127.0.0.1:${backend.address().port}`;
  process.env.VITE_API_URL = backendOrigin;
  vite = await createServer({ mode: "test", server: { host: "127.0.0.1", port: 0, strictPort: true, hmr: false } });
  await vite.listen();
  frontendOrigin = `http://127.0.0.1:${vite.httpServer.address().port}`;
  auth = (await vite.ssrLoadModule("/src/services/auth.service.ts")).AuthService;
  api = (await vite.ssrLoadModule("/src/services/api.ts")).api;
  globalThis.localStorage = { getItem: () => token ?? null };
});

after(async () => {
  await vite?.close();
  if (backend) await new Promise((resolve, reject) => backend.close((error) => error ? reject(error) : resolve()));
  if (originalApiUrl === undefined) delete process.env.VITE_API_URL;
  else process.env.VITE_API_URL = originalApiUrl;
  delete globalThis.localStorage;
});

for (const throughProxy of [false, true]) {
  test(`auth service preserves canonical URLs, form encoding and bearer tokens ${throughProxy ? "through Vite" : "directly"}`, async () => {
    const configuredOrigin = api.defaults.baseURL;
    if (!throughProxy) assert.equal(configuredOrigin, backendOrigin);
    api.defaults.baseURL = throughProxy ? frontendOrigin : backendOrigin;
    requests.length = 0;
    token = null;
    try {
      const account = await auth.register({ email: " student@example.test ", full_name: " Student ", password: "Testing&+=Password" });
      assert.equal(account.email, "student@example.test");
      const login = await auth.login({ username: " student@example.test ", password: "Testing&+=Password" });
      token = login.access_token;
      assert.equal((await auth.getCurrentUser()).id, 10);
      assert.deepEqual(requests.map((request) => `${request.method} ${request.path}`), [
        "POST /api/v1/users", "POST /api/v1/login/access-token", "GET /api/v1/users/me",
      ]);
      assert.deepEqual(JSON.parse(requests[0].body), { email: "student@example.test", full_name: "Student", password: "Testing&+=Password" });
      assert.match(requests[1].headers["content-type"], /^application\/x-www-form-urlencoded/);
      assert.equal(new URLSearchParams(requests[1].body).get("password"), "Testing&+=Password");
      assert.equal(requests[2].headers.authorization, "Bearer routing-test-token");
    } finally {
      api.defaults.baseURL = configuredOrigin;
    }
  });
}

test("Vite passes backend validation and unauthenticated responses instead of returning its HTML fallback", async () => {
  for (const [method, path, expected] of [
    ["POST", "/api/v1/users", 422], ["POST", "/api/v1/login/access-token", 422], ["GET", "/api/v1/users/me", 401],
  ]) {
    const response = await fetch(frontendOrigin + path, { method });
    assert.equal(response.status, expected);
    assert.match(response.headers.get("content-type"), /^application\/json/);
    assert.ok((await response.json()).detail);
  }
});
