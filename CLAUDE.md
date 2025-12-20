# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

红墨（RedInk）是一个小红书 AI 图文生成器，通过一句话 + 一张图片生成完整小红书图文内容。

## 技术栈

- **后端**: Python 3.11+ / Flask / uv 包管理
- **前端**: Vue 3 + TypeScript / Vite / Pinia
- **AI服务**: 文案生成（Gemini/OpenAI兼容）/ 图片生成（Google GenAI/OpenAI兼容/Image API）

## 常用命令

### 后端

```bash
# 安装依赖
uv sync

# 启动后端服务 (端口 12398)
uv run python -m backend.app

# 运行测试
uv run pytest tests/
```

### 前端

```bash
cd frontend

# 安装依赖
pnpm install

# 开发模式 (端口 5173)
pnpm dev

# 构建生产版本
pnpm build
```

### Docker

```bash
# 一键启动
docker run -d -p 12398:12398 -v ./history:/app/history -v ./output:/app/output histonemax/redink:latest

# 使用 docker-compose
docker-compose up -d
```

## 项目架构

### 后端结构 (`backend/`)

```
backend/
├── app.py              # Flask 应用入口，自动检测前端构建产物
├── config.py           # 配置管理
├── routes/             # API 路由（蓝图模式）
│   ├── outline_routes  # 大纲生成 API
│   ├── image_routes    # 图片生成/获取 API
│   ├── history_routes  # 历史记录 CRUD
│   └── config_routes   # 配置管理 API
├── services/           # 业务逻辑层
│   ├── outline.py      # 大纲生成服务
│   ├── image.py        # 图片生成服务（支持并发）
│   └── history.py      # 历史记录服务
├── generators/         # 图片生成器（工厂模式）
│   ├── factory.py      # 生成器工厂
│   ├── base.py         # 基类
│   ├── google_genai.py # Google GenAI 实现
│   ├── openai_compatible.py
│   └── image_api.py
├── utils/              # 工具类
│   ├── text_client.py  # 文本生成客户端
│   ├── genai_client.py # GenAI 客户端
│   └── image_compressor.py
└── prompts/            # Prompt 模板文件
```

### 前端结构 (`frontend/src/`)

```
src/
├── views/              # 页面视图
│   ├── HomeView.vue    # 首页（输入主题）
│   ├── OutlineView.vue # 大纲编辑
│   ├── GenerateView.vue # 图片生成进度
│   ├── ResultView.vue  # 结果展示
│   ├── HistoryView.vue # 历史记录
│   └── SettingsView.vue # 设置页面
├── components/         # 可复用组件
│   ├── home/           # 首页组件
│   ├── history/        # 历史记录组件
│   └── settings/       # 设置组件
├── stores/             # Pinia 状态管理
│   └── generator.ts    # 生成器状态（含本地持久化）
├── api/                # API 封装
└── router/             # Vue Router 配置
```

## 核心业务流程

1. **输入阶段** (HomeView) → 用户输入主题和上传参考图片
2. **大纲生成** (OutlineView) → 调用文本 AI 生成 6-9 页内容大纲
3. **图片生成** (GenerateView) → 先生成封面，再并发生成内容页（最多15张）
4. **结果展示** (ResultView) → 支持单张重新生成、下载

## 配置文件

- `text_providers.yaml` - 文本生成服务商配置
- `image_providers.yaml` - 图片生成服务商配置
- 配置也可通过 Web 界面（设置页面）可视化管理

## API 端点

所有 API 路由前缀为 `/api`：
- `POST /api/outline` - 生成大纲
- `POST /api/generate` - 生成图片（SSE流式）
- `GET /api/images/{task_id}/{filename}` - 获取图片
- `GET /api/history` - 历史记录列表
- `GET/POST/DELETE /api/config/*` - 配置管理

## 注意事项

- 图片生成使用 SSE 流式返回进度
- 封面图会作为后续内容页的参考图，保持风格一致
- `high_concurrency` 配置控制是否并发生成（默认关闭，避免触发 API 速率限制）
