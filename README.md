
# GameOps AI Agent

一个用于学习 AI 应用后端开发的游戏运营分析项目。

## 1. 项目目标

逐步构建一个能够查询游戏玩家数据、检索游戏规则、
调用工具并生成运营分析报告的 AI Agent。

当前阶段：Python 后端基础与自动化测试。

尚未接入大模型 API。

## 2. 技术栈

当前已使用：

- Python 3.12
- Python 标准库 json / datetime / pathlib
- dataclasses
- pytest
- Git

后续计划学习：

- FastAPI
- 大模型 API 与 Function Calling
- PostgreSQL / pgvector
- RAG
- LangGraph
- MCP
- Redis
- Docker

## 3. 项目结构

```text
gameops-ai/
├── models.py
├── data.py
├── services.py
├── main.py
├── players.py
├── check_day5.py
├── requirements-dev.txt
├── data/
│   └── players.json
└── tests/
    ├── test_services.py
    └── test_data.py
```

各文件的职责：

- models.py：定义 Player 数据类
- data.py：读取和验证 JSON 数据
- services.py：玩家查询及统计逻辑
- main.py：命令行程序入口
- players.py：兼容早期学习代码的接口
- check_day5.py：Day 5 的断言检查
- tests/：pytest 自动化测试

## 4. 开发环境

要求 Python 3.12。

创建虚拟环境：

```bash
python3.12 -m venv .venv
```

macOS 激活环境：

```bash
source .venv/bin/activate
```

安装开发依赖：

```bash
python -m pip install -r requirements-dev.txt
```

## 5. 运行项目

```bash
python main.py
```

当前模拟数据：

- 玩家总数：5
- 服务器：3 服和 5 服
- 3 服玩家数：3
- 3 服在 2026-10-14 最后登录玩家数：2

## 6. 运行测试

完整自动化测试：

```bash
python -m pytest -q tests/
```

当前预期：

21 passed

兼容性验收：

```bash
python check_day5.py
```

预期：

Day 5: all checks passed!

## 7. 业务接口

services.py 中的主要函数：

- get_players(server_id)
- count_players(server_id)
- get_high_level_players(server_id, min_level)
- get_active_players(server_id, target_date)
- count_active_players(server_id, target_date)

## 8. 数据口径

目前使用的模拟玩家记录只有 last_login。

当 last_login 等于查询日期时，将玩家计入当天的
“最后登录日期匹配玩家”。

这个指标不等于真实的历史 DAU。

真实 DAU 需要依据完整的玩家活跃事件或每日活跃记录统计。

## 9. 安全说明

- 所有玩家数据均为模拟数据
- 不提交 .env 密钥文件
- 不上传真实游戏运营数据
- 目前项目不具备生产级鉴权或数据隔离能力

## 10. 学习进度

- [x] Day 1：Python 环境与 Git
- [x] Day 2：数据结构
- [x] Day 3：函数与类型标注
- [x] Day 4：JSON、日期和异常处理
- [x] Day 5：模块化和数据类
- [x] Day 6：pytest 自动化测试
- [x] Day 7：第一周复习与整理
- [x] Day 8：FastAPI 健康检查
- [x] Day 9：FastAPI 玩家查询 API
- [x] Day 10：Pydantic 玩家响应模型
- [ ] Day 11：FastAPI 查询参数与业务筛选

## 11. 未来目标

实现支持模型调用、知识检索、业务工具调用、
任务状态管理及运营分析的 AI 应用后端服务。

## FastAPI

启动 Web 服务：

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

健康检查接口：

    GET http://127.0.0.1:8000/health

响应：

    {"status": "ok"}

自动生成的 API 文档：

    http://127.0.0.1:8000/docs

运行自动化测试：

    python -m pytest -q tests/

Day 8 预期测试结果：25 passed

## 玩家查询 API

启动服务：

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

查询 3 服玩家：

    GET http://127.0.0.1:8000/servers/3/players

查询 5 服玩家：

    GET http://127.0.0.1:8000/servers/5/players

接口规则：

- server_id 必须是大于等于 1 的整数
- 正常请求返回 JSON 玩家数组
- 当前约定：无玩家返回 []
- 参数校验失败返回 HTTP 422

运行全部测试：

    python -m pytest -q tests/

Day 9 预期：31 passed

## Day 10：Pydantic 响应模型

玩家查询 API：

    GET /servers/{server_id}/players

使用 PlayerResponse 模型定义响应字段：

- player_id：正整数
- name：非空字符串
- server_id：大于等于 1 的整数
- level：非负整数
- last_login：日期

模型位于 app/schemas.py。

原有服务函数与响应 JSON 字段保持不变。

查看 OpenAPI 文档：

    http://127.0.0.1:8000/docs

运行完整测试：

    python -m pytest -q tests/

预期结果：39 passed