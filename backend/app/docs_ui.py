from __future__ import annotations

from fastapi.responses import HTMLResponse


def hiremind_docs_html(*, title: str, version: str) -> HTMLResponse:
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} · API 控制台</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    :root {{
      --ink:#172035; --muted:#7b8497; --line:#e8eaf0; --soft:#f4f5f8;
      --purple:#6c5ce7; --purple-dark:#5142cf; --sidebar:#171827;
      --card:#fff; --topbar:rgba(255,255,255,.92);
    }}
    * {{ box-sizing:border-box; }}
    html,body {{ margin:0; min-height:100%; background:var(--soft); color:var(--ink);
      font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; }}
    body.dark {{
      --ink:#eef0f6; --muted:#9ca3b8; --line:#303345; --soft:#11131d;
      --card:#1b1e2b; --topbar:rgba(27,30,43,.92);
    }}
    .shell {{ min-height:100vh; display:flex; }}
    .sidebar {{ position:fixed; inset:0 auto 0 0; width:236px; padding:22px 15px 18px;
      color:#fff; background:radial-gradient(circle at 100% 0%,rgba(108,92,231,.14),transparent 36%),var(--sidebar);
      display:flex; flex-direction:column; z-index:20; }}
    .brand {{ display:flex; align-items:center; gap:11px; padding:0 8px 22px; }}
    .brand-mark {{ width:35px; height:35px; border-radius:11px; display:grid; place-items:center;
      font-size:13px; font-weight:800; background:linear-gradient(145deg,#8b7cf6,#5747dc);
      box-shadow:0 8px 24px rgba(108,92,231,.3); }}
    .brand strong,.brand small {{ display:block; }}
    .brand strong {{ font-size:15px; }} .brand small {{ color:#8f94aa; font-size:10px; margin-top:2px; }}
    .workspace {{ display:flex; gap:9px; align-items:center; padding:10px; margin-bottom:22px;
      border:1px solid rgba(255,255,255,.08); border-radius:10px; background:rgba(255,255,255,.04); }}
    .workspace-icon {{ width:30px; height:30px; border-radius:8px; display:grid; place-items:center;
      color:#5445ce; background:#eef2ff; font-size:12px; font-weight:800; }}
    .workspace strong,.workspace span {{ display:block; }} .workspace strong {{ font-size:12px; }}
    .workspace span {{ color:#8f94aa; font-size:9px; margin-top:2px; }}
    .nav-label {{ color:#696e83; font-size:9px; letter-spacing:.14em; margin:0 10px 8px; }}
    .nav {{ display:flex; gap:11px; align-items:center; height:39px; padding:0 11px; margin:2px 0;
      border-radius:8px; color:#9ea3b6; text-decoration:none; font-size:12px; }}
    .nav.active {{ color:#fff; background:linear-gradient(90deg,rgba(108,92,231,.22),rgba(108,92,231,.09));
      box-shadow:inset 2px 0 #8172ef; }}
    .side-status {{ margin-top:auto; padding:14px 10px; border-top:1px solid rgba(255,255,255,.08); }}
    .side-status span {{ display:block; color:#73798f; font-size:9px; margin-bottom:6px; }}
    .side-status strong {{ color:#cfd3df; font-size:11px; font-weight:600; }}
    .main {{ min-width:0; flex:1; margin-left:236px; }}
    .topbar {{ position:sticky; top:0; z-index:15; min-height:62px; padding:0 30px; display:flex;
      align-items:center; justify-content:space-between; border-bottom:1px solid var(--line);
      background:var(--topbar); backdrop-filter:blur(14px); }}
    .crumb {{ display:flex; gap:9px; align-items:center; font-size:12px; }} .crumb span {{ color:var(--muted); }}
    .top-actions {{ display:flex; align-items:center; gap:9px; }}
    .status-pill {{ border:1px solid var(--line); border-radius:20px; padding:7px 10px; background:var(--card);
      color:var(--muted); font-size:11px; }}
    .status-pill i {{ width:7px; height:7px; display:inline-block; margin-right:6px; border-radius:50%; background:#16a779; }}
    .theme {{ width:34px; height:34px; border:1px solid var(--line); border-radius:8px;
      background:var(--card); color:var(--ink); font-size:17px; cursor:pointer; }}
    .content {{ max-width:1280px; margin:0 auto; padding:28px 30px 56px; }}
    .hero {{ display:flex; justify-content:space-between; align-items:end; margin-bottom:18px; }}
    .eyebrow {{ margin:0 0 7px; color:#7666e9; font-size:10px; letter-spacing:.12em; font-weight:700; }}
    h1 {{ margin:0; font-size:25px; letter-spacing:-.6px; }} .hero p {{ color:var(--muted); margin:8px 0 0; font-size:12px; }}
    .version {{ padding:8px 11px; color:#5f52cd; background:#efedff; border-radius:8px; font-size:11px; font-weight:700; }}
    .api-card {{ overflow:hidden; padding:4px 0 18px; border:1px solid var(--line); border-radius:14px;
      background:var(--card); box-shadow:0 4px 18px rgba(31,37,58,.04); }}
    .api-card-head {{ padding:16px 20px 12px; border-bottom:1px solid var(--line); }}
    .api-card-head strong {{ font-size:13px; }} .api-card-head span {{ color:var(--muted); font-size:10px; margin-left:8px; }}
    .swagger-ui {{ color:var(--ink); }} .swagger-ui .topbar,.swagger-ui .information-container {{ display:none; }}
    .swagger-ui .wrapper {{ max-width:none; padding:0 20px; }}
    .swagger-ui .scheme-container {{ margin:0 0 16px; padding:15px 20px; background:transparent; box-shadow:none; border-bottom:1px solid var(--line); }}
    .swagger-ui .opblock-tag {{ color:var(--ink); border-bottom-color:var(--line); font-size:17px; }}
    .swagger-ui .opblock {{ border-radius:9px; box-shadow:none; }}
    .swagger-ui, .swagger-ui .info p, .swagger-ui .opblock-tag, .swagger-ui .opblock .opblock-summary-description,
    .swagger-ui .parameter__name, .swagger-ui table thead tr td, .swagger-ui table thead tr th {{
      font-family:inherit; }}
    body.dark .swagger-ui .opblock-tag,body.dark .swagger-ui .parameter__name,body.dark .swagger-ui .parameter__type,
    body.dark .swagger-ui .response-col_status,body.dark .swagger-ui table thead tr td,body.dark .swagger-ui table thead tr th,
    body.dark .swagger-ui label,body.dark .swagger-ui .model-title,body.dark .swagger-ui .model,body.dark .swagger-ui .responses-inner h4,
    body.dark .swagger-ui .responses-inner h5 {{ color:var(--ink); }}
    body.dark .swagger-ui input,body.dark .swagger-ui textarea,body.dark .swagger-ui select {{ color:var(--ink); background:#242837; border-color:#3b4054; }}
    @media(max-width:820px) {{
      .sidebar {{ display:none; }} .main {{ margin-left:0; }} .topbar,.content {{ padding-left:16px; padding-right:16px; }}
      .status-pill {{ display:none; }} .hero {{ align-items:flex-start; }} h1 {{ font-size:21px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark">HM</div><div><strong>HireMind</strong><small>AI 招聘助手</small></div></div>
      <div class="workspace"><div class="workspace-icon">API</div><div><strong>后端工作台</strong><span>FastAPI 服务控制台</span></div></div>
      <div class="nav-label">开发工具</div>
      <a class="nav active" href="/docs"><span>⌘</span> API 接口文档</a>
      <a class="nav" href="/api/health"><span>◉</span> 服务健康检查</a>
      <a class="nav" href="/openapi.json"><span>{{}}</span> OpenAPI JSON</a>
      <div class="side-status"><span>当前服务</span><strong id="side-health">正在连接…</strong></div>
    </aside>
    <main class="main">
      <header class="topbar">
        <div class="crumb"><span>HireMind</span><b>›</b><strong>API 控制台</strong></div>
        <div class="top-actions">
          <div class="status-pill"><i></i><span id="api-status">服务检测中</span></div>
          <div class="status-pill">AI · <span id="llm-status">检测中</span></div>
          <button class="theme" id="theme-toggle" aria-label="切换明暗主题">☾</button>
        </div>
      </header>
      <div class="content">
        <section class="hero">
          <div><p class="eyebrow">DEVELOPER CONSOLE</p><h1>后端 API 控制台</h1>
            <p>查看、调试招聘岗位、简历批次、AI 分析与审计接口。</p></div>
          <div class="version">V{version}</div>
        </section>
        <section class="api-card">
          <div class="api-card-head"><strong>接口资源</strong><span>可展开接口并直接发起测试请求</span></div>
          <div id="swagger-ui"></div>
        </section>
      </div>
    </main>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    const applyTheme = (theme) => {{
      document.body.classList.toggle("dark", theme === "dark");
      document.getElementById("theme-toggle").textContent = theme === "dark" ? "☀" : "☾";
      localStorage.setItem("hiremind-api-theme", theme);
    }};
    applyTheme(localStorage.getItem("hiremind-api-theme") || "light");
    document.getElementById("theme-toggle").onclick = () =>
      applyTheme(document.body.classList.contains("dark") ? "light" : "dark");
    fetch("/api/health").then(r => r.json()).then(data => {{
      document.getElementById("api-status").textContent = "服务正常";
      document.getElementById("side-health").textContent = data.database + " · " + data.max_batch_files + " 份/批";
      document.getElementById("llm-status").textContent = data.llm === "deepseek" ? "DeepSeek 已配置" : "规则评分";
    }}).catch(() => {{
      document.getElementById("api-status").textContent = "服务异常";
      document.getElementById("side-health").textContent = "连接失败";
    }});
    window.ui = SwaggerUIBundle({{
      url:"/openapi.json",
      dom_id:"#swagger-ui",
      deepLinking:true,
      displayRequestDuration:true,
      filter:true,
      persistAuthorization:true,
      docExpansion:"none",
      defaultModelsExpandDepth:-1,
      tryItOutEnabled:false
    }});
  </script>
</body>
</html>"""
    return HTMLResponse(html)
