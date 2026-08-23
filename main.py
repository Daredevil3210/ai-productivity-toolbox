from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from toolbox.assistant import ProductivityAssistant
from toolbox.config import ConfigurationError, Settings
from toolbox.tools import TOOLS


console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 个人效率工具箱")
    parser.add_argument("-q", "--question", help="只提问一次，输出回答后退出")
    parser.add_argument(
        "--no-tool-trace",
        action="store_true",
        help="不显示本次调用过的工具",
    )
    return parser


def print_help() -> None:
    console.print(
        "\n[bold]可用命令[/bold]\n"
        "  /help   查看帮助\n"
        "  /tools  查看已注册工具\n"
        "  /clear  清空本次会话上下文\n"
        "  /exit   退出程序\n"
    )


def print_tools() -> None:
    console.print("\n[bold]当前工具[/bold]")
    for item in TOOLS:
        console.print(f"  • [cyan]{item.name}[/cyan]：{item.description}")
    console.print()


def print_result(result, show_trace: bool) -> None:
    if show_trace and result.tool_events:
        console.print("[dim]本次工具调用：[/dim]")
        for event in result.tool_events:
            state = "成功" if event.success else "失败"
            console.print(
                f"  [dim]• {event.name}({event.arguments}) -> {state}[/dim]"
            )
    console.print(Panel(Markdown(result.answer), title="助手", border_style="green"))


def ask_once(assistant: ProductivityAssistant, question: str, show_trace: bool) -> None:
    with console.status("[bold cyan]正在思考并选择工具...[/bold cyan]"):
        result = assistant.ask(question)
    print_result(result, show_trace)


def interactive_loop(assistant: ProductivityAssistant, show_trace: bool) -> None:
    console.print(
        Panel(
            "可以让我计算、换算单位、查询日期/天气，以及管理待办事项。\n"
            "输入 [bold]/help[/bold] 查看命令，输入 [bold]/exit[/bold] 退出。",
            title="AI 个人效率工具箱",
            border_style="cyan",
        )
    )

    while True:
        try:
            question = console.input("[bold blue]你：[/bold blue]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n再见！")
            return

        if not question:
            continue
        if question.lower() in {"/exit", "/quit", "exit", "quit"}:
            console.print("再见！")
            return
        if question.lower() == "/help":
            print_help()
            continue
        if question.lower() == "/tools":
            print_tools()
            continue
        if question.lower() == "/clear":
            assistant.clear()
            console.print("[green]本次会话上下文已清空。[/green]")
            continue

        try:
            ask_once(assistant, question, show_trace)
        except Exception as exc:  # CLI boundary: keep the session alive.
            console.print(f"[bold red]请求失败：[/bold red]{exc}")


def main() -> int:
    args = build_parser().parse_args()
    try:
        settings = Settings.from_env()
        assistant = ProductivityAssistant(settings)
    except ConfigurationError as exc:
        console.print(f"[bold red]配置错误：[/bold red]{exc}")
        console.print("请复制 .env.example 为 .env，并按 README 填写模型配置。")
        return 2
    except ImportError as exc:
        console.print(f"[bold red]缺少依赖：[/bold red]{exc}")
        console.print("请执行：pip install -r requirements.txt")
        return 3

    show_trace = settings.show_tool_trace and not args.no_tool_trace
    if args.question:
        ask_once(assistant, args.question, show_trace)
        return 0

    interactive_loop(assistant, show_trace)
    return 0


if __name__ == "__main__":
    sys.exit(main())
