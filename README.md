# AI 个人效率工具箱

这是一个与《尚硅谷 LangChain 1.2》前五章学习进度匹配的综合练习项目。它使用模型、Message、提示词、Tools 和手动工具调用循环实现，不依赖 `create_agent`、记忆或 RAG。

项目可以完成以下任务：

- 安全计算数学表达式
- 查询指定时区的日期和时间
- 计算两个日期相差多少天
- 换算长度、重量和温度单位
- 查询实时天气及三日内预报
- 新增、查看和完成本地待办事项
- 在一个问题中自动组合多个工具

详细的设计说明、调用流程和源码导读见 [docs/PROJECT_GUIDE.md](docs/PROJECT_GUIDE.md)。

## 1. 项目结构

```text
project1/
├── main.py                    # 命令行入口
├── toolbox/
│   ├── __init__.py
│   ├── assistant.py           # 手动工具调用循环
│   ├── config.py              # .env 配置读取与校验
│   ├── prompts.py             # System Prompt
│   └── tools.py               # 所有工具及 args_schema
├── data/
│   └── .gitkeep               # todos.json 运行后自动产生
├── tests/
│   ├── test_config.py
│   └── test_tools.py
├── docs/
│   └── PROJECT_GUIDE.md       # 整体与详细说明
├── .env.example
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## 2. 环境准备

推荐使用你现有的 Conda 环境：

```cmd
conda activate langchain1.2
cd /d D:\Project\project1
pip install -r requirements.txt
```

如果不使用 Conda，也可以建立独立虚拟环境：

```cmd
cd /d D:\Project\project1
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## 3. 配置模型

先复制环境变量模板：

```cmd
copy .env.example .env
```

### 3.1 使用 DeepSeek

编辑 `.env`：

```env
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-v4-flash
MODEL_API_KEY=你的API_KEY
MODEL_BASE_URL=https://api.deepseek.com
```

也可以继续使用课程项目中的变量名：

```env
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-v4-flash
DEEPSEEK_API_KEY=你的API_KEY
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

不要把真实 `.env` 提交到 Git。项目的 `.gitignore` 已忽略该文件。

### 3.2 使用 Ollama

确认本地服务和模型可用：

```cmd
D:\ollama\ollama.exe list
D:\ollama\ollama.exe run deepseek-r1:1.5b
```

然后将 `.env` 改为：

```env
MODEL_PROVIDER=ollama
MODEL_NAME=deepseek-r1:1.5b
MODEL_BASE_URL=http://localhost:11434
MAX_TOOL_ROUNDS=6
SHOW_TOOL_TRACE=true
```

本地小模型的工具选择能力通常弱于较大的在线模型。如果出现工具参数不稳定，优先使用 DeepSeek 在线模型完成学习和调试。

## 4. 启动项目

进入交互模式：

```cmd
python main.py
```

只提问一次：

```cmd
python main.py -q "计算 (123.5 + 20) * 3"
```

隐藏工具调用轨迹：

```cmd
python main.py --no-tool-trace
```

## 5. 推荐测试问题

### 单工具调用

```text
计算 (125.6 + 74.4) * 3
把 2.5 千米换算成米
2026-08-21 到 2026-10-01 相差多少天？
现在上海是星期几、几点？
查询杭州未来三天的天气
```

### 待办事项

```text
添加一个高优先级待办：8月30日前完成 LangChain Tools 复习
列出我的未完成待办
把 1 号待办标记为完成
显示全部待办
```

待办数据保存在：

```text
data/todos.json
```

### 多工具调用

```text
查询杭州天气，并计算今天到 2026 年国庆节还有多少天
添加一个明天到期的高优先级待办“复习 Tools”，然后列出未完成事项
现在上海几点？顺便把 10 英里换算成千米
```

## 6. 交互命令

```text
/help   查看帮助
/tools  查看所有已注册工具
/clear  清空当前进程中的对话上下文
/exit   退出
```

`/clear` 只清空模型消息列表，不会删除 `data/todos.json`。

## 7. 运行测试

安装开发依赖：

```cmd
pip install -r requirements-dev.txt
```

运行测试：

```cmd
pytest
```

测试不会访问大模型，也不会调用真实天气网络接口。待办测试使用 pytest 临时目录，不会污染正式数据。

## 8. LangSmith 追踪

在 `.env` 中启用：

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的LANGSMITH_API_KEY
LANGSMITH_PROJECT=ai-productivity-toolbox
```

运行项目后，可在 LangSmith 中观察：

- 模型收到的 SystemMessage 和 HumanMessage
- 工具 Schema
- 模型生成的 `tool_calls`
- 工具返回的 `ToolMessage`
- 最终模型回答

## 9. 常见问题

### 配置错误：必须设置 API Key

确认 `.env` 位于项目根目录，并填写了：

```env
MODEL_API_KEY=...
```

或者：

```env
DEEPSEEK_API_KEY=...
```

### 天气查询失败

天气工具调用 Open-Meteo 公共 API，不需要 Key，但需要能访问互联网。网络异常时工具会重试三次，然后将错误作为字符串交给模型，不会让整个工具循环崩溃。

### 模型一直调用工具

项目通过 `MAX_TOOL_ROUNDS` 限制最大轮数，默认 6。不要为了“解决”循环而把它设得很大，应使用 LangSmith 检查工具描述和模型返回参数。

### Ollama 连接失败

检查：

```cmd
D:\ollama\ollama.exe list
curl http://localhost:11434/api/tags
```

并确认 `.env` 中的地址为：

```env
MODEL_BASE_URL=http://localhost:11434
```
