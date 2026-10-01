import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createServer } from "vite";

let server;
let getEmbedUrl;

before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false }, appType: "custom" });
  ({ getEmbedUrl } = await server.ssrLoadModule("/src/lib/youtube.ts"));
});

after(async () => {
  await server?.close();
});

test("converts YouTube watch, short, and embed URLs to canonical embed URLs", () => {
  const expected = "https://www.youtube.com/embed/abcdefghijk";
  assert.equal(getEmbedUrl("https://www.youtube.com/watch?v=abcdefghijk&t=30"), expected);
  assert.equal(getEmbedUrl("https://youtu.be/abcdefghijk?si=share"), expected);
  assert.equal(getEmbedUrl("https://www.youtube.com/embed/abcdefghijk?start=30"), expected);
});

test("rejects malformed IDs and non-YouTube URLs", () => {
  assert.equal(getEmbedUrl("https://youtube.com/watch?v=short"), null);
  assert.equal(getEmbedUrl("https://youtube.com.evil.example/watch?v=abcdefghijk"), null);
  assert.equal(getEmbedUrl("javascript:alert(1)"), null);
});