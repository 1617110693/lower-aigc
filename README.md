# Lower-AIGC — 学术论文 AIGC 率在线降低工具

上传 DOCX 论文，通过 DeepSeek 大模型智能改写，降低 AI 生成内容检测率，同时保持学术严谨性。支持全文或逐段降重，完成后可复制段落/全文或导出为 DOCX。

## 功能特性

- **智能改写** — 内置 3 套降重策略（学术改写 / 风格多样化 / 自然人声），DeepSeek 大模型驱动
- **灵活模式** — 全文一键降重，或逐段精细控制
- **格式保留** — 导出 DOCX 时保留字体、字号、加粗、对齐、行距等原始样式
- **邮箱注册** — 支持邮箱验证注册、密码重置（开发环境可跳过验证）
- **中英双语** — 默认中文，一键切换英文界面
- **一键部署** — Docker Compose 一键启动，也支持本地裸跑调试

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Vue 3 + Vite + Element Plus + vue-i18n + Pinia |
| 后端 | Python FastAPI + SQLAlchemy 2.0 (async) + SQLite |
| AI | DeepSeek API (deepseek-chat) |
| 部署 | Docker + Nginx + docker-compose |

## 快速开始

### 1. 克隆并配置

```bash
git clone <repo-url> lower-aigc
cd lower-aigc
cp .env.example .env
```

编辑 `.env`，至少填入 `DEEPSEEK_API_KEY`：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
```

开发环境建议关闭邮箱验证：

```env
REQUIRE_EMAIL_VERIFICATION=false
```

### 2. Docker 一键启动（推荐）

```bash
docker-compose up -d
```

访问 `http://localhost`，前端 Nginx 自动反向代理 `/api` 到后端。

### 3. 本地开发（非 Docker）

**后端**（需要 Python 3.12+）：

```bash
cd backend
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
cp ../.env .env              # 或直接使用项目根目录的 .env
uvicorn app.main:app --reload --port 8000
```

**前端**（需要 Node.js 20+）：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`，Vite 开发服务器自动代理 `/api` 到后端 `:8000`。

## 项目结构

```
lower-aigc/
├── .env.example              # 配置模板（复制为 .env 后填写）
├── docker-compose.yml        # Docker 编排
├── README.md
│
├── backend/                  # Python FastAPI 后端
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py           # 应用入口，CORS，生命周期
│       ├── config.py         # 配置（从 .env 加载）
│       ├── database.py       # 异步 SQLAlchemy 引擎
│       ├── models/           # ORM 模型（User, Document, Paragraph）
│       ├── schemas/          # Pydantic 请求/响应模型
│       ├── routers/          # API 路由（auth, document, health）
│       ├── services/         # 业务逻辑（auth, document, deepseek, email）
│       ├── core/             # JWT、密码哈希、依赖注入、异常
│       └── utils/            # DOCX 解析器 & 构建器
│
└── frontend/                 # Vue 3 前端
    ├── Dockerfile
    ├── nginx.conf            # Nginx 配置（反向代理 + SPA）
    └── src/
        ├── App.vue           # 布局外壳
        ├── main.js           # 入口，注册插件
        ├── views/            # 7 个页面视图
        ├── components/       # 通用 & 业务组件
        ├── stores/           # 3 个 Pinia store
        ├── api/              # axios 实例 + API 模块
        ├── router/           # 路由 + 认证守卫
        ├── i18n/             # 中英文语言包
        └── composables/      # 可组合函数
```

## API 概览

### 认证 `/api/v1/auth`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 注册，发送验证邮件 |
| POST | `/verify-email` | 邮箱验证 |
| POST | `/login` | 登录，返回 JWT |
| POST | `/forgot-password` | 发送重置邮件 |
| POST | `/reset-password` | 重置密码 |
| GET | `/me` | 获取当前用户信息 |

### 文档 `/api/v1/documents`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/upload` | 上传 DOCX，解析段落 |
| GET | `/` | 文档列表（分页） |
| GET | `/{id}` | 文档详情含段落 |
| POST | `/{id}/reduce` | 启动降 AIGC |
| GET | `/{id}/status` | 降重进度 |
| GET | `/{id}/export` | 导出 DOCX |
| DELETE | `/{id}` | 删除文档 |
| GET | `/prompts` | 可用降重策略列表 |

## 降重策略

| ID | 名称 | 说明 |
|----|------|------|
| `academic-paraphrase` | 学术改写 | 变换句式结构，使用学科词汇，保持学术严谨性 |
| `style-diversification` | 风格多样化 | 长短句交替，添加过渡语，融入领域术语 |
| `natural-human-voice` | 自然人声 | 增加适度不完美，模拟真人写作风格 |

## 配置项

完整配置见 `.env.example`。核心配置：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DEEPSEEK_API_KEY` | **必填** DeepSeek API 密钥 | — |
| `SECRET_KEY` | JWT 签名密钥 | `change-me...` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite+aiosqlite:///./data/lower_aigc.db` |
| `SMTP_HOST` | SMTP 服务器 | `smtp.example.com` |
| `SMTP_PASSWORD` | SMTP 密码（空=控制台模式） | — |
| `REQUIRE_EMAIL_VERIFICATION` | 是否需要邮箱验证 | `true` |
| `MAX_UPLOAD_SIZE_MB` | 上传文件大小限制 | `16` |

## 已知限制

- **仅支持 `.docx`** — `.doc`（旧格式）是二进制格式，`python-docx` 无法解析
- **混合格式简化** — 同一段落内混合加粗/普通文字在导出时简化为统一格式
- **超长文档** — 全文模式段落过多时自动回退为逐段模式，避免超过 token 限制
- **最大段落数** — 默认 500 段，可在 `.env` 中调整 `MAX_PARAGRAPHS_PER_DOC`

## License

MIT
