# HireMind AI 招聘初筛 Agent

面向企业 HR 的招聘初筛系统。当前 V1.1 包含可交互管理后台、岗位配置、1–200 份简历批量上传、可恢复处理任务、分层去重、可解释评分、人工决策和审计日志。

## 项目结构

- `app/`：React 管理后台与在线产品 Demo
- `backend/app/`：FastAPI API、数据库模型和异步处理管线
- `backend/tests/`：批量上传、去重、决策与审计测试
- `docker-compose.yml`：PostgreSQL、API 和独立 Worker

## 本地运行

### 前端

```bash
npm install
npm run dev
```

访问 `http://localhost:3000`。

### 后端

复制环境变量文件并填写新的 DeepSeek Key：

```bash
cp backend/.env.example backend/.env
docker compose up
```

API 文档位于 `http://localhost:8020/docs`。

若不启动 PostgreSQL，后端会自动使用 SQLite 作为单机开发数据库：

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r backend/requirements.txt
cd backend
../.venv/bin/uvicorn app.main:app --reload
```

## 后台任务

上传请求会为每份简历创建持久化任务。Web 进程可以在开发环境处理任务；生产环境应运行独立 Worker：

```bash
cd backend
../.venv/bin/python -m app.worker
```

任务包含租约、自动恢复和最多三次重试。PostgreSQL 使用行锁避免多个 Worker 重复领取任务；SQLite 开发模式自动限制为单写入并发。

## 验证

```bash
npm run build
cd backend && ../.venv/bin/pytest
```

测试覆盖岗位创建、20 份批量简历分析、完全重复识别、人工决策、审计记录以及 200 份批次上限。

## 安全原则

- API Key 只通过后端环境变量提供。
- 候选人手机号和邮箱默认通过 API 脱敏。
- AI 结论必须保留评分版本、模型版本和文本证据。
- 年龄、性别、照片和婚育信息不进入评分。
- AI 仅提供辅助建议，最终决定始终由 HR 完成。
