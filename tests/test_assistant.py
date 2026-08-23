from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from toolbox.assistant import ProductivityAssistant
from toolbox.config import Settings


class FakeToolCallingModel:
    def __init__(self):
        self.responses = [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"expression": "(12 + 3) * 4"},
                        "id": "call-test-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="计算结果是 60。"),
        ]
        self.invocations = []

    def bind_tools(self, tools, tool_choice="auto"):
        assert tools
        assert tool_choice == "auto"
        return self

    def invoke(self, messages):
        self.invocations.append(list(messages))
        return self.responses.pop(0)


def test_manual_tool_loop_executes_tool_and_returns_final_answer() -> None:
    settings = Settings(
        provider="ollama",
        model_name="test-model",
        api_key=None,
        base_url="http://localhost:11434",
        max_tool_rounds=3,
    )
    model = FakeToolCallingModel()
    assistant = ProductivityAssistant(settings=settings, model=model)

    result = assistant.ask("请计算 (12 + 3) * 4")

    assert result.answer == "计算结果是 60。"
    assert result.tool_events[0].name == "calculator"
    assert result.tool_events[0].success is True
    assert any(isinstance(message, ToolMessage) for message in model.invocations[1])
