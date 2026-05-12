# aiops-v2

AIOps 智能自动化运维平台。当前阶段已完成 Hermes 插件 Task 0 边界探针，并开始建立项目基础骨架与依赖清单。

## Installation

```bash
uv sync --extra dev
```

## Quick Start

```bash
uv run pytest tests/integration/test_phase1_bootstrap.py -v
uv run aiops-cli --help
uv run python main.py
```

## Configuration

Task 1 仅建立项目骨架。完整环境变量与基础设施配置将在后续任务中补齐。

当前关键约束：

- Hermes 插件入口点为 `aiops`
- 本地 bootstrap 入口为 `main.py`
- Python 最低版本目标为 3.13+

## Development

```bash
uv sync --extra dev
uv run pytest -v -m "not hermes_runtime"
uv run ruff check src tests
uv run mypy src
```

## Project Status

- Task 0: Hermes 插件边界探针已落地
- Task 1: 项目骨架与完整依赖清单进行中
- 后续任务将继续补齐 settings、数据库模型、Temporal、Fast Path 和审批工作流
