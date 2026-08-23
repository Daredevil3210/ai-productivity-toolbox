from __future__ import annotations

import ast
import json
import math
import operator
import os
from datetime import date, datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _evaluate_ast(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate_ast(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in {int, float}:
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_ast(node.left)
        right = _evaluate_ast(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("指数绝对值不能超过 100。")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if not math.isfinite(float(result)) or abs(result) > 1e100:
            raise ValueError("计算结果过大。")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_ast(node.operand))
    raise ValueError("表达式包含不允许的名称、函数或运算。")


def safe_calculate(expression: str) -> int | float:
    expression = expression.strip()
    if not expression:
        raise ValueError("表达式不能为空。")
    if len(expression) > 200:
        raise ValueError("表达式过长。")
    tree = ast.parse(expression, mode="eval")
    return _evaluate_ast(tree)


class CalculatorInput(BaseModel):
    expression: str = Field(
        description="只包含数字、括号和 + - * / // % ** 的数学表达式，例如 (12+3)*4"
    )


@tool(args_schema=CalculatorInput)
def calculator(expression: str) -> str:
    """安全计算数学表达式，不执行任意 Python 代码。"""
    try:
        result = safe_calculate(expression)
        return _json_text({"expression": expression, "result": result})
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError) as exc:
        return _json_text({"error": f"计算失败：{exc}"})


# ---------------------------------------------------------------------------
# Date and time
# ---------------------------------------------------------------------------


class CurrentDateTimeInput(BaseModel):
    timezone: str = Field(
        default="Asia/Shanghai",
        description="IANA 时区名称，例如 Asia/Shanghai、UTC、America/New_York",
    )


@tool(args_schema=CurrentDateTimeInput)
def get_current_datetime(timezone: str = "Asia/Shanghai") -> str:
    """查询指定时区的当前日期、时间和星期。"""
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        return _json_text({"error": f"未知时区：{timezone}"})

    weekdays = "一二三四五六日"
    return _json_text(
        {
            "timezone": timezone,
            "iso_datetime": now.isoformat(timespec="seconds"),
            "date": now.date().isoformat(),
            "time": now.strftime("%H:%M:%S"),
            "weekday": f"星期{weekdays[now.weekday()]}",
        }
    )


class DaysBetweenInput(BaseModel):
    start_date: date = Field(description="开始日期，格式 YYYY-MM-DD")
    end_date: date = Field(description="结束日期，格式 YYYY-MM-DD")


@tool(args_schema=DaysBetweenInput)
def days_between(start_date: date, end_date: date) -> str:
    """计算两个日期之间相差的天数。"""
    difference = (end_date - start_date).days
    return _json_text(
        {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "signed_days": difference,
            "absolute_days": abs(difference),
        }
    )


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------

UnitName = Literal[
    "mm",
    "cm",
    "m",
    "km",
    "inch",
    "foot",
    "mile",
    "g",
    "kg",
    "lb",
    "celsius",
    "fahrenheit",
    "kelvin",
]

_LINEAR_UNITS = {
    "mm": ("length", 0.001),
    "cm": ("length", 0.01),
    "m": ("length", 1.0),
    "km": ("length", 1000.0),
    "inch": ("length", 0.0254),
    "foot": ("length", 0.3048),
    "mile": ("length", 1609.344),
    "g": ("mass", 0.001),
    "kg": ("mass", 1.0),
    "lb": ("mass", 0.45359237),
}
_TEMPERATURE_UNITS = {"celsius", "fahrenheit", "kelvin"}


def convert_value(value: float, from_unit: str, to_unit: str) -> float:
    if from_unit == to_unit:
        return value
    if from_unit in _TEMPERATURE_UNITS and to_unit in _TEMPERATURE_UNITS:
        if from_unit == "celsius":
            celsius = value
        elif from_unit == "fahrenheit":
            celsius = (value - 32) * 5 / 9
        else:
            celsius = value - 273.15

        if to_unit == "celsius":
            return celsius
        if to_unit == "fahrenheit":
            return celsius * 9 / 5 + 32
        return celsius + 273.15

    if from_unit not in _LINEAR_UNITS or to_unit not in _LINEAR_UNITS:
        raise ValueError("不支持在温度单位与长度/重量单位之间换算。")
    from_dimension, from_factor = _LINEAR_UNITS[from_unit]
    to_dimension, to_factor = _LINEAR_UNITS[to_unit]
    if from_dimension != to_dimension:
        raise ValueError("不能在不同维度之间换算。")
    return value * from_factor / to_factor


class UnitConversionInput(BaseModel):
    value: float = Field(description="需要换算的数值")
    from_unit: UnitName = Field(description="原单位")
    to_unit: UnitName = Field(description="目标单位")


@tool(args_schema=UnitConversionInput)
def convert_unit(value: float, from_unit: UnitName, to_unit: UnitName) -> str:
    """换算长度、重量或温度单位。"""
    try:
        result = convert_value(value, from_unit, to_unit)
        return _json_text(
            {
                "input": {"value": value, "unit": from_unit},
                "output": {"value": round(result, 8), "unit": to_unit},
            }
        )
    except ValueError as exc:
        return _json_text({"error": f"单位换算失败：{exc}"})


# ---------------------------------------------------------------------------
# Weather (Open-Meteo, no API key required)
# ---------------------------------------------------------------------------

_WEATHER_CODES = {
    0: "晴朗",
    1: "大部晴朗",
    2: "局部多云",
    3: "阴天",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "强毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    80: "小阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    95: "雷雨",
}


def weather_code_text(code: int) -> str:
    return _WEATHER_CODES.get(code, f"未知天气代码 {code}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    reraise=True,
)
def _get_json(url: str, params: dict[str, object]) -> dict:
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


class WeatherInput(BaseModel):
    city: str = Field(min_length=1, max_length=80, description="城市名称，例如杭州、北京")
    forecast_days: int = Field(
        default=1,
        ge=1,
        le=3,
        description="返回未来几天的天气，可选 1 到 3",
    )


@tool(args_schema=WeatherInput)
def get_weather(city: str, forecast_days: int = 1) -> str:
    """通过 Open-Meteo 查询城市实时天气和最多三天天气预报。"""
    try:
        locations = _get_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            {"name": city, "count": 1, "language": "zh", "format": "json"},
        ).get("results", [])
        if not locations:
            return _json_text({"error": f"没有找到城市：{city}"})

        location = locations[0]
        data = _get_json(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": forecast_days,
                "timezone": "auto",
            },
        )

        current = data.get("current", {})
        daily = data.get("daily", {})
        forecast = []
        for index, forecast_date in enumerate(daily.get("time", [])):
            forecast.append(
                {
                    "date": forecast_date,
                    "weather": weather_code_text(daily["weather_code"][index]),
                    "min_temperature_c": daily["temperature_2m_min"][index],
                    "max_temperature_c": daily["temperature_2m_max"][index],
                    "max_precipitation_probability_percent": daily[
                        "precipitation_probability_max"
                    ][index],
                }
            )

        return _json_text(
            {
                "resolved_city": location.get("name"),
                "administrative_area": location.get("admin1"),
                "country": location.get("country"),
                "timezone": data.get("timezone"),
                "current": {
                    "time": current.get("time"),
                    "weather": weather_code_text(current.get("weather_code", -1)),
                    "temperature_c": current.get("temperature_2m"),
                    "apparent_temperature_c": current.get("apparent_temperature"),
                    "wind_speed_kmh": current.get("wind_speed_10m"),
                },
                "forecast": forecast,
                "data_source": "Open-Meteo",
            }
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        return _json_text({"error": f"天气查询失败：{exc}"})


# ---------------------------------------------------------------------------
# Persistent todo list
# ---------------------------------------------------------------------------


def _todo_file() -> Path:
    configured_dir = os.getenv("TOOLBOX_DATA_DIR")
    if configured_dir:
        data_dir = Path(configured_dir)
    else:
        data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "todos.json"


def _load_todos() -> list[dict]:
    path = _todo_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"待办文件读取失败：{exc}") from exc
    if not isinstance(data, list):
        raise ValueError("待办文件格式不正确，应为 JSON 列表。")
    return data


def _save_todos(todos: list[dict]) -> None:
    path = _todo_file()
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(_json_text(todos) + "\n", encoding="utf-8")
    temporary.replace(path)


Priority = Literal["low", "medium", "high"]


class AddTodoInput(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="待办事项内容")
    due_date: date | None = Field(default=None, description="截止日期 YYYY-MM-DD，可不填")
    priority: Priority = Field(
        default="medium", description="优先级：low、medium 或 high"
    )


@tool(args_schema=AddTodoInput)
def add_todo(
    title: str,
    due_date: date | None = None,
    priority: Priority = "medium",
) -> str:
    """新增一条待办事项并保存到本地 JSON 文件。"""
    try:
        todos = _load_todos()
        next_id = max((int(item.get("id", 0)) for item in todos), default=0) + 1
        todo = {
            "id": next_id,
            "title": title.strip(),
            "due_date": due_date.isoformat() if due_date else None,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        todos.append(todo)
        _save_todos(todos)
        return _json_text({"message": "待办已添加", "todo": todo})
    except (OSError, ValueError) as exc:
        return _json_text({"error": str(exc)})


TodoStatus = Literal["all", "pending", "completed"]


class ListTodosInput(BaseModel):
    status: TodoStatus = Field(
        default="pending", description="筛选状态：all、pending 或 completed"
    )


@tool(args_schema=ListTodosInput)
def list_todos(status: TodoStatus = "pending") -> str:
    """列出本地保存的待办事项。"""
    try:
        todos = _load_todos()
        filtered = todos if status == "all" else [x for x in todos if x["status"] == status]
        return _json_text({"status_filter": status, "count": len(filtered), "todos": filtered})
    except (OSError, ValueError, KeyError) as exc:
        return _json_text({"error": str(exc)})


class CompleteTodoInput(BaseModel):
    todo_id: int = Field(gt=0, description="需要完成的待办 ID")


@tool(args_schema=CompleteTodoInput)
def complete_todo(todo_id: int) -> str:
    """根据待办 ID 将事项标记为已完成。"""
    try:
        todos = _load_todos()
        for todo in todos:
            if todo.get("id") == todo_id:
                todo["status"] = "completed"
                todo["completed_at"] = datetime.now().isoformat(timespec="seconds")
                _save_todos(todos)
                return _json_text({"message": "待办已完成", "todo": todo})
        return _json_text({"error": f"没有找到 ID 为 {todo_id} 的待办事项"})
    except (OSError, ValueError) as exc:
        return _json_text({"error": str(exc)})


TOOLS = [
    calculator,
    get_current_datetime,
    days_between,
    convert_unit,
    get_weather,
    add_todo,
    list_todos,
    complete_todo,
]
TOOL_MAP = {item.name: item for item in TOOLS}
