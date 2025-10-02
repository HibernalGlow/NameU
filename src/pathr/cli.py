"""Command-line interface for the ``pathr`` package."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm, Prompt

from .core import PathRestoreManager, RestoreOutcome, SUPPORTED_EXTENSIONS

app = typer.Typer(help="基于 NameSet 元数据的路径恢复工具集")
console = Console()


def _normalize_extensions(exts: Optional[Sequence[str]]) -> Optional[Sequence[str]]:
    if not exts:
        return None
    normalized = []
    for ext in exts:
        ext = ext.strip()
        if not ext:
            continue
        if not ext.startswith('.'):
            ext = f".{ext}"
        normalized.append(ext.lower())
    return tuple(normalized)


def _render_summary(outcomes: List[RestoreOutcome]) -> None:
    counter = Counter(outcome.status for outcome in outcomes)
    table = Table(title="恢复结果统计", show_lines=False)
    table.add_column("状态", style="cyan", justify="left")
    table.add_column("数量", style="green", justify="right")
    for status, count in counter.most_common():
        table.add_row(status, str(count))
    console.print(table)

    if not outcomes:
        console.print("[yellow]未检测到任何文件。[/]")
        return

    problematic = [
        outcome
        for outcome in outcomes
        if outcome.status in {"no-match", "ambiguous", "no-target", "skipped", "error"}
    ]
    if problematic:
        problem_table = Table(title="需要关注的条目", show_lines=False)
        problem_table.add_column("状态", style="magenta")
        problem_table.add_column("源文件", style="white")
        problem_table.add_column("消息", style="yellow")
        for outcome in problematic[:20]:
            problem_table.add_row(outcome.status, outcome.source_path, outcome.message)
        console.print(problem_table)
        if len(problematic) > 20:
            console.print(f"[yellow]还有 {len(problematic) - 20} 条问题未展示。[/]")


def _prompt_selection(valid_indices: Iterable[int]) -> List[int]:
    valid = sorted(set(valid_indices))
    if not valid:
        return []

    index_str = ", ".join(str(i) for i in valid)
    prompt_text = f"选择要移动的序号 (可输入逗号分隔的数字，默认 all，全选可用: all；跳过请输入 none)"

    while True:
        raw = Prompt.ask(prompt_text, default="all").strip().lower()
        if raw in {"all", "a", "*", ""}:
            return valid
        if raw in {"none", "n", "0"}:
            return []

        try:
            chosen = set()
            for chunk in raw.replace(";", ",").split(","):
                chunk = chunk.strip()
                if not chunk:
                    continue
                value = int(chunk)
                if value not in valid:
                    raise ValueError
                chosen.add(value)
            return sorted(chosen)
        except ValueError:
            console.print(f"[red]无效输入，请在 {index_str} 范围内选择。[/]")


def _display_planned_table(planned: Dict[int, RestoreOutcome]) -> None:
    table = Table(title="待移动的文件", show_lines=False)
    table.add_column("序号", justify="right", style="cyan")
    table.add_column("当前文件", style="white")
    table.add_column("目标路径", style="green")
    for index, outcome in planned.items():
        table.add_row(str(index), outcome.source_path, outcome.target_path or "-")
    console.print(Panel(table, title="预览列表", border_style="cyan"))


def _interactive_restore(manager: PathRestoreManager, outcomes: List[RestoreOutcome]) -> None:
    planned_items = {idx: outcome for idx, outcome in enumerate(outcomes, start=1) if outcome.status == "planned"}

    if not planned_items:
        console.print("[green]没有需要移动的文件，所有文件已在正确位置或缺少目标信息。[/]")
        return

    _display_planned_table(planned_items)
    selected_indices = _prompt_selection(planned_items.keys())

    if not selected_indices:
        console.print("[yellow]未选择任何文件，未执行移动操作。[/]")
        return

    if not Confirm.ask("确认移动所选文件吗？", default=True):
        console.print("[yellow]用户取消了移动操作。[/]")
        return

    result_rows: List[RestoreOutcome] = []
    result_table = Table(title="执行结果", show_lines=False)
    result_table.add_column("源文件", style="white")
    result_table.add_column("目标路径", style="cyan")
    result_table.add_column("状态", style="green")
    result_table.add_column("说明", style="yellow")

    for index in selected_indices:
        outcome = planned_items[index]
        result = manager.restore_file(outcome.source_path, dry_run=False)
        result_rows.append(result)
        result_table.add_row(
            result.source_path,
            result.target_path or "-",
            result.status,
            result.message,
        )

    console.print(result_table)
    _render_summary(result_rows)


@app.command("restore")
def restore_command(
    source: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="待恢复的文件夹"),
    execute: bool = typer.Option(False, "--execute", help="执行实际移动；默认仅预览"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="archives.db 的路径"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="是否递归扫描文件"),
    ext: Optional[List[str]] = typer.Option(None, "--ext", help="指定要匹配的扩展名，可重复"),
    interactive: bool = typer.Option(False, "--interactive", help="进入交互模式，批量选择要恢复的文件"),
) -> None:
    """根据数据库历史记录批量恢复路径。"""

    extensions = _normalize_extensions(ext)
    dry_run = True if interactive else not execute

    with PathRestoreManager(db_path=str(db_path) if db_path else None) as manager:
        outcomes = manager.restore_from_directory(
            source,
            recursive=recursive,
            extensions=extensions or SUPPORTED_EXTENSIONS,
            dry_run=dry_run,
        )

        _render_summary(outcomes)

        if interactive:
            _interactive_restore(manager, outcomes)
        elif not execute:
            console.print("[cyan]使用 --execute 选项即可实际执行移动操作。[/]")


@app.command("file")
def restore_single_file(
    file_path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False),
    execute: bool = typer.Option(False, "--execute", help="执行移动；默认仅预览"),
    db_path: Optional[Path] = typer.Option(None, "--db", help="archives.db 的路径"),
    interactive: bool = typer.Option(False, "--interactive", help="交互式确认并执行移动"),
) -> None:
    """恢复单个文件。"""

    with PathRestoreManager(db_path=str(db_path) if db_path else None) as manager:
        outcome = manager.restore_file(file_path, dry_run=(not execute) or interactive)

        if interactive and outcome.status == "planned":
            console.print(
                Panel(
                    f"[white]目标路径[/]: {outcome.target_path}\n[white]当前状态[/]: {outcome.status}\n[white]说明[/]: {outcome.message}",
                    title="预览",
                    border_style="cyan",
                )
            )

            if Confirm.ask("确认执行上述移动吗？", default=True):
                outcome = manager.restore_file(file_path, dry_run=False)
            else:
                console.print("[yellow]用户取消了移动操作。[/]")

    status_color = {
        "moved": "green",
        "planned": "cyan",
        "aligned": "green",
        "skipped": "yellow",
        "no-match": "yellow",
        "ambiguous": "magenta",
        "no-target": "magenta",
        "error": "red",
    }.get(outcome.status, "white")

    console.print(f"[{status_color}]{outcome.status}[/]: {outcome.message}")
    if outcome.target_path:
        console.print(f"  目标路径: {outcome.target_path}")
    if outcome.archive_id:
        console.print(f"  Archive ID: {outcome.archive_id}")
    if outcome.history_id:
        console.print(f"  History ID: {outcome.history_id}")

    if (not execute) and (not interactive) and outcome.status == "planned":
        console.print("[cyan]使用 --execute 可以实际执行移动。[/]")


def main() -> None:  # pragma: no cover - Typer 入口
    app()


__all__ = ["app", "main"]
