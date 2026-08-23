# AI 个人效率工具箱：项目整体与详细说明

## 1. 项目目标

本项目的目标不是提前使用 LangChain Agent，而是把课程前五章知识连接成一个完整应用：

1. 使用 `init_chat_model()` 初始化 DeepSeek 或 Ollama 模型。
2. 使用 `SystemMessage` 和 `HumanMessage` 构造上下文。
3. 使用 `@tool` 和 Pydantic 描述工具名称、用途与参数。
4. 使用 `model.bind_tools()` 将工具 Schema 提供给模型。
5. 读取模型返回的 `AIMessage.tool_calls`。
6. 由程序查找并执行对应工具。
7. 将工具结果作为 `ToolMessage` 放回消息列表。
8. 再次调用模型，让模型根据真实工具结果回答用户。

这正是 Agent 内部最核心的循环。手写一次之后，后面学习 `create_agent()` 时会更容易理解框架替你完成了什么。

## 2. 整体架构

```text
用户输入
   |
   v
main.py（命令行界面）
   |
   v
ProductivityAssistant.ask()
   |
   v
绑定工具后的聊天模型 model_with_tools
   |
   +-- 不需要工具 --> AIMessage.content --> 返回用户
   |
   +-- 需要工具 --> AIMessage.tool_calls
                         |
                         v
                  TOOL_MAP 查找工具
                         |
                         v
                    tool.invoke()
                         |
                         v
                     ToolMessage
                         |
                         +---- 放回 messages，继续调用模型
```

## 3. 每个文件的职责

### `main.py`

只负责用户界面：

- 读取命令行参数
- 创建配置和助手
- 接收用户问题
- 显示工具调用轨迹
- 处理 `/tools`、`/clear`、`/exit`

业务逻辑不放在这里，避免命令行代码和 LangChain 代码耦合。

### `toolbox/config.py`

负责加载 `.env` 并验证配置。它支持：

- `deepseek`
- `ollama`
- 最大工具轮数
- 是否显示工具轨迹

使用 `load_dotenv(override=True)`，因此项目目录 `.env` 中的值会覆盖当前进程中已有的同名环境变量。这与课程 notebook 的约定一致。

### `toolbox/prompts.py`

保存 System Prompt。它明确告诉模型：

- 事实性任务应调用工具
- 可以一次调用多个工具
- 工具失败时不能伪造答案
- 最终回复不应直接倾倒原始 JSON

工具描述决定“模型是否知道该调用谁”，System Prompt 决定“模型整体上应该如何工作”。

### `toolbox/tools.py`

包含全部工具和 Pydantic `args_schema`。

每个工具遵循以下原则：

- 功能单一
- 名称明确
- 参数有类型、范围和描述
- 返回字符串
- 错误也转换成字符串
- 不把异常直接泄漏到整个会话

文件底部维护：

```python
TOOLS = [...]
TOOL_MAP = {item.name: item for item in TOOLS}
```

`TOOLS` 用于绑定模型，`TOOL_MAP` 用于根据模型返回的工具名称快速找到 Python 工具，避免写很长的 `if/elif`。

### `toolbox/assistant.py`

这是项目核心，包含手动工具循环。

逻辑可以简化理解为：

```python
while 没有超过最大轮数:
    response = model_with_tools.invoke(messages)
    messages.append(response)

    if response.tool_calls 为空:
        return response.content

    for tool_call in response.tool_calls:
        tool = TOOL_MAP[tool_call["name"]]
        tool_message = tool.invoke(tool_call)
        messages.append(tool_message)
```

真实代码额外处理了：

- 未注册工具
- 工具执行异常
- 空回答
- 最大循环轮数
- 工具轨迹记录
- 不同模型可能返回的多段 content

## 4. 工具详细说明

### 4.1 `calculator`

支持：

```text
+ - * / // % ** 和括号
```

没有使用危险的 `eval()`，而是通过 Python AST 只允许数字和指定运算符。因此下面的代码不会被执行：

```text
__import__('os').system(...)
```

同时限制表达式长度、指数大小和结果大小。

### 4.2 `get_current_datetime`

使用标准库 `zoneinfo` 查询时区，Windows 上通过 `tzdata` 提供时区数据库。

输入：

```json
{"timezone": "Asia/Shanghai"}
```

输出包含 ISO 时间、日期、时间和中文星期。

### 4.3 `days_between`

Pydantic 会把模型传入的 `YYYY-MM-DD` 自动解析为 `date`。工具返回带符号天数和绝对天数，模型可根据用户语义选择表达方式。

### 4.4 `convert_unit`

支持：

- 长度：`mm`、`cm`、`m`、`km`、`inch`、`foot`、`mile`
- 重量：`g`、`kg`、`lb`
- 温度：`celsius`、`fahrenheit`、`kelvin`

参数使用 `Literal`，模型只能从允许的单位中选择。工具还会阻止“千克转米”这类不同维度换算。

### 4.5 `get_weather`

调用过程：

1. 使用 Open-Meteo Geocoding API 将城市名解析为经纬度。
2. 使用 Forecast API 查询实时天气与未来预报。
3. 将 WMO 天气代码转换为中文。
4. 返回干净的 JSON 字符串。

网络超时会通过 Tenacity 最多尝试三次。API 不需要申请 Key。

### 4.6 待办工具

包含：

```text
add_todo
list_todos
complete_todo
```

数据存储在 `data/todos.json`。写入时先生成临时文件，再原子替换正式文件，降低写到一半导致 JSON 损坏的概率。

待办只属于当前项目，不会读取或修改系统日历、邮件或其他应用。

## 5. 一次完整工具调用示例

用户输入：

```text
查询杭州未来两天天气，并计算今天到 2026-10-01 还有多少天
```

可能发生的消息流转：

```text
SystemMessage：定义助手规则
HumanMessage：用户问题
AIMessage：
  tool_calls = [
    get_weather(city="杭州", forecast_days=2),
    get_current_datetime(timezone="Asia/Shanghai")
  ]
ToolMessage：杭州天气结果
ToolMessage：当前日期结果
AIMessage：
  tool_calls = [days_between(start_date="...", end_date="2026-10-01")]
ToolMessage：日期差结果
AIMessage：综合天气和剩余天数，生成最终回答
```

这说明多工具调用不一定只发生在一轮。模型可以根据第一轮工具结果继续决定下一步，所以必须使用循环，而不能只写一次 `if response.tool_calls`。

## 6. 为什么设置最大工具轮数

如果工具描述不清晰、小模型能力有限或工具持续失败，模型可能重复调用同一工具。项目默认最多执行六轮：

```env
MAX_TOOL_ROUNDS=6
```

达到上限后停止，避免无限请求消耗 Token 或占用本地资源。

## 7. 错误处理设计

项目采用三层错误边界：

1. 工具参数层：Pydantic 拒绝非法类型、枚举和范围。
2. 工具实现层：预期内错误转换为包含 `error` 的字符串。
3. 工具循环层：未预料的异常转换成 `ToolMessage`，让模型向用户解释。

模型接口自身失败仍会交给 `main.py` 显示，因为 API Key 错误、额度不足或模型服务不可用不能靠工具内部修复。

## 8. 如何调试模型选错工具

按以下顺序检查：

1. 执行 `/tools`，确认工具已注册。
2. 检查工具名称和 description 是否准确。
3. 检查 Pydantic 字段 description 是否给了明确格式和示例。
4. 查看终端工具轨迹。
5. 开启 LangSmith，查看模型实际收到的 Tool Schema。
6. 使用更明确的问题复现，并判断是工具描述问题还是模型能力问题。

不要直接把 `tool_choice` 永久设为 `required`，否则普通聊天也会被迫调用工具。当前项目使用默认的 `auto`。

## 9. 与后续课程衔接

学完第 06 章“结构化输出”后：

- 给最终回答增加固定的数据模型
- 让天气或待办摘要输出稳定字段

学完第 07 章“智能体”后：

- 使用 `create_agent()` 重构 `ProductivityAssistant.ask()`
- 比较 Agent 自动循环与当前手写循环

学完第 08 章“中间件”后：

- 增加工具权限检查
- 增加调用日志和敏感操作确认

学完第 09 章“上下文与记忆”后：

- 保存跨进程会话历史
- 为不同用户隔离待办和偏好

学完第 10 章“RAG”后：

- 增加课程资料检索工具
- 让助手基于本地讲义回答学习问题

## 10. 推荐练习任务

在不参考答案的情况下尝试完成：

1. 新增 `delete_todo`，要求必须传入待办 ID。
2. 新增 `update_todo`，支持修改标题、截止日期或优先级。
3. 为待办增加 `overdue` 状态判断。
4. 为天气工具增加穿衣建议，但必须根据工具数据生成，不能写死城市。
5. 新增人民币、美元、欧元汇率工具，并处理接口失败。
6. 使用 LangSmith 比较 DeepSeek 在线模型和 Ollama 1.5B 模型的工具选择准确率。
