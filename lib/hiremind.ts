export type ApiJob = {
  id: string;
  title: string;
  department: string;
  location: string;
  minYears: number;
  mustHave: string[];
  niceToHave: string[];
  status: "open" | "paused" | "archived";
  candidates: number;
  highMatch: number;
  createdAt: string;
  updatedAt: string;
};

export type ApiCandidate = {
  id: string;
  jobId: string;
  fileName: string;
  name: string;
  role: string;
  company: string;
  years: string;
  city: string;
  degree: string;
  score: number;
  status: "待处理" | "建议面试" | "已约面试" | "人才库";
  skills: string[];
  strength: string;
  risk: string;
  summary: string;
  dimensions: { label: string; score: number; note: string }[];
  provider: string;
  createdAt: string;
};

export function safeJson<T>(value: string, fallback: T): T {
  try {
    return JSON.parse(value) as T;
  } catch {
    return fallback;
  }
}
