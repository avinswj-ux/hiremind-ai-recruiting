"use client";

import { useEffect, useMemo, useState } from "react";

type Candidate = {
  id: number;
  name: string;
  initials: string;
  role: string;
  company: string;
  years: string;
  city: string;
  degree: string;
  score: number;
  status: "待处理" | "建议面试" | "已约面试" | "人才库";
  applied: string;
  skills: string[];
  strength: string;
  risk: string;
  summary: string;
  dimensions: { label: string; score: number; note: string }[];
};

type HiringJob = {
  id: string;
  title: string;
  department: string;
  location: string;
  candidates: number;
  highMatch: number;
  status: "招聘中" | "已暂停" | "已归档";
  updated: string;
};

const initialJobs: HiringJob[] = [
  { id: "python", title: "高级 Python 后端工程师", department: "研发部", location: "深圳 / 香港", candidates: 24, highMatch: 6, status: "招聘中", updated: "12 分钟前" },
  { id: "ai-app", title: "AI 应用工程师", department: "AI 产品部", location: "深圳", candidates: 18, highMatch: 4, status: "招聘中", updated: "昨天" },
  { id: "product", title: "高级产品经理", department: "产品部", location: "上海 / 远程", candidates: 31, highMatch: 8, status: "招聘中", updated: "2 天前" },
  { id: "design", title: "产品设计师", department: "设计部", location: "深圳", candidates: 12, highMatch: 2, status: "已暂停", updated: "5 天前" },
];

const candidates: Candidate[] = [
  {
    id: 1,
    name: "林知远",
    initials: "LZ",
    role: "高级后端工程师",
    company: "字节跳动 · 推荐系统",
    years: "6 年经验",
    city: "深圳",
    degree: "华中科技大学 · 本科",
    score: 92,
    status: "建议面试",
    applied: "12 分钟前",
    skills: ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "LLM"],
    strength: "主导过千万级日活推荐服务重构，核心技术栈与岗位高度一致。",
    risk: "简历中未明确说明 Kubernetes 的生产环境实践深度。",
    summary:
      "具备 6 年大型互联网后端经验，近 3 年持续使用 Python 与 FastAPI。项目经历可验证，技术深度和业务复杂度均高于岗位基准，建议优先安排技术面试。",
    dimensions: [
      { label: "硬性条件", score: 96, note: "4/4 项满足" },
      { label: "技能匹配", score: 94, note: "核心栈完整" },
      { label: "项目经验", score: 92, note: "高并发场景" },
      { label: "行业经验", score: 88, note: "互联网 / AI" },
      { label: "信息完整度", score: 90, note: "证据充分" },
    ],
  },
  {
    id: 2,
    name: "周雨晴",
    initials: "ZY",
    role: "Python 后端工程师",
    company: "商汤科技 · 平台工程",
    years: "4 年经验",
    city: "上海",
    degree: "同济大学 · 硕士",
    score: 86,
    status: "已约面试",
    applied: "38 分钟前",
    skills: ["Python", "Django", "PostgreSQL", "Docker", "AWS"],
    strength: "AI 平台背景突出，工程能力与学历背景均满足岗位要求。",
    risk: "FastAPI 经验较少，需要确认框架迁移成本。",
    summary:
      "候选人技术基础扎实，在 AI 平台和数据服务方向有连续项目经验。虽然主框架为 Django，但核心后端能力可迁移，建议进入面试验证系统设计能力。",
    dimensions: [
      { label: "硬性条件", score: 90, note: "4/4 项满足" },
      { label: "技能匹配", score: 84, note: "框架可迁移" },
      { label: "项目经验", score: 88, note: "AI 平台经验" },
      { label: "行业经验", score: 86, note: "人工智能" },
      { label: "信息完整度", score: 82, note: "部分需核实" },
    ],
  },
  {
    id: 3,
    name: "陈嘉豪",
    initials: "CJ",
    role: "后端开发工程师",
    company: "顺丰科技 · 物流平台",
    years: "3 年经验",
    city: "深圳",
    degree: "深圳大学 · 本科",
    score: 78,
    status: "待处理",
    applied: "1 小时前",
    skills: ["Python", "Flask", "MySQL", "Redis", "Docker"],
    strength: "工作年限达标，具备完整的后端交付经验与稳定履历。",
    risk: "缺少 PostgreSQL 和生成式 AI 项目经验。",
    summary:
      "基础能力符合岗位要求，物流系统项目具备一定复杂度。技术栈存在两处可接受缺口，建议 HR 复核学习能力与 AI 方向意愿后决定。",
    dimensions: [
      { label: "硬性条件", score: 82, note: "3/4 项满足" },
      { label: "技能匹配", score: 76, note: "2 项缺口" },
      { label: "项目经验", score: 80, note: "交付完整" },
      { label: "行业经验", score: 72, note: "物流科技" },
      { label: "信息完整度", score: 84, note: "证据充分" },
    ],
  },
  {
    id: 4,
    name: "唐安琪",
    initials: "TA",
    role: "全栈工程师",
    company: "创业公司 · 技术中台",
    years: "2.5 年经验",
    city: "广州",
    degree: "华南理工大学 · 本科",
    score: 64,
    status: "人才库",
    applied: "昨天",
    skills: ["TypeScript", "React", "Node.js", "Python", "MongoDB"],
    strength: "全栈交付能力强，React 属于岗位加分项。",
    risk: "后端年限低于要求，SQL 与容器化经验证据不足。",
    summary:
      "候选人潜力较好但现阶段与高级后端岗位仍有差距，建议纳入人才库，后续匹配中级全栈或应用开发岗位。",
    dimensions: [
      { label: "硬性条件", score: 58, note: "年限未达标" },
      { label: "技能匹配", score: 68, note: "偏全栈方向" },
      { label: "项目经验", score: 64, note: "规模待核实" },
      { label: "行业经验", score: 60, note: "创业公司" },
      { label: "信息完整度", score: 74, note: "基本完整" },
    ],
  },
  {
    id: 5,
    name: "吴思成",
    initials: "WS",
    role: "Java 后端工程师",
    company: "平安科技 · 金融云",
    years: "5 年经验",
    city: "深圳",
    degree: "暨南大学 · 本科",
    score: 51,
    status: "待处理",
    applied: "2 天前",
    skills: ["Java", "Spring", "MySQL", "Kafka", "Kubernetes"],
    strength: "金融系统经验丰富，微服务与容器化能力较强。",
    risk: "核心语言与岗位不匹配，简历中无 Python 项目证据。",
    summary:
      "工程资历较好，但核心技术栈偏差较大。若岗位坚持 Python 作为一票条件则不建议推进；可转投 Java 平台相关岗位。",
    dimensions: [
      { label: "硬性条件", score: 42, note: "核心语言不符" },
      { label: "技能匹配", score: 48, note: "技术栈偏差" },
      { label: "项目经验", score: 78, note: "复杂度较高" },
      { label: "行业经验", score: 66, note: "金融科技" },
      { label: "信息完整度", score: 84, note: "证据充分" },
    ],
  },
];

const navItems = [
  ["⌂", "工作台"],
  ["◎", "候选人"],
  ["▣", "岗位管理"],
  ["◫", "人才库"],
  ["◌", "数据洞察"],
];

function scoreTone(score: number) {
  if (score >= 85) return "high";
  if (score >= 70) return "medium";
  return "low";
}

export default function Home() {
  const [activeNav, setActiveNav] = useState("工作台");
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("全部候选人");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [jobOpen, setJobOpen] = useState(false);
  const [jobManagerOpen, setJobManagerOpen] = useState(false);
  const [pendingDeleteJob, setPendingDeleteJob] = useState<HiringJob | null>(null);
  const [toast, setToast] = useState("");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [batchFiles, setBatchFiles] = useState(0);
  const [batchProgress, setBatchProgress] = useState(0);
  const [jobs, setJobs] = useState<HiringJob[]>(initialJobs);
  const [currentJob, setCurrentJob] = useState("高级 Python 后端工程师");

  useEffect(() => {
    const saved = window.localStorage.getItem("hiremind-theme");
    if (saved === "dark") setTheme("dark");
  }, []);

  useEffect(() => {
    window.localStorage.setItem("hiremind-theme", theme);
  }, [theme]);

  const filtered = useMemo(() => {
    return candidates.filter((candidate) => {
      const matchesQuery =
        !query ||
        [candidate.name, candidate.company, candidate.role, ...candidate.skills]
          .join(" ")
          .toLowerCase()
          .includes(query.toLowerCase());
      const matchesFilter =
        filter === "全部候选人" ||
        (filter === "高匹配" && candidate.score >= 85) ||
        candidate.status === filter;
      return matchesQuery && matchesFilter;
    });
  }, [filter, query]);

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }

  function startDemoBatch() {
    const linkedJob = jobs.find((job) => job.title === currentJob);
    if (!linkedJob || linkedJob.status !== "招聘中") {
      showToast("当前岗位未在招聘中，请先恢复岗位再上传简历");
      return;
    }
    if (!selectedFiles.length) {
      showToast("请先选择至少 1 份简历");
      return;
    }
    const count = selectedFiles.length;
    setBatchFiles(count);
    setBatchProgress(8);
    setUploadOpen(false);
    showToast(`${count} 份简历已进入可恢复处理队列`);
    const timer = window.setInterval(() => {
      setBatchProgress((progress) => {
        const next = Math.min(100, progress + Math.max(3, Math.round(Math.random() * 13)));
        if (next === 100) {
          window.clearInterval(timer);
          window.setTimeout(() => showToast(`批次处理完成，发现 ${Math.min(2, Math.floor(count / 10))} 份重复简历`), 150);
        }
        return next;
      });
    }, 520);
  }

  function setJobStatus(jobId: string, status: HiringJob["status"]) {
    setJobs((items) =>
      items.map((job) =>
        job.id === jobId ? { ...job, status, updated: "刚刚" } : job
      )
    );
    const target = jobs.find((job) => job.id === jobId);
    const action = status === "招聘中" ? "恢复招聘" : status === "已暂停" ? "暂停招聘" : "归档";
    showToast(`岗位「${target?.title || ""}」已${action}，操作已记录`);
  }

  function requestDeleteJob(job: HiringJob) {
    if (job.candidates > 0) {
      showToast(`该岗位关联 ${job.candidates} 位候选人，不能永久删除，请先归档`);
      return;
    }
    setPendingDeleteJob(job);
  }

  function confirmDeleteJob() {
    if (!pendingDeleteJob) return;
    const remaining = jobs.filter((job) => job.id !== pendingDeleteJob.id);
    setJobs(remaining);
    if (currentJob === pendingDeleteJob.title) {
      setCurrentJob(remaining.find((job) => job.status === "招聘中")?.title || remaining[0]?.title || "");
    }
    showToast(`空岗位「${pendingDeleteJob.title}」已永久删除，操作已记录`);
    setPendingDeleteJob(null);
  }

  return (
    <main className={`app-shell ${theme === "dark" ? "dark" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><span>hi</span></div>
          <div>
            <strong>HireMind</strong>
            <small>AI 招聘助手</small>
          </div>
        </div>

        <div className="workspace-switch">
          <div className="company-avatar">云</div>
          <div>
            <strong>云杉科技</strong>
            <span>企业工作区</span>
          </div>
          <button aria-label="切换工作区">⌄</button>
        </div>

        <nav aria-label="主要导航">
          <p className="nav-label">工作空间</p>
          {navItems.map(([icon, label]) => (
            <button
              className={activeNav === label ? "nav-item active" : "nav-item"}
              key={label}
              onClick={() => {
                setActiveNav(label);
                if (label === "岗位管理") setJobManagerOpen(true);
                else if (label !== "工作台") showToast(`${label}模块将在后续页面中开放`);
              }}
            >
              <span>{icon}</span>{label}
              {label === "候选人" && <em>24</em>}
            </button>
          ))}
          <p className="nav-label nav-label-spaced">设置</p>
          <button className="nav-item" onClick={() => showToast("团队协作设置将在下一版本开放")}>
            <span>♙</span>团队与权限
          </button>
          <button className="nav-item" onClick={() => showToast("集成中心将在 V1.1 开放")}>
            <span>⌘</span>集成中心
            <i>即将上线</i>
          </button>
        </nav>

        <div className="sidebar-foot">
          <div className="quota-head"><span>本月解析额度</span><strong>68%</strong></div>
          <div className="quota-bar"><span /></div>
          <small>已解析 136 / 200 份简历</small>
          <div className="profile">
            <div className="profile-avatar">赵</div>
            <div><strong>赵敏</strong><span>招聘负责人</span></div>
            <button aria-label="更多">•••</button>
          </div>
        </div>
      </aside>

      <section className="main-panel">
        <header className="topbar">
          <div className="crumb"><span>工作台</span><b>/</b><strong>招聘概览</strong></div>
          <div className="top-actions">
            <label className="global-search">
              <span>⌕</span>
              <input
                aria-label="全局搜索"
                placeholder="搜索候选人、技能..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <kbd>⌘ K</kbd>
            </label>
            <button
              className="icon-button theme-button"
              aria-label={theme === "light" ? "切换至夜间模式" : "切换至白天模式"}
              title={theme === "light" ? "夜间模式" : "白天模式"}
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? "☾" : "☀"}
            </button>
            <button className="icon-button" aria-label="通知" onClick={() => showToast("没有新的待办通知")}>♢<i /></button>
            <button className="upload-button" onClick={() => setUploadOpen(true)}><span>＋</span>上传简历</button>
          </div>
        </header>

        <div className="content">
          <div className="welcome-row">
            <div>
              <p className="eyebrow">2026 年 7 月 25 日 · 周六</p>
              <h1>早上好，赵敏 <span>👋</span></h1>
              <p>今天有 <strong>8 位新候选人</strong> 等待初筛，3 位高匹配候选人值得优先关注。</p>
            </div>
            <div className="job-selector">
              <span>当前岗位</span>
              <button onClick={() => setJobManagerOpen(true)}>{currentJob} <b>⌄</b></button>
            </div>
          </div>

          <div className="stats-grid">
            <article className="stat-card">
              <div className="stat-icon violet">♙</div>
              <div className="stat-copy"><span>候选人总数</span><strong>24</strong><small><b>↗ 12.5%</b> 较上周</small></div>
              <div className="spark-bars purple"><i /><i /><i /><i /><i /><i /><i /></div>
            </article>
            <article className="stat-card">
              <div className="stat-icon blue">✦</div>
              <div className="stat-copy"><span>高匹配候选人</span><strong>6</strong><small><b>25%</b> 综合评分 ≥ 85</small></div>
              <div className="ring"><span>25%</span></div>
            </article>
            <article className="stat-card">
              <div className="stat-icon amber">◷</div>
              <div className="stat-copy"><span>待 HR 处理</span><strong>8</strong><small><b>3 位</b> 已等待超过 24h</small></div>
              <div className="mini-stack"><span>待筛选 5</span><span>待复核 3</span></div>
            </article>
            <article className="stat-card">
              <div className="stat-icon green">✓</div>
              <div className="stat-copy"><span>本周推进面试</span><strong>4</strong><small><b>＋2</b> 较上周</small></div>
              <div className="avatar-stack"><span>L</span><span>Z</span><span>C</span><span>+1</span></div>
            </article>
          </div>

          <section className="insight-card">
            <div className="insight-glow" />
            <div className="ai-orb">✦</div>
            <div className="insight-copy">
              <span>AI 每日洞察</span>
              <h2>3 位候选人与岗位高度匹配</h2>
              <p>林知远的技术栈覆盖率最高；周雨晴具备稀缺的 AI 平台经验。建议今天优先联系，预计可提升面试转化率。</p>
            </div>
            <button onClick={() => setSelected(candidates[0])}>查看候选人 <span>→</span></button>
            <div className="insight-score"><strong>92</strong><span>最高匹配分</span></div>
          </section>

          {batchFiles > 0 && (
            <section className="batch-card">
              <div className="batch-icon">{batchProgress === 100 ? "✓" : "↻"}</div>
              <div className="batch-copy">
                <div>
                  <strong>{batchProgress === 100 ? "批次解析完成" : "批次正在解析"}</strong>
                  <span>共 {batchFiles} 份简历 · 数据已持久化，关闭页面也不会中断</span>
                </div>
                <div className="batch-progress"><i style={{ width: `${batchProgress}%` }} /></div>
              </div>
              <strong className="batch-percent">{batchProgress}%</strong>
              <button onClick={() => showToast("已打开批次审计详情")}>查看详情</button>
            </section>
          )}

          <section className="candidate-section">
            <div className="section-head">
              <div><h2>候选人初筛</h2><span>AI 已完成 24 份简历分析</span></div>
              <button className="text-button" onClick={() => showToast("已切换至完整候选人列表")}>查看全部 <span>→</span></button>
            </div>

            <div className="candidate-toolbar">
              <div className="filter-tabs">
                {["全部候选人", "高匹配", "待处理", "已约面试", "人才库"].map((item) => (
                  <button key={item} className={filter === item ? "active" : ""} onClick={() => setFilter(item)}>
                    {item}{item === "全部候选人" && <span>24</span>}
                  </button>
                ))}
              </div>
              <div className="table-actions">
                <button onClick={() => showToast("筛选条件已打开")}>≡ 筛选</button>
                <button onClick={() => showToast("当前按匹配度从高到低排序")}>⇅ 匹配度</button>
              </div>
            </div>

            <div className="candidate-table">
              <div className="table-head">
                <span>候选人</span><span>核心技能</span><span>AI 匹配度</span><span>当前状态</span><span>投递时间</span><span />
              </div>
              {filtered.map((candidate) => (
                <button className="candidate-row" key={candidate.id} onClick={() => setSelected(candidate)}>
                  <span className="candidate-info">
                    <i className={`candidate-avatar avatar-${candidate.id}`}>{candidate.initials}</i>
                    <span><strong>{candidate.name}</strong><small>{candidate.company} · {candidate.years}</small></span>
                  </span>
                  <span className="skill-list">
                    {candidate.skills.slice(0, 3).map((skill) => <i key={skill}>{skill}</i>)}
                    {candidate.skills.length > 3 && <em>+{candidate.skills.length - 3}</em>}
                  </span>
                  <span className="score-cell">
                    <i className={`score-pill ${scoreTone(candidate.score)}`}>{candidate.score}</i>
                    <span><i style={{ width: `${candidate.score}%` }} /></span>
                  </span>
                  <span><i className={`status status-${candidate.status}`}>{candidate.status === "建议面试" && "✦ "}{candidate.status}</i></span>
                  <span className="time-cell">{candidate.applied}</span>
                  <span className="row-arrow">›</span>
                </button>
              ))}
              {filtered.length === 0 && (
                <div className="empty-state">没有找到匹配的候选人，请调整搜索条件。</div>
              )}
            </div>
          </section>

          <div className="bottom-grid">
            <section className="pipeline-card">
              <div className="section-head compact"><div><h2>招聘漏斗</h2><span>近 30 天</span></div><button>•••</button></div>
              <div className="pipeline">
                {[
                  ["收到简历", 48, "100%"],
                  ["通过初筛", 24, "50%"],
                  ["进入面试", 12, "25%"],
                  ["发出 Offer", 4, "8.3%"],
                ].map(([label, value, rate], index) => (
                  <div className="pipeline-row" key={label as string}>
                    <div><span>{label}</span><b>{value}</b></div>
                    <div className="pipeline-bar"><i style={{ width: `${100 - index * 23}%` }} /></div>
                    <em>{rate}</em>
                  </div>
                ))}
              </div>
            </section>
            <section className="activity-card">
              <div className="section-head compact"><div><h2>最近动态</h2><span>团队协作记录</span></div><button>•••</button></div>
              <div className="activities">
                <div><i className="activity-avatar a1">赵</i><p><strong>你</strong> 将 <b>周雨晴</b> 标记为已约面试<span>12 分钟前</span></p></div>
                <div><i className="activity-avatar a2">AI</i><p><strong>AI Agent</strong> 完成 8 份新简历分析<span>38 分钟前</span></p></div>
                <div><i className="activity-avatar a3">王</i><p><strong>王蕾</strong> 将 <b>唐安琪</b> 加入人才库<span>昨天 16:42</span></p></div>
              </div>
            </section>
          </div>
        </div>
      </section>

      {selected && (
        <div className="drawer-backdrop" onMouseDown={() => setSelected(null)}>
          <aside className="detail-drawer" onMouseDown={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div><span>候选人分析报告</span><small>匹配岗位：{currentJob} · 已脱敏评估</small></div>
              <button aria-label="关闭详情" onClick={() => setSelected(null)}>×</button>
            </div>
            <div className="candidate-hero">
              <i className={`candidate-avatar large avatar-${selected.id}`}>{selected.initials}</i>
              <div><h2>{selected.name}</h2><p>{selected.role} · {selected.city}</p><span>{selected.degree} · {selected.years}</span></div>
              <div className={`hero-score ${scoreTone(selected.score)}`}><strong>{selected.score}</strong><span>匹配度</span></div>
            </div>
            <div className="drawer-content">
              <div className="ai-summary">
                <span><i>✦</i> AI 综合结论</span>
                <p>{selected.summary}</p>
              </div>
              <h3>多维匹配评估</h3>
              <div className="dimension-list">
                {selected.dimensions.map((dimension) => (
                  <div key={dimension.label}>
                    <div><span>{dimension.label}<small>{dimension.note}</small></span><strong>{dimension.score}</strong></div>
                    <p><i style={{ width: `${dimension.score}%` }} /></p>
                  </div>
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
              <button className="secondary" onClick={() => showToast(`${selected.name} 已加入人才库`)}>加入人才库</button>
              <button className="primary" onClick={() => { showToast(`已将 ${selected.name} 标记为建议面试`); setSelected(null); }}>推进面试 <span>→</span></button>
            </div>
          </aside>
        </div>
      )}

      {uploadOpen && (
        <div className="modal-backdrop" onMouseDown={() => setUploadOpen(false)}>
          <div className="upload-modal" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-head"><div><h2>上传候选人简历</h2><p>上传后 AI 将自动解析、去重并完成岗位匹配</p></div><button onClick={() => setUploadOpen(false)}>×</button></div>
            <label className="dropzone">
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.txt"
                onChange={(event) => {
                  const files = Array.from(event.target.files || []).slice(0, 200);
                  setSelectedFiles(files);
                  if (files.length) showToast(`已选择 ${files.length} 份简历`);
                }}
              />
              <i>{selectedFiles.length ? "✓" : "⇧"}</i>
              <strong>{selectedFiles.length ? `已选择 ${selectedFiles.length} 份简历` : "拖放简历到这里，或点击选择文件"}</strong>
              <span>{selectedFiles.length ? "可继续添加，单批最多 200 份" : "支持 PDF、DOCX、TXT，单个文件不超过 20 MB"}</span>
            </label>
            <div className="upload-settings">
              <label>
                <span>关联岗位</span>
                <select value={currentJob} onChange={(event) => setCurrentJob(event.target.value)}>
                  {jobs.map((job) => <option key={job.id} value={job.title} disabled={job.status !== "招聘中"}>{job.title}{job.status !== "招聘中" ? `（${job.status}）` : ""}</option>)}
                </select>
              </label>
              <label><span>重复简历处理</span><select defaultValue="merge"><option value="merge">识别后合并为新版本</option><option>跳过重复文件</option></select></label>
            </div>
            <div className="job-link-note"><span>↗</span><p>本批简历将分别与<strong>「{currentJob}」</strong>的硬性条件、加分项和评分权重进行匹配，并生成独立分析报告。</p></div>
            <div className="privacy-tip"><span>⌾</span><p><strong>隐私保护</strong>简历仅用于本次招聘评估，敏感信息会被加密存储。</p></div>
            <div className="modal-actions"><button onClick={() => setUploadOpen(false)}>取消</button><button className="primary" onClick={startDemoBatch}>开始解析{selectedFiles.length ? `（${selectedFiles.length}）` : ""}</button></div>
          </div>
        </div>
      )}

      {jobManagerOpen && (
        <div className="modal-backdrop" onMouseDown={() => setJobManagerOpen(false)}>
          <section className="upload-modal job-manager" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-head">
              <div><h2>岗位管理</h2><p>选择一个岗位作为当前工作台，或创建新的招聘岗位</p></div>
              <button type="button" onClick={() => setJobManagerOpen(false)}>×</button>
            </div>
            <div className="job-manager-toolbar">
              <span>全部岗位 <b>{jobs.length}</b><i>演示数据</i></span>
              <button
                className="primary"
                onClick={() => {
                  setJobManagerOpen(false);
                  setJobOpen(true);
                }}
              >
                ＋ 创建岗位
              </button>
            </div>
            <div className="job-list" role="listbox" aria-label="选择当前岗位">
              {jobs.map((job) => {
                const isCurrent = currentJob === job.title;
                return (
                  <button
                    type="button"
                    role="option"
                    aria-selected={isCurrent}
                    className={`job-list-item ${isCurrent ? "selected" : ""}`}
                    key={job.id}
                    onClick={() => {
                      setCurrentJob(job.title);
                      setJobManagerOpen(false);
                      setActiveNav("工作台");
                      showToast(`已切换至「${job.title}」`);
                    }}
                  >
                    <i className="job-radio">{isCurrent ? "✓" : ""}</i>
                    <span className="job-main">
                      <strong>{job.title}</strong>
                      <small>{job.department} · {job.location} · 更新于 {job.updated}</small>
                    </span>
                    <span className="job-metrics"><strong>{job.candidates}</strong><small>候选人</small></span>
                    <span className="job-metrics"><strong>{job.highMatch}</strong><small>高匹配</small></span>
                    <em className={`job-status ${job.status === "招聘中" ? "open" : job.status === "已暂停" ? "paused" : "archived"}`}>{job.status}</em>
                  </button>
                );
              })}
            </div>
            <div className="job-action-bar">
              <div>
                <span>当前操作岗位</span>
                <strong>{currentJob}</strong>
              </div>
              {(() => {
                const job = jobs.find((item) => item.title === currentJob);
                if (!job) return null;
                return (
                  <div className="job-action-buttons">
                    {job.status === "招聘中" ? (
                      <button type="button" onClick={() => setJobStatus(job.id, "已暂停")}>暂停招聘</button>
                    ) : (
                      <button type="button" onClick={() => setJobStatus(job.id, "招聘中")}>恢复招聘</button>
                    )}
                    <button type="button" onClick={() => setJobStatus(job.id, "已归档")}>归档岗位</button>
                    <button type="button" className="danger" onClick={() => requestDeleteJob(job)}>永久删除</button>
                  </div>
                );
              })()}
            </div>
            <div className="job-manager-foot">
              <span>有关联候选人的岗位只能归档；只有空岗位可以永久删除。</span>
              <button type="button" onClick={() => setJobManagerOpen(false)}>关闭</button>
            </div>
          </section>
        </div>
      )}

      {pendingDeleteJob && (
        <div className="confirm-backdrop" onMouseDown={() => setPendingDeleteJob(null)}>
          <section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-job-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="confirm-icon">!</div>
            <h2 id="delete-job-title">永久删除空岗位？</h2>
            <p>即将删除「{pendingDeleteJob.title}」。此操作无法撤销，但会保留一条删除审计记录。</p>
            <div>
              <button type="button" onClick={() => setPendingDeleteJob(null)}>取消</button>
              <button type="button" className="danger-confirm" onClick={confirmDeleteJob}>确认永久删除</button>
            </div>
          </section>
        </div>
      )}

      {jobOpen && (
        <div className="modal-backdrop" onMouseDown={() => setJobOpen(false)}>
          <form
            className="upload-modal job-modal"
            onMouseDown={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              const title = String(data.get("title") || "未命名岗位");
              const department = String(data.get("department") || "未分配部门");
              const location = String(data.get("location") || "待定");
              const newJob: HiringJob = {
                id: `job-${Date.now()}`,
                title,
                department,
                location,
                candidates: 0,
                highMatch: 0,
                status: "招聘中",
                updated: "刚刚",
              };
              setJobs((items) => [newJob, ...items]);
              setCurrentJob(title);
              setJobOpen(false);
              setActiveNav("工作台");
              showToast(`岗位「${title}」已创建并写入审计日志`);
            }}
          >
            <div className="modal-head"><div><h2>创建招聘岗位</h2><p>配置硬性要求与评分基准，后续每次调整都会保留版本记录</p></div><button type="button" onClick={() => setJobOpen(false)}>×</button></div>
            <div className="job-form-grid">
              <label><span>岗位名称</span><input name="title" required defaultValue="高级 Python 后端工程师" /></label>
              <label><span>所属部门</span><input name="department" defaultValue="研发部" /></label>
              <label><span>工作地点</span><input name="location" defaultValue="深圳 / 香港" /></label>
              <label><span>最低经验</span><select name="years" defaultValue="3"><option value="0">无经验</option><option value="1">1 年</option><option value="2">2 年</option><option value="3">3 年</option><option value="5">5 年及以上</option></select></label>
              <label className="full"><span>硬性要求</span><textarea name="mustHave" defaultValue={"Python\nFastAPI / Django\nPostgreSQL\nDocker"} /></label>
              <label className="full"><span>加分项</span><input name="niceToHave" defaultValue="LLM、Redis、Kubernetes、React" /></label>
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
