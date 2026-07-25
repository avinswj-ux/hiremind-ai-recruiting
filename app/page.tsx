"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ApiCandidate, ApiJob } from "../lib/hiremind";

type Theme = "light" | "dark";
type CandidateFilter = "全部候选人" | "高匹配" | "待 HR 处理" | ApiCandidate["status"];

const statusLabel: Record<ApiJob["status"], string> = {
  open: "招聘中",
  paused: "已暂停",
  archived: "已归档",
};

const candidateStatusOptions: ApiCandidate["status"][] = ["待处理", "建议面试", "已约面试", "人才库"];

function scoreTone(score: number) {
  if (score >= 85) return "high";
  if (score >= 70) return "medium";
  return "low";
}

function initials(name: string) {
  return name.trim().slice(0, 2).toUpperCase() || "HR";
}

function avatarIndex(id: string) {
  return (Array.from(id).reduce((sum, char) => sum + char.charCodeAt(0), 0) % 5) + 1;
}

function relativeTime(value: string) {
  const normalized = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value.replace(" ", "T")}Z`;
  const seconds = Math.max(0, (Date.now() - new Date(normalized).getTime()) / 1000);
  if (seconds < 60) return "刚刚";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} 分钟前`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} 小时前`;
  return `${Math.floor(seconds / 86400)} 天前`;
}

async function api<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  const payload = (await response.json()) as T & { error?: string };
  if (!response.ok) throw new Error(payload.error || "请求失败");
  return payload;
}

export default function Home() {
  const [theme, setTheme] = useState<Theme>("light");
  const [jobs, setJobs] = useState<ApiJob[]>([]);
  const [currentJobId, setCurrentJobId] = useState("");
  const [candidates, setCandidates] = useState<ApiCandidate[]>([]);
  const [selected, setSelected] = useState<ApiCandidate | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<CandidateFilter>("全部候选人");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [jobOpen, setJobOpen] = useState(false);
  const [jobManagerOpen, setJobManagerOpen] = useState(false);
  const [pendingDeleteJob, setPendingDeleteJob] = useState<ApiJob | null>(null);
  const [pendingDeleteCandidate, setPendingDeleteCandidate] = useState<ApiCandidate | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState("");
  const [batch, setBatch] = useState<null | {
    total: number;
    completed: number;
    duplicates: number;
    failed: number;
    running: boolean;
  }>(null);

  const currentJob = jobs.find((job) => job.id === currentJobId) || null;

  const showToast = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3200);
  }, []);

  const loadCandidates = useCallback(async (jobId: string) => {
    if (!jobId) {
      setCandidates([]);
      return;
    }
    const data = await api<{ candidates: ApiCandidate[] }>(`/api/candidates?jobId=${encodeURIComponent(jobId)}`);
    setCandidates(data.candidates);
  }, []);

  const loadJobs = useCallback(async (preferredId?: string) => {
    const data = await api<{ jobs: ApiJob[] }>("/api/jobs");
    setJobs(data.jobs);
    const nextId =
      preferredId && data.jobs.some((job) => job.id === preferredId)
        ? preferredId
        : data.jobs.find((job) => job.status === "open")?.id || data.jobs[0]?.id || "";
    setCurrentJobId(nextId);
    await loadCandidates(nextId);
  }, [loadCandidates]);

  useEffect(() => {
    const saved = window.localStorage.getItem("hiremind-theme");
    if (saved === "dark") setTheme("dark");
    loadJobs()
      .catch((error) => showToast(error instanceof Error ? error.message : "数据加载失败"))
      .finally(() => setLoading(false));
  }, [loadJobs, showToast]);

  useEffect(() => {
    window.localStorage.setItem("hiremind-theme", theme);
  }, [theme]);

  const filtered = useMemo(() => {
    return candidates.filter((candidate) => {
      const haystack = [candidate.name, candidate.company, candidate.role, ...candidate.skills].join(" ").toLowerCase();
      const matchesQuery = !query || haystack.includes(query.toLowerCase());
      const matchesFilter =
        filter === "全部候选人" ||
        (filter === "高匹配" && candidate.score >= 85) ||
        (filter === "待 HR 处理" && ["待处理", "建议面试"].includes(candidate.status)) ||
        candidate.status === filter;
      return matchesQuery && matchesFilter;
    });
  }, [candidates, filter, query]);

  const highMatch = candidates.filter((candidate) => candidate.score >= 85).length;
  const pending = candidates.filter((candidate) => ["待处理", "建议面试"].includes(candidate.status)).length;
  const interviews = candidates.filter((candidate) => candidate.status === "已约面试").length;
  const topCandidate = candidates[0] || null;
  const progress = batch ? Math.round(((batch.completed + batch.duplicates + batch.failed) / batch.total) * 100) : 0;

  async function changeJob(jobId: string) {
    setCurrentJobId(jobId);
    setJobManagerOpen(false);
    setLoading(true);
    try {
      await loadCandidates(jobId);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "候选人加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function setJobStatus(job: ApiJob, status: ApiJob["status"]) {
    try {
      await api(`/api/jobs/${job.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await loadJobs(job.id);
      showToast(`岗位「${job.title}」已${status === "open" ? "恢复招聘" : status === "paused" ? "暂停" : "归档"}`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "岗位更新失败");
    }
  }

  async function confirmDeleteJob() {
    if (!pendingDeleteJob) return;
    try {
      await api(`/api/jobs/${pendingDeleteJob.id}`, { method: "DELETE" });
      const title = pendingDeleteJob.title;
      setPendingDeleteJob(null);
      await loadJobs();
      showToast(`空岗位「${title}」已永久删除`);
    } catch (error) {
      setPendingDeleteJob(null);
      showToast(error instanceof Error ? error.message : "岗位删除失败");
    }
  }

  function focusCandidates(nextFilter: CandidateFilter) {
    setFilter(nextFilter);
    window.setTimeout(() => {
      document.getElementById("candidate-section")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  }

  async function confirmDeleteCandidate() {
    if (!pendingDeleteCandidate) return;
    const candidate = pendingDeleteCandidate;
    try {
      await api(`/api/candidates/${candidate.id}`, { method: "DELETE" });
      setCandidates((items) => items.filter((item) => item.id !== candidate.id));
      setSelected(null);
      setPendingDeleteCandidate(null);
      await loadJobs(currentJobId);
      showToast(`${candidate.name} 已删除，审计记录已保留`);
    } catch (error) {
      setPendingDeleteCandidate(null);
      showToast(error instanceof Error ? error.message : "候选人删除失败");
    }
  }

  async function startAnalysis() {
    if (!currentJob || currentJob.status !== "open") {
      showToast("请先选择一个招聘中的岗位");
      return;
    }
    if (!selectedFiles.length) {
      showToast("请先选择至少 1 份简历");
      return;
    }
    const files = selectedFiles.slice(0, 200);
    setUploadOpen(false);
    setBatch({ total: files.length, completed: 0, duplicates: 0, failed: 0, running: true });
    let cursor = 0;
    const results = { completed: 0, duplicates: 0, failed: 0 };
    const worker = async () => {
      while (cursor < files.length) {
        const file = files[cursor++];
        const form = new FormData();
        form.append("jobId", currentJob.id);
        form.append("file", file);
        try {
          const result = await api<{ duplicate: boolean }>("/api/analyze", { method: "POST", body: form });
          if (result.duplicate) results.duplicates += 1;
          else results.completed += 1;
        } catch {
          results.failed += 1;
        }
        setBatch({ total: files.length, ...results, running: true });
      }
    };
    await Promise.all(Array.from({ length: Math.min(3, files.length) }, worker));
    setBatch({ total: files.length, ...results, running: false });
    setSelectedFiles([]);
    await Promise.all([loadCandidates(currentJob.id), loadJobs(currentJob.id)]);
    showToast(`分析完成：成功 ${results.completed}，重复 ${results.duplicates}，失败 ${results.failed}`);
  }

  async function updateCandidateStatus(candidate: ApiCandidate, status: ApiCandidate["status"]) {
    try {
      await api(`/api/candidates/${candidate.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      setCandidates((items) => items.map((item) => (item.id === candidate.id ? { ...item, status } : item)));
      setSelected(null);
      showToast(`${candidate.name} 已更新为「${status}」`);
    } catch (error) {
      showToast(error instanceof Error ? error.message : "状态更新失败");
    }
  }

  return (
    <main className={`app-shell ${theme === "dark" ? "dark" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><span>hi</span></div>
          <div><strong>HireMind</strong><small>AI 招聘助手</small></div>
        </div>
        <div className="workspace-switch">
          <div className="company-avatar">HR</div>
          <div><strong>招聘工作台</strong><span>真实数据模式</span></div>
        </div>
        <nav aria-label="主要导航">
          <p className="nav-label">工作空间</p>
          <button className="nav-item active" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
            <span>⌂</span>工作台
          </button>
          <button className="nav-item" onClick={() => document.getElementById("candidate-section")?.scrollIntoView({ behavior: "smooth" })}>
            <span>◎</span>候选人<em>{candidates.length}</em>
          </button>
          <button className="nav-item" onClick={() => setJobManagerOpen(true)}>
            <span>▣</span>岗位管理
          </button>
        </nav>
        <div className="sidebar-foot">
          <div className="quota-head"><span>当前岗位已分析</span><strong>{candidates.length}</strong></div>
          <div className="quota-bar"><span style={{ width: `${Math.min(100, candidates.length / 2)}%` }} /></div>
          <small>每批支持 1–200 份简历</small>
          <div className="profile">
            <div className="profile-avatar">HR</div>
            <div><strong>招聘负责人</strong><span>最终决策人</span></div>
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="crumb"><span>工作台</span><b>/</b><strong>招聘概览</strong></div>
          <div className="top-actions">
            <label className="global-search">
              <span>⌕</span>
              <input aria-label="搜索候选人" placeholder="搜索候选人、技能..." value={query} onChange={(event) => setQuery(event.target.value)} />
            </label>
            <button className="icon-button theme-button" aria-label="切换明暗主题" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
              {theme === "light" ? "☾" : "☀"}
            </button>
            <button className="upload-button" onClick={() => (jobs.length ? setUploadOpen(true) : setJobOpen(true))}>
              <span>＋</span>{jobs.length ? "上传简历" : "创建岗位"}
            </button>
          </div>
        </header>

        <div className="content">
          <div className="welcome-row">
            <div>
              <p className="eyebrow">REAL WORKFLOW · DEEPSEEK</p>
              <h1>招聘初筛工作台</h1>
              <p>{currentJob ? <>当前正在处理 <strong>{currentJob.title}</strong> 的真实候选人数据。</> : "创建岗位后即可上传并分析简历。"}</p>
            </div>
            {currentJob && (
              <div className="job-selector">
                <span>当前岗位</span>
                <button onClick={() => setJobManagerOpen(true)}>{currentJob.title} <b>⌄</b></button>
              </div>
            )}
          </div>

          <div className="stats-grid">
            <button className="stat-card stat-action" onClick={() => focusCandidates("全部候选人")}><div className="stat-icon violet">♙</div><div className="stat-copy"><span>候选人总数</span><strong>{candidates.length}</strong><small>查看当前岗位全部记录</small></div><i className="stat-arrow">→</i></button>
            <button className="stat-card stat-action" onClick={() => focusCandidates("高匹配")}><div className="stat-icon blue">✦</div><div className="stat-copy"><span>高匹配候选人</span><strong>{highMatch}</strong><small>综合评分 ≥ 85</small></div><i className="stat-arrow">→</i></button>
            <button className="stat-card stat-action" onClick={() => focusCandidates("待 HR 处理")}><div className="stat-icon amber">◷</div><div className="stat-copy"><span>待 HR 处理</span><strong>{pending}</strong><small>查看等待最终判断的候选人</small></div><i className="stat-arrow">→</i></button>
            <button className="stat-card stat-action" onClick={() => focusCandidates("已约面试")}><div className="stat-icon green">✓</div><div className="stat-copy"><span>已约面试</span><strong>{interviews}</strong><small>查看已推进面试的候选人</small></div><i className="stat-arrow">→</i></button>
          </div>

          {topCandidate ? (
            <section className="insight-card">
              <div className="insight-glow" />
              <div className="ai-orb">✦</div>
              <div className="insight-copy">
                <span>AI 当前洞察</span>
                <h2>{topCandidate.name} 是当前匹配度最高的候选人</h2>
                <p>{topCandidate.summary}</p>
              </div>
              <button onClick={() => setSelected(topCandidate)}>查看报告 <span>→</span></button>
              <div className="insight-score"><strong>{topCandidate.score}</strong><span>最高匹配分</span></div>
            </section>
          ) : (
            <section className="insight-card">
              <div className="insight-glow" />
              <div className="ai-orb">✦</div>
              <div className="insight-copy">
                <span>开始真实分析</span>
                <h2>{jobs.length ? "当前岗位还没有候选人" : "先创建一个真实岗位"}</h2>
                <p>{jobs.length ? "上传 PDF、DOCX 或 TXT 简历后，系统会调用 DeepSeek 生成排序与分析报告。" : "填写岗位硬性要求和经验门槛，系统将以此作为分析基准。"}</p>
              </div>
              <button onClick={() => (jobs.length ? setUploadOpen(true) : setJobOpen(true))}>{jobs.length ? "上传简历" : "创建岗位"} <span>→</span></button>
            </section>
          )}

          {batch && (
            <section className="batch-card">
              <div className="batch-icon">{batch.running ? "↻" : "✓"}</div>
              <div className="batch-copy">
                <div><strong>{batch.running ? "正在解析并调用 DeepSeek" : "本批次处理完成"}</strong><span>成功 {batch.completed} · 重复 {batch.duplicates} · 失败 {batch.failed}</span></div>
                <div className="batch-progress"><i style={{ width: `${progress}%` }} /></div>
              </div>
              <strong className="batch-percent">{progress}%</strong>
            </section>
          )}

          <section className="candidate-section" id="candidate-section">
            <div className="section-head">
              <div><h2>候选人初筛</h2><span>{loading ? "正在读取…" : `已完成 ${candidates.length} 份真实简历分析`}</span></div>
            </div>
            <div className="candidate-toolbar">
              <div className="filter-tabs">
                {(["全部候选人", "高匹配", "待 HR 处理", "已约面试", "人才库"] as CandidateFilter[]).map((item) => (
                  <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>
                    {item}{item === "全部候选人" && <span>{candidates.length}</span>}
                  </button>
                ))}
              </div>
            </div>
            <div className="candidate-table">
              <div className="table-head"><span>候选人</span><span>核心技能</span><span>AI 匹配度</span><span>当前状态</span><span>分析时间</span><span /></div>
              {filtered.map((candidate) => (
                <div
                  className="candidate-row"
                  key={candidate.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`查看 ${candidate.name} 的分析报告`}
                  onClick={() => setSelected(candidate)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelected(candidate);
                    }
                  }}
                >
                  <span className="candidate-info">
                    <i className={`candidate-avatar avatar-${avatarIndex(candidate.id)}`}>{initials(candidate.name)}</i>
                    <span><strong>{candidate.name}</strong><small>{[candidate.company, candidate.role, candidate.years].filter(Boolean).join(" · ") || candidate.fileName}</small></span>
                  </span>
                  <span className="skill-list">
                    {candidate.skills.slice(0, 3).map((skill) => <i key={skill}>{skill}</i>)}
                    {candidate.skills.length > 3 && <em>+{candidate.skills.length - 3}</em>}
                  </span>
                  <span className="score-cell"><i className={`score-pill ${scoreTone(candidate.score)}`}>{candidate.score}</i><span><i style={{ width: `${candidate.score}%` }} /></span></span>
                  <span className="status-control" onClick={(event) => event.stopPropagation()}>
                    <select
                      aria-label={`修改 ${candidate.name} 的当前状态`}
                      className={`status status-${candidate.status}`}
                      value={candidate.status}
                      onChange={(event) => updateCandidateStatus(candidate, event.target.value as ApiCandidate["status"])}
                    >
                      {candidateStatusOptions.map((status) => <option key={status} value={status}>{status === "建议面试" ? `✦ ${status}` : status}</option>)}
                    </select>
                  </span>
                  <span className="time-cell">{relativeTime(candidate.createdAt)}</span>
                  <span className="row-arrow">›</span>
                </div>
              ))}
              {!loading && filtered.length === 0 && <div className="empty-state">{query || filter !== "全部候选人" ? "没有符合当前筛选条件的候选人。" : "暂无候选人，请上传真实简历开始分析。"}</div>}
            </div>
          </section>
        </div>
      </section>

      {selected && (
        <div className="drawer-backdrop" onMouseDown={() => setSelected(null)}>
          <aside className="detail-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="drawer-head"><div><span>候选人分析报告</span><small>匹配岗位：{currentJob?.title} · {selected.provider}</small></div><button aria-label="关闭详情" onClick={() => setSelected(null)}>×</button></div>
            <div className="candidate-hero">
              <i className={`candidate-avatar large avatar-${avatarIndex(selected.id)}`}>{initials(selected.name)}</i>
              <div><h2>{selected.name}</h2><p>{selected.role || "职位待确认"}{selected.city ? ` · ${selected.city}` : ""}</p><span>{[selected.degree, selected.years].filter(Boolean).join(" · ")}</span></div>
              <div className={`hero-score ${scoreTone(selected.score)}`}><strong>{selected.score}</strong><span>匹配度</span></div>
            </div>
            <div className="drawer-content">
              <div className="ai-summary"><span><i>✦</i> AI 综合结论</span><p>{selected.summary}</p></div>
              <h3>多维匹配评估</h3>
              <div className="dimension-list">
                {selected.dimensions.map((dimension) => (
                  <div key={dimension.label}><div><span>{dimension.label}<small>{dimension.note}</small></span><strong>{dimension.score}</strong></div><p><i style={{ width: `${dimension.score}%` }} /></p></div>
                ))}
              </div>
              <div className="evidence-grid">
                <article className="evidence positive"><span>✓ 推荐依据</span><p>{selected.strength}</p></article>
                <article className="evidence warning"><span>△ 待核实风险</span><p>{selected.risk}</p></article>
              </div>
              <h3>技能标签</h3>
              <div className="all-skills">{selected.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>
              <div className="fairness-note"><span>◉</span><p><strong>公平性保护已开启</strong>本次评分未使用年龄、性别、照片、婚育等敏感信息。</p></div>
            </div>
            <div className="drawer-actions">
              <button className="danger-outline" onClick={() => setPendingDeleteCandidate(selected)}>删除候选人</button>
              <button className="secondary" onClick={() => updateCandidateStatus(selected, "人才库")}>加入人才库</button>
              <button className="primary" onClick={() => updateCandidateStatus(selected, "已约面试")}>推进面试 <span>→</span></button>
            </div>
          </aside>
        </div>
      )}

      {uploadOpen && currentJob && (
        <div className="modal-backdrop" onMouseDown={() => !batch?.running && setUploadOpen(false)}>
          <div className="upload-modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-head"><div><h2>上传候选人简历</h2><p>上传后将真实解析、去重并调用 DeepSeek 生成报告</p></div><button onClick={() => setUploadOpen(false)}>×</button></div>
            <label className="dropzone">
              <input type="file" multiple accept=".pdf,.docx,.txt" onChange={(event) => setSelectedFiles(Array.from(event.target.files || []).slice(0, 200))} />
              <i>{selectedFiles.length ? "✓" : "⇧"}</i>
              <strong>{selectedFiles.length ? `已选择 ${selectedFiles.length} 份简历` : "拖放简历到这里，或点击选择文件"}</strong>
              <span>支持 PDF、DOCX、TXT；每批最多 200 份，单份不超过 20 MB</span>
            </label>
            <div className="upload-settings">
              <label><span>关联岗位</span><select value={currentJobId} onChange={(event) => setCurrentJobId(event.target.value)}>{jobs.filter((job) => job.status === "open").map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select></label>
              <label><span>重复处理</span><select disabled><option>相同岗位自动跳过重复文件</option></select></label>
            </div>
            <div className="job-link-note"><span>↗</span><p>本批简历将按照<strong>「{currentJob.title}」</strong>的经验、硬性要求和加分项生成独立分析报告。</p></div>
            <div className="privacy-tip"><span>⌾</span><p><strong>隐私保护</strong>只保存分析所需文本和可追溯记录，不将密钥发送到浏览器。</p></div>
            <div className="modal-actions"><button onClick={() => setUploadOpen(false)}>取消</button><button className="primary" onClick={startAnalysis}>开始真实解析{selectedFiles.length ? `（${selectedFiles.length}）` : ""}</button></div>
          </div>
        </div>
      )}

      {jobManagerOpen && (
        <div className="modal-backdrop" onMouseDown={() => setJobManagerOpen(false)}>
          <section className="upload-modal job-manager" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-head"><div><h2>岗位管理</h2><p>岗位和候选人均来自持久化数据库</p></div><button onClick={() => setJobManagerOpen(false)}>×</button></div>
            <div className="job-manager-toolbar"><span>全部岗位 <b>{jobs.length}</b></span><button className="primary" onClick={() => { setJobManagerOpen(false); setJobOpen(true); }}>＋ 创建岗位</button></div>
            <div className="job-list" role="listbox" aria-label="选择当前岗位">
              {jobs.map((job) => {
                const isCurrent = currentJobId === job.id;
                return (
                  <button type="button" role="option" aria-selected={isCurrent} className={`job-list-item ${isCurrent ? "selected" : ""}`} key={job.id} onClick={() => changeJob(job.id)}>
                    <i className="job-radio">{isCurrent ? "✓" : ""}</i>
                    <span className="job-main"><strong>{job.title}</strong><small>{job.department || "未分配部门"} · {job.location || "地点待定"}</small></span>
                    <span className="job-metrics"><strong>{job.candidates}</strong><small>候选人</small></span>
                    <span className="job-metrics"><strong>{job.highMatch}</strong><small>高匹配</small></span>
                    <em className={`job-status ${job.status}`}>{statusLabel[job.status]}</em>
                  </button>
                );
              })}
              {!jobs.length && <div className="empty-state">暂无岗位，请创建第一个真实岗位。</div>}
            </div>
            {currentJob && (
              <div className="job-action-bar">
                <div><span>当前操作岗位</span><strong>{currentJob.title}</strong></div>
                <div className="job-action-buttons">
                  {currentJob.status === "open" ? <button onClick={() => setJobStatus(currentJob, "paused")}>暂停招聘</button> : <button onClick={() => setJobStatus(currentJob, "open")}>恢复招聘</button>}
                  {currentJob.status !== "archived" && <button onClick={() => setJobStatus(currentJob, "archived")}>归档岗位</button>}
                  <button className="danger" onClick={() => currentJob.candidates ? showToast("有关联候选人的岗位只能归档") : setPendingDeleteJob(currentJob)}>永久删除</button>
                </div>
              </div>
            )}
            <div className="job-manager-foot"><span>有关联候选人的岗位只能归档；空岗位可以永久删除。</span><button onClick={() => setJobManagerOpen(false)}>关闭</button></div>
          </section>
        </div>
      )}

      {pendingDeleteJob && (
        <div className="confirm-backdrop" onMouseDown={() => setPendingDeleteJob(null)}>
          <section className="confirm-dialog" role="alertdialog" aria-modal="true" onMouseDown={(event) => event.stopPropagation()}>
            <div className="confirm-icon">!</div><h2>永久删除空岗位？</h2><p>即将删除「{pendingDeleteJob.title}」，此操作无法撤销。</p>
            <div><button onClick={() => setPendingDeleteJob(null)}>取消</button><button className="danger-confirm" onClick={confirmDeleteJob}>确认永久删除</button></div>
          </section>
        </div>
      )}

      {pendingDeleteCandidate && (
        <div className="confirm-backdrop" onMouseDown={() => setPendingDeleteCandidate(null)}>
          <section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-candidate-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="confirm-icon">!</div><h2 id="delete-candidate-title">删除候选人记录？</h2><p>即将删除「{pendingDeleteCandidate.name}」的简历分析、评分和当前状态。该操作无法撤销，但会保留删除审计记录。</p>
            <div><button onClick={() => setPendingDeleteCandidate(null)}>取消</button><button className="danger-confirm" onClick={confirmDeleteCandidate}>确认删除候选人</button></div>
          </section>
        </div>
      )}

      {jobOpen && (
        <div className="modal-backdrop" onMouseDown={() => setJobOpen(false)}>
          <form className="upload-modal job-modal" onMouseDown={(event) => event.stopPropagation()} onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            try {
              const data = await api<{ job: ApiJob }>("/api/jobs", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  title: String(form.get("title") || ""),
                  department: String(form.get("department") || ""),
                  location: String(form.get("location") || ""),
                  minYears: Number(form.get("years") || 0),
                  mustHave: String(form.get("mustHave") || "").split(/\n|、|,/).map((item) => item.trim()).filter(Boolean),
                  niceToHave: String(form.get("niceToHave") || "").split(/\n|、|,/).map((item) => item.trim()).filter(Boolean),
                }),
              });
              setJobOpen(false);
              await loadJobs(data.job.id);
              showToast(`岗位「${data.job.title}」已创建`);
            } catch (error) {
              showToast(error instanceof Error ? error.message : "岗位创建失败");
            }
          }}>
            <div className="modal-head"><div><h2>创建招聘岗位</h2><p>这些要求将真实参与后续简历评分</p></div><button type="button" onClick={() => setJobOpen(false)}>×</button></div>
            <div className="job-form-grid">
              <label><span>岗位名称</span><input name="title" required placeholder="例如：高级 Python 后端工程师" /></label>
              <label><span>所属部门</span><input name="department" placeholder="例如：研发部" /></label>
              <label><span>工作地点</span><input name="location" placeholder="例如：深圳 / 远程" /></label>
              <label><span>最低经验</span><select name="years" defaultValue="3"><option value="0">无经验</option><option value="1">1 年</option><option value="2">2 年</option><option value="3">3 年</option><option value="5">5 年及以上</option></select></label>
              <label className="full"><span>硬性要求（每行一项）</span><textarea name="mustHave" required placeholder={"Python\nFastAPI\nPostgreSQL\nDocker"} /></label>
              <label className="full"><span>加分项</span><input name="niceToHave" placeholder="LLM、Redis、Kubernetes" /></label>
            </div>
            <div className="fair-config"><span>✦</span><p><strong>公平性保护默认开启</strong>年龄、性别、照片和婚育信息不会进入评分。</p></div>
            <div className="modal-actions"><button type="button" onClick={() => setJobOpen(false)}>取消</button><button className="primary" type="submit">创建岗位</button></div>
          </form>
        </div>
      )}

      {toast && <div className="toast"><span>✓</span>{toast}</div>}
    </main>
  );
}
