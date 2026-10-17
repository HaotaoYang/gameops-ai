# GameOps AI Agent

一个用于学习 AI 应用开发的游戏运营智能分析项目。

## 技术背景

- 原有技术：Erlang / OTP
- 新学习语言：Python 3.12
- 学习目标：AI Application Backend / AI Agent

## 最终功能

1. 查询游戏玩家数据
2. 查询服务器统计数据
3. 查询游戏活动配置
4. 使用 RAG 检索游戏规则
5. 使用 AI Agent 分析运营数据
6. 生成有数据依据的分析报告

## 开发环境

- macOS
- Python 3.12
- Git
- VS Code

## 运行方式

创建并激活虚拟环境：

    python3.12 -m venv .venv
    source .venv/bin/activate

## 自动化测试

安装测试依赖：

    python -m pip install -r requirements-dev.txt

运行所有测试：

    python -m pytest -q tests/

运行 Day 5 的旧验收：

    python check_day5.py

当前自动化测试数量：21

## 学习进度

- [x] Day 1：Python 环境与 Git
- [x] Day 2：Python 数据结构
- [x] Day 3：函数与类型标注
- [x] Day 4：JSON、日期与异常处理
- [x] Day 5：模块化与数据类
- [x] Day 6：pytest 自动化测试
- [ ] Day 7：第一周代码复习与整理
