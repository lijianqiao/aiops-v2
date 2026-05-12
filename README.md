# aiops-v2

AIOps 智能自动化运维平台。当前 Phase 1 已具备本地基础设施编排、NetBox seed、gateway webhook 写库、Langfuse trace 记录以及 Hermes bot 只读查询链路。

## Installation

```bash
uv sync --extra dev
```

## Bootstrap

1. `cp .env.example .env`（Windows PowerShell：`Copy-Item .env.example .env`；Windows cmd：`copy .env.example .env`）并填充需要覆盖的密钥。
2. `docker compose up -d`
3. `uv run alembic upgrade head`
4. `uv run python scripts/seed_netbox.py`
5. `uv run pytest tests/integration -v -m integration`

## Quick Start

```bash
uv run python main.py
uv run aiops-cli --help
uv run pytest tests/unit/test_gateway_hooks.py tests/unit/test_read_only_tools.py -v
```

## Configuration

核心运行配置集中在 `.env`：

- `AIOPS_DATABASE_URL` 指向本地 PostgreSQL 控制面库
- `AIOPS_REDIS_URL` 用于 webhook 去重与后续 kill-switch
- `AIOPS_NETBOX_URL` / `AIOPS_NETBOX_TOKEN` 用于 CMDB enrichment 与 seed 校验
- `AIOPS_LANGFUSE_HOST` / `AIOPS_LANGFUSE_PUBLIC_KEY` / `AIOPS_LANGFUSE_SECRET_KEY` 用于 webhook trace
- `AIOPS_LITELLM_ENDPOINT` 预留给后续 LLM 路由与 Fast Path 执行面

注意：为让 Langfuse 在本地 compose 中真正启动，编排文件额外包含 ClickHouse 和 MinIO 作为 Langfuse 的必需依赖。

## Development

```bash
uv sync --extra dev
uv run pytest -v -m "not hermes_runtime"
uv run ruff check src tests
uv run mypy src
```

## Project Status

- Task 0-5：Hermes 插件、gateway hook、只读工具、prompt 注入防护、wiki seed 已完成
- Task 6：本地 docker compose、NetBox seed、Phase 1 live integration 已接入
- 后续任务将继续补齐 Temporal、Execution Policy、Fast Path 和审批工作流

## Known Issues

- **Python 3.14 + Langfuse 4.x**：Langfuse SDK 内部仍引用 `pydantic.v1.datetime_parse`，
  在 Python 3.14 上会触发 `UserWarning: Core Pydantic V1 functionality isn't compatible
  with Python 3.14 or greater`。当前测试和运行链路未受影响，但 Langfuse
  在某些路径上可能行为不稳定。**推荐生产部署使用 Python 3.13**，等 Langfuse
  上游修复后再升级到 3.14。
