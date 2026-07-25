# HireMind AI 招聘初筛 Agent

面向企业 HR 的全栈招聘初筛系统。岗位配置、1–200 份简历批量上传、去重、DeepSeek 分析、排序和人工决策均在同一个应用中完成。

## 项目结构

- `app/`：React 管理后台及同源 API 路由
- `lib/`：简历解析、DeepSeek 分析与共享数据类型
- `db/`：D1 数据表定义
- `drizzle/`：线上数据库迁移

## 本地运行

```bash
npm install
npm run dev
```

访问 `http://localhost:3000`。本地 DeepSeek 配置放在不会提交的 `.dev.vars` 中；线上密钥由托管环境注入，浏览器无法读取。

## 验证

```bash
npm run build
npm test
```

测试覆盖同源 API、真实数据入口、上传流程、岗位操作、候选人决策以及无效入口清理。

## 安全原则

- API Key 只通过服务端运行环境提供。
- 原始简历不会作为模拟数据写入前端代码。
- AI 结论必须保留评分版本、模型版本和文本证据。
- 年龄、性别、照片和婚育信息不进入评分。
- AI 仅提供辅助建议，最终决定始终由 HR 完成。
