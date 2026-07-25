import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("server-renders the HireMind product shell", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);

  const html = await response.text();
  assert.match(html, /<title>HireMind · AI 招聘初筛 Agent<\/title>/i);
  assert.match(html, /HireMind/);
  assert.match(html, /招聘概览/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape/);
});

test("includes bulk processing, job creation, and theme controls", async () => {
  const [page, css, packageJson] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(page, /创建招聘岗位/);
  assert.match(page, /选择当前岗位/);
  assert.match(page, /演示数据/);
  assert.match(page, /单批最多 200 份/);
  assert.match(page, /切换至夜间模式/);
  assert.match(page, /可恢复处理队列/);
  assert.match(css, /\.app-shell\.dark/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
