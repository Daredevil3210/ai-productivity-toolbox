# AI Productivity Toolbox

English | [简体中文](README.zh.md)

A Chinese-language command-line assistant that turns everyday requests into explicit LangChain tool calls. It combines arithmetic, dates, unit conversion, Open-Meteo weather, and a local to-do list while displaying the tools chosen by the model.

Version `0.1.0` is a learning project aligned with the first five chapters of the 尚硅谷 LangChain 1.2 course. The assistant uses Models, Messages, prompts, and Tools through a hand-written call loop. It does not use `create_agent`, RAG, or a persistent conversation store.

## Tools and behavior

- `calculator`: parses arithmetic with Python's AST, allowing numbers, parentheses, and `+ - * / // % **`; it limits expression length, exponent size, and result magnitude.
- `get_current_datetime`: reads the date and time in an IANA timezone, defaulting to `Asia/Shanghai`.
- `days_between`: calculates the interval between two dates.
- `convert_unit`: converts supported length, weight, and temperature units.
- `get_weather`: queries Open-Meteo for current conditions and a one-to-three-day forecast, with city geocoding.
- `add_todo`, `list_todos`, and `complete_todo`: create, filter, and complete items in local JSON storage.

The assistant can combine several tools in one request and keeps messages in memory for follow-up questions. Tool errors are returned to the model as messages. A configurable round limit stops repeated tool calls.

## Requirements and installation

- Python **3.11 or later**, as declared in `pyproject.toml`.
- A DeepSeek API account, or a running Ollama service with an installed model that supports tool calls.
- Internet access for remote-model requests and Open-Meteo weather.

The dependency file pins LangChain `1.2.12`, its core/provider packages, and supporting libraries. In PowerShell:

```powershell
git clone https://github.com/Daredevil3210/ai-productivity-toolbox.git
cd ai-productivity-toolbox
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Copy the template only for initial setup; preserve an existing `.env` during updates. You can also activate an existing Conda environment and install `requirements.txt` from the repository root.

## Model configuration

Edit the local `.env`:

```dotenv
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-v4-flash
MODEL_API_KEY=replace_with_your_private_key
MODEL_BASE_URL=https://api.deepseek.com
MAX_TOOL_ROUNDS=6
SHOW_TOOL_TRACE=true
```

`deepseek-v4-flash` is the configured identifier in the repository template, not a guarantee of availability. Select a model your account can access that supports tool calls. `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL` are accepted as fallback names. Settings are loaded from the project-root `.env` with precedence over existing environment values.

To use Ollama, replace the model settings with:

```dotenv
MODEL_PROVIDER=ollama
MODEL_NAME=replace_with_your_installed_tool_capable_model
MODEL_BASE_URL=http://localhost:11434
MAX_TOOL_ROUNDS=6
SHOW_TOOL_TRACE=true
```

Ollama must already be running and the selected model must produce actual tool calls; installing a local model does not by itself establish that capability. `MAX_TOOL_ROUNDS` accepts values from 1 to 20. If the limit is reached, inspect the tool trace and model behavior before increasing it.

## Run

```powershell
python main.py
python main.py -q "计算 (123.5 + 20) * 3"
python main.py --no-tool-trace
```

Interactive commands:

- `/help`: show help.
- `/tools`: list registered tools.
- `/clear`: reset the current in-memory conversation.
- `/exit`: quit.

The interface and system instructions are Chinese. Try:

```text
把 2.5 千米换算成米
现在上海是星期几、几点？
查询杭州未来三天的天气
添加一个高优先级待办：复习 LangChain Tools，然后列出未完成事项
现在上海几点？顺便把 10 英里换算成千米
```

## Local data and optional tracing

To-do items are stored in `data/todos.json`, created when needed. `TOOLBOX_DATA_DIR` can override the storage directory. `/clear` resets model messages only; it does not delete saved to-do items. This is local file storage, without a multi-user service or account separation.

The model receives prompts and tool results. You can optionally enable LangSmith in `.env` to inspect messages, schemas, tool calls, and final responses:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=replace_with_your_private_key
LANGSMITH_PROJECT=ai-productivity-toolbox
```

Tracing can upload conversation and tool data. Keep real keys and `.env` local; the template contains placeholders only.

## Project structure

```text
ai-productivity-toolbox/
├── main.py                    # CLI and interactive commands
├── toolbox/
│   ├── assistant.py           # Model setup and manual tool loop
│   ├── config.py              # Environment loading and validation
│   ├── prompts.py             # Chinese system prompt
│   └── tools.py               # Tools, input schemas, local storage
├── data/                      # Runtime to-do storage
├── tests/                     # Configuration, tools, assistant loop
├── docs/PROJECT_GUIDE.md       # Detailed Chinese design/source guide
├── .env.example
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## Provided checks

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

The tests cover calculator restrictions, dates, unit conversion, weather response handling, the to-do lifecycle, model configuration, and the manual tool loop. Weather calls and model responses are mocked; to-do tests use temporary directories and test tracing is disabled. This documentation update did not run tests or make live API calls.

## Troubleshooting and current limits

- Missing key: check `MODEL_API_KEY` or `DEEPSEEK_API_KEY` in the root `.env`, then restart.
- Weather failure: Open-Meteo requires network access but no weather key. Timeouts and network errors are retried up to three attempts, then returned as a tool error.
- Ollama connection failure: check that the service is running and `MODEL_BASE_URL` points to it. The default local address is `http://localhost:11434`.
- Repeated calls or incorrect parameters: inspect the trace, tool descriptions, and chosen model. A successful local unit test does not establish live model reliability.
- Conversation history ends with the process. File-backed to-do storage is separate from model memory; RAG, persistent chat memory, and a web interface are not implemented.

## Learning context and license

See the [project guide](docs/PROJECT_GUIDE.md) for the full message flow, source walkthrough, and follow-on exercises from the LangChain course. The project retains the [MIT License](LICENSE) and `AI Productivity Toolbox contributors` copyright notice.
