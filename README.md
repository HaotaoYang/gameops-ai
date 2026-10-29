
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
- [x] Day 9：路径参数与玩家查询
- [x] Day 10：Pydantic 响应模型
- [x] Day 11：等级查询参数
- [x] Day 12：日期与组合筛选
- [x] Day 13：分页
- [x] Day 14：第二周 FastAPI 阶段验收
- [x] Day 15：首次调用大模型 API
- [x] Day 16：Prompt 基础与模型请求控制
- [x] Day 17：上下文与多轮消息组织
- [ ] Day 18：下一阶段内容，待开始

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


## Day 11：玩家等级筛选

### 接口

GET /servers/{server_id}/players

### 可选查询参数

min_level：最低玩家等级。

要求：
- 必须是整数
- 必须 >= 0
- 不提供时，不执行等级筛选

### 示例

GET /servers/3/players?min_level=50

返回 Alice 和 David。

GET /servers/3/players?min_level=60

只返回 David。

GET /servers/3/players?min_level=61

返回空数组 []。

### 错误处理

min_level=-1：HTTP 422

min_level=abc：HTTP 422

### 自动化测试

python -m pytest -q tests/

Day 11 预期：47 passed

## Day 12：多条件玩家查询

现有玩家 API：

GET /servers/{server_id}/players

支持的可选查询参数：

- min_level：最低玩家等级，非负整数
- login_date：最后登录日期，使用 YYYY-MM-DD 格式

示例：

GET /servers/3/players

返回 Alice、Bob、David。

GET /servers/3/players?min_level=50

返回 Alice、David。

GET /servers/3/players?login_date=2026-10-14

返回 Bob、David。

GET /servers/3/players?min_level=50&login_date=2026-10-14

只返回 David。

说明：

- 两个条件同时提供时使用 AND 逻辑
- 条件合法但无结果时返回 HTTP 200 和 []
- 参数格式错误时返回 HTTP 422
- login_date 表示最后登录日期匹配，不等于历史 DAU
- 响应继续使用 PlayerResponse Pydantic 模型

测试命令：

python -m pytest -q tests/

Day 12 预期：57 passed

## Day 13：玩家查询分页

接口：

GET /servers/{server_id}/players

支持可选参数：

- min_level：最低玩家等级，必须 >= 0
- login_date：最后登录日期
- limit：最多返回多少条，范围 1～100
- offset：跳过多少条，必须 >= 0，默认 0

分页规则：

1. 先根据服务器、等级和日期筛选
2. 再根据 offset 和 limit 截取结果
3. 最后使用 PlayerResponse 验证并序列化

示例：

GET /servers/3/players?limit=2

返回 Alice、Bob。

GET /servers/3/players?limit=2&offset=1

返回 Bob、David。

GET /servers/3/players?min_level=50&limit=1&offset=1

返回 David。

兼容性：

- 不提供 limit 时，不限制结果数量
- 不提供 offset 时，默认从第一条开始
- 筛选后无结果返回 200 和 []
- 非法分页参数返回 HTTP 422

测试：

python -m pytest -q tests/

Day 13 预期：67 passed

## Day 14：FastAPI 第二周阶段验收

### 已实现接口

1. GET /health
2. GET /servers/{server_id}/players

### 玩家查询参数

- server_id：必填整数，必须 >= 1
- min_level：可选整数，必须 >= 0
- login_date：可选日期，YYYY-MM-DD
- limit：可选整数，范围 1～100
- offset：非负整数，默认 0

### 查询规则

1. 根据服务器选择玩家
2. 根据等级与日期条件筛选
3. 先筛选，再分页
4. 使用 PlayerResponse 验证响应
5. 转换为 JSON 返回客户端

无结果时返回 HTTP 200 和空数组 []。

非法参数返回 HTTP 422。

### 启动服务

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

### 接口文档

http://127.0.0.1:8000/docs

### 自动化测试

完整回归：

python -m pytest -q tests/

第二周阶段验收：

python -m pytest -q tests/test_week2_review.py

Day 14 预期测试结果：

75 passed

### 当前工程限制

- 使用模拟 JSON 数据
- 使用同步业务查询
- 使用内存分页
- 尚未实现鉴权、持久化数据库与生产监控
- 尚未接入大模型

### 下一阶段

Day 15 开始学习大模型 API 调用。

## Day 15：大模型 API 基础

新增模块：

- app/llm.py：封装模型请求
- llm_day15.py：模型调用示例
- tests/test_llm.py：离线模型调用测试

### 开发依赖

python -m pip install -r requirements-dev.txt

### 配置 API Key

复制 .env.example 为 .env，并设置：

OPENAI_API_KEY=自己的APIKey
OPENAI_MODEL=gpt-5.4-mini

不要将真实密钥提交到 Git。

### 调用大模型

python llm_day15.py

### 自动化测试

python -m pytest -q tests/

Day 15 预期：80 passed

### 说明

- 当前通过 OpenAI Responses API 调用模型
- 自动化测试使用 Mock，不依赖真实 API
- 真实模型调用可能产生额外费用
- 尚未实现对话上下文、流式输出和 Function Calling

## Day 16：Prompt 基础与模型请求控制

### 新增模块

- app/prompts.py：游戏运营分析提示词及输入模板
- prompt_day16.py：结合现有业务数据调用模型
- tests/test_prompts.py：Prompt 和请求控制离线测试

### 核心设计

1. instructions 描述应用行为规则
2. input 提供本次问题和业务数据
3. 统计数据由 services.py 生成
4. 数据不合理时先由 Python 抛出异常
5. 缺少证据时要求模型说明数据不足
6. Prompt 约束不替代程序校验和权限控制

### 运行演示

python prompt_day16.py

注意：执行演示会调用真实大模型 API，可能产生费用。

### 自动化测试

python -m pytest -q tests/test_prompts.py

python -m pytest -q tests/

Day 16 预期：86 passed

### 当前限制

- 尚未实现结构化输出
- 尚未实现模型质量评测
- 尚未实现自动 Function Calling
- 尚未实现 RAG

## Day 17：大模型上下文与消息组织

新增文件：

- app/conversation.py：多轮对话状态管理
- conversation_day17.py：两轮真实对话演示
- tests/test_conversation.py：离线上下文测试

核心功能：

- 使用 role/content 组织消息
- 将历史消息与最新问题一起提交 Responses API
- 独立保存每个 ChatSession 的对话
- 仅在模型请求成功后保存一轮历史
- 支持查看和清空消息历史

运行演示：

python conversation_day17.py

注意：演示会执行两次真实 API 调用，可能产生费用。

运行测试：

python -m pytest -q tests/test_conversation.py
python -m pytest -q tests/

Day 17 预期：92 passed

限制：

- 历史只保存在当前 Python 进程内存
- 未做上下文截断或 Token 预算
- 尚未实现数据库或 Redis 持久化
- 不支持多用户并发会话管理

## Day 18：结构化输出与 Pydantic

新增文件：

- app/report_schemas.py：结构化游戏运营报告模型
- app/structured_llm.py：Responses API 结构化调用
- structured_day18.py：真实结构化报告演示
- tests/test_structured_llm.py：离线测试

核心知识：

- JSON 是数据格式
- Pydantic 负责模型验证
- Responses API 的 parse() 支持结构化输出
- output_parsed 可以直接获取解析后的模型对象
- 结构正确不等于业务事实正确

真实演示：

python structured_day18.py

离线测试：

python -m pytest -q tests/test_structured_llm.py

完整回归目标：98 passed

当前限制：

- 尚未实现完整的模型输出质量评测
- 尚未实现流式输出
- 尚未将结构化报告接入 FastAPI
- 尚未实现 Function Calling

## Day 19：Streaming 流式输出

新增：

- app/streaming_llm.py
- streaming_day19.py
- tests/test_streaming_llm.py

核心能力：

- 使用 Responses API 的 stream=True
- 处理 response.output_text.delta
- 通过 Python yield 逐段返回文本
- 处理 completed、failed、incomplete 等事件
- 正确关闭流式连接
- 拼接文本片段生成完整回答

真实演示：

python streaming_day19.py

离线测试：

python -m pytest -q tests/test_streaming_llm.py

完整回归目标：106 passed

当前限制：

- 尚未接入 FastAPI StreamingResponse
- 尚未实现多轮对话流式输出
- 尚未实现实时 Token 用量展示
- 尚未实现断线恢复和自动重试
- 流式文本不等于经过业务校验的正式报告

## Day 21：第三周 AI 应用综合复习与验收

### 已完成能力

- Day 15：Responses API 普通调用
- Day 16：Prompt 与 instructions
- Day 17：多轮上下文管理
- Day 18：Pydantic 结构化输出
- Day 19：Streaming 流式响应
- Day 20：模型业务语义评测
- Day 21：跨模块综合回归测试

### 新增测试

tests/test_week3_review.py

共8项综合测试，覆盖：

1. 业务统计正确性
2. Prompt字段语义
3. 普通模型调用契约
4. 多轮会话上下文
5. Pydantic结构化输出
6. Streaming事件处理
7. 历史业务错误评测
8. 业务数据到模型评测的完整离线流程

### 运行测试

python -m pytest -q tests/test_week3_review.py
python -m pytest -q tests/

Day 21 完整回归目标：122 passed

### 阶段总结

现有gameops-ai已经具备基础AI应用后端能力。

当前仍然是教学项目，尚未完成：

- 模型自主选择业务工具
- Function Calling执行循环
- RAG与向量数据库
- 会话持久化
- 多用户并发状态管理
- 生产环境鉴权与权限管理
- 完整模型质量评测体系

下一阶段将学习Function Calling和Agent工具调用。