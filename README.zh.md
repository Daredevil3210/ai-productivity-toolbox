# AI 个人效率工具箱

[English](README.md) | 简体中文

中文命令行助手，将日常问题转为明确的 LangChain 工具调用。项目组合数学计算、日期、单位换算、Open-Meteo 天气和本地待办事项，并在终端显示模型选择的工具。

当前 `0.1.0` 版本是与尚硅谷 LangChain 1.2 课程前五章对应的学习项目，使用 Models、Messages、提示词和 Tools 手写调用循环，不依赖 `create_agent`、RAG 或持久化对话存储。

## 工具与行为

- `calculator`：通过 Python AST 解析数字、括号及 `+ - * / // % **` 运算，限制表达式长度、指数与结果大小。
- `get_current_datetime`：读取指定 IANA 时区的日期时间，默认 `Asia/Shanghai`。
- `days_between`：计算两个日期之间的间隔。
- `convert_unit`：换算支持的长度、重量和温度单位。
- `get_weather`：通过城市地理编码调用 Open-Meteo，返回当前天气及一至三天预报。
- `add_todo`、`list_todos`、`complete_todo`：在本地 JSON 中新增、筛选和完成待办。

助手能在同一请求中组合多个工具，当前进程保留消息以支持追问。工具错误会作为消息交给模型，最大轮数配置用于停止重复调用。

## 环境与安装

- Python **3.11 或更高版本**，见 `pyproject.toml`。
- DeepSeek API 账号，或已启动并安装了工具调用模型的 Ollama 服务。
- 使用远程模型及 Open-Meteo 时需要联网。

依赖文件固定了 LangChain `1.2.12`、核心及模型适配包和配套库。以下命令在 PowerShell 中执行：

```powershell
git clone https://github.com/Daredevil3210/ai-productivity-toolbox.git
cd ai-productivity-toolbox
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

复制模板仅用于首次配置，更新时保留已有 `.env`。也可激活现有 Conda 环境，在仓库根目录安装 `requirements.txt`。

## 模型配置

编辑本地 `.env`：

```dotenv
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-v4-flash
MODEL_API_KEY=replace_with_your_private_key
MODEL_BASE_URL=https://api.deepseek.com
MAX_TOOL_ROUNDS=6
SHOW_TOOL_TRACE=true
```

`deepseek-v4-flash` 是模板配置的标识，不代表可用性保证。请选择账号可访问且支持工具调用的模型。程序兼容 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 作为后备名称。根目录 `.env` 的值会覆盖已有环境变量。

使用 Ollama 时，替换模型配置为：

```dotenv
MODEL_PROVIDER=ollama
MODEL_NAME=replace_with_your_installed_tool_capable_model
MODEL_BASE_URL=http://localhost:11434
MAX_TOOL_ROUNDS=6
SHOW_TOOL_TRACE=true
```

Ollama 服务需已启动，所选模型需真正产生工具调用，安装本地模型本身不代表具备该能力。`MAX_TOOL_ROUNDS` 允许 1 至 20；触达上限时，应先检查轨迹和模型行为，再决定是否增加。

## 运行

```powershell
python main.py
python main.py -q "计算 (123.5 + 20) * 3"
python main.py --no-tool-trace
```

交互命令：

- `/help`：查看帮助。
- `/tools`：列出注册工具。
- `/clear`：重置本次内存对话。
- `/exit`：退出。

界面和系统提示词使用中文。可尝试：

```text
把 2.5 千米换算成米
现在上海是星期几、几点？
查询杭州未来三天的天气
添加一个高优先级待办：复习 LangChain Tools，然后列出未完成事项
现在上海几点？顺便把 10 英里换算成千米
```

## 本地数据与可选追踪

待办数据保存在按需创建的 `data/todos.json`，可用 `TOOLBOX_DATA_DIR` 覆盖存储目录。`/clear` 只清空模型消息，不删除已保存待办。这是本地文件存储，没有多用户服务或账号隔离。

模型会接收提示词与工具结果。可在 `.env` 中启用 LangSmith，查看消息、Schema、工具调用和最终回答：

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=replace_with_your_private_key
LANGSMITH_PROJECT=ai-productivity-toolbox
```

追踪可能上传对话及工具数据。真实密钥和 `.env` 保留在本地，公开模板只使用占位符。

## 项目结构

```text
ai-productivity-toolbox/
├── main.py                    # CLI 和交互命令
├── toolbox/
│   ├── assistant.py           # 模型初始化及手写工具循环
│   ├── config.py              # 配置读取与校验
│   ├── prompts.py             # 中文系统提示词
│   └── tools.py               # 工具、输入 Schema 和本地存储
├── data/                      # 运行时待办存储
├── tests/                     # 配置、工具和助手循环测试
├── docs/PROJECT_GUIDE.md       # 详细设计与源码导读
├── .env.example
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## 提供的检查

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

测试覆盖计算器限制、日期、单位换算、天气响应、待办生命周期、模型配置与手写工具循环。天气请求与模型响应使用模拟实现，待办测试使用临时目录，并关闭测试追踪。本次文档更新未运行测试或调用真实 API。

## 排查与当前限制

- 缺少密钥：检查根目录 `.env` 的 `MODEL_API_KEY` 或 `DEEPSEEK_API_KEY`，修改后重启。
- 天气失败：Open-Meteo 无需天气密钥，但需要联网。超时和网络错误最多尝试三次，之后返回工具错误。
- Ollama 连接失败：检查服务已启动且 `MODEL_BASE_URL` 指向正确地址，默认本地地址为 `http://localhost:11434`。
- 重复调用或参数错误：检查轨迹、工具描述和所选模型。本地单元测试通过不代表真实模型可靠性。
- 对话历史随进程结束而消失。文件待办存储与模型记忆相互独立；RAG、持久化对话和 Web 界面尚未实现。

## 学习背景与许可

完整消息流程、源码导读及课程后续练习见 [项目指南](docs/PROJECT_GUIDE.md)。仓库保留 [MIT License](LICENSE) 和 `AI Productivity Toolbox contributors` 版权声明。
