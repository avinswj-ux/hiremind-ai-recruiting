import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const read = (path) => readFile(new URL(path, import.meta.url), "utf8");

test("source contains the full-stack HireMind routes", async () => {
  const [jobs, candidates, analyze] = await Promise.all([
    read("../app/api/jobs/route.ts"),
    read("../app/api/candidates/route.ts"),
    read("../app/api/analyze/route.ts"),
  ]);
  assert.match(jobs, /export async function (GET|POST)/);
  assert.match(candidates, /export async function GET/);
  assert.match(analyze, /analyzeResume/);
});

test("every visible primary control has a real action", async () => {
  const [page, css] = await Promise.all([
    read("../app/page.tsx"),
    read("../app/globals.css"),
  ]);

  assert.match(page, /api<\{ jobs: ApiJob\[\] \}>\("\/api\/jobs"\)/);
  assert.match(page, /fetch\(url, options\)/);
  assert.match(page, /\/api\/analyze/);
  assert.match(page, /\/api\/candidates\/\$\{candidate\.id\}/);
  assert.match(page, /删除候选人/);
  assert.match(page, /确认删除候选人/);
  assert.match(page, /待 HR 处理/);
  assert.match(page, /修改 \$\{candidate\.name\} 的当前状态/);
  assert.match(page, /candidateStatusOptions/);
  assert.match(page, /scrollIntoView/);
  assert.match(page, /setTheme/);
  assert.match(page, /创建招聘岗位/);
  assert.match(page, /上传候选人简历/);
  assert.match(page, /暂停招聘/);
  assert.match(page, /归档岗位/);
  assert.match(page, /确认永久删除/);
  assert.match(page, /<option value="0">无经验<\/option>/);
  assert.match(page, /每批最多 200 份/);
  assert.doesNotMatch(page, /演示数据|即将上线|将在下一版本|可恢复处理队列/);
  assert.match(css, /\.app-shell\.dark/);
  assert.match(css, /Readability V2/);
});

test("no hard-coded candidate or job records remain", async () => {
  const page = await read("../app/page.tsx");
  assert.doesNotMatch(page, /林知远|周雨晴|字节跳动|云杉科技/);
  assert.doesNotMatch(page, /const initialJobs|const candidates:/);
});
