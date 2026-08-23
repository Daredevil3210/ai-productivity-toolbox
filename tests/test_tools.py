from __future__ import annotations

import json

import pytest

import toolbox.tools as tools_module
from toolbox.tools import (
    add_todo,
    calculator,
    complete_todo,
    convert_unit,
    convert_value,
    days_between,
    get_weather,
    list_todos,
    safe_calculate,
    weather_code_text,
)


def parse_tool_output(value: str) -> dict:
    return json.loads(value)


def test_safe_calculator_supports_normal_arithmetic() -> None:
    assert safe_calculate("(12 + 3) * 4") == 60
    assert safe_calculate("2 ** 8") == 256


def test_safe_calculator_rejects_python_code() -> None:
    with pytest.raises(ValueError):
        safe_calculate("__import__('os').getcwd()")


def test_calculator_returns_error_as_string() -> None:
    result = parse_tool_output(calculator.invoke({"expression": "1 / 0"}))
    assert "error" in result


def test_days_between_dates() -> None:
    result = parse_tool_output(
        days_between.invoke({"start_date": "2026-08-01", "end_date": "2026-08-21"})
    )
    assert result["signed_days"] == 20
    assert result["absolute_days"] == 20


def test_unit_conversions() -> None:
    assert convert_value(1, "km", "m") == 1000
    assert convert_value(32, "fahrenheit", "celsius") == pytest.approx(0)
    result = parse_tool_output(
        convert_unit.invoke({"value": 2.5, "from_unit": "kg", "to_unit": "g"})
    )
    assert result["output"]["value"] == 2500


def test_incompatible_units_return_error() -> None:
    result = parse_tool_output(
        convert_unit.invoke({"value": 1, "from_unit": "kg", "to_unit": "m"})
    )
    assert "error" in result


def test_weather_code_mapping() -> None:
    assert weather_code_text(0) == "晴朗"
    assert "未知" in weather_code_text(999)


def test_weather_tool_with_mocked_api(monkeypatch) -> None:
    def fake_get_json(url, params):
        if "geocoding" in url:
            return {
                "results": [
                    {
                        "name": "杭州",
                        "admin1": "浙江",
                        "country": "中国",
                        "latitude": 30.27,
                        "longitude": 120.15,
                    }
                ]
            }
        return {
            "timezone": "Asia/Shanghai",
            "current": {
                "time": "2026-08-21T10:00",
                "weather_code": 0,
                "temperature_2m": 30.0,
                "apparent_temperature": 32.0,
                "wind_speed_10m": 8.0,
            },
            "daily": {
                "time": ["2026-08-21"],
                "weather_code": [1],
                "temperature_2m_min": [25.0],
                "temperature_2m_max": [34.0],
                "precipitation_probability_max": [20],
            },
        }

    monkeypatch.setattr(tools_module, "_get_json", fake_get_json)
    result = parse_tool_output(get_weather.invoke({"city": "杭州", "forecast_days": 1}))
    assert result["resolved_city"] == "杭州"
    assert result["current"]["weather"] == "晴朗"
    assert result["forecast"][0]["weather"] == "大部晴朗"


def test_todo_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TOOLBOX_DATA_DIR", str(tmp_path))

    added = parse_tool_output(
        add_todo.invoke(
            {"title": "完成 LangChain 工具项目", "due_date": "2026-08-25", "priority": "high"}
        )
    )
    todo_id = added["todo"]["id"]

    pending = parse_tool_output(list_todos.invoke({"status": "pending"}))
    assert pending["count"] == 1
    assert pending["todos"][0]["title"] == "完成 LangChain 工具项目"

    completed = parse_tool_output(complete_todo.invoke({"todo_id": todo_id}))
    assert completed["todo"]["status"] == "completed"

    pending_after = parse_tool_output(list_todos.invoke({"status": "pending"}))
    assert pending_after["count"] == 0
