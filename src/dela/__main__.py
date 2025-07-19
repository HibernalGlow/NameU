import subprocess
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import fnmatch

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.text import Text
from rich import print as rprint

# 添加idu路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from idu.core.archive_handler import ArchiveHandler
except ImportError:
    # 如果导入失败，提供简化版本
    class ArchiveHandler:
        @staticmethod
        def _analyze_folder_structure(archive_path: str) -> str:
            """分析压缩包的文件夹结构"""
            try:
                result = subprocess.run(
                    ['7z', 'l', archive_path],
                    capture_output=True,
                    text=True,
                    encoding='gbk',
                    errors='ignore',
                    check=True
                )
                root_items = set()
                for line in result.stdout.splitlines():
                    if line.strip() and not line.startswith('-') and not line.startswith('Date'):
                        parts = line.split()
                        if len(parts) >= 6:
                            name = parts[-1]
                            if '/' in name or '\\' in name:
                                root_items.add(name.split('/')[0].split('\\')[0])
                            else:
                                root_items.add('')

                if '' in root_items:
                    return "no_folder" if len(root_items) == 1 else "multiple_folders"
                elif len(root_items) == 1:
                    return "single_folder"
                else:
                    return "multiple_folders"
            except Exception:
                return "no_folder"

console = Console()

def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.json"
    # config_path = Path("config.json")
    if not config_path.exists():
        console.print("[red]配置文件 config.json 不存在！[/red]")
        sys.exit(1)

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        console.print(f"[red]加载配置文件失败: {e}[/red]")
        sys.exit(1)

def find_archives(folder: str, config: Dict[str, Any]) -> List[str]:
    """查找压缩包文件"""
    archives = []
    archive_types = tuple(config.get('archive_types', ['.zip', '.7z', '.rar']))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("搜索压缩包文件...", total=None)

        for root, dirs, files in os.walk(folder):
            for name in files:
                if name.lower().endswith(archive_types):
                    archives.append(os.path.join(root, name))
                    progress.update(task, description=f"找到 {len(archives)} 个压缩包...")

    return archives

def check_archive_conditions(archive_path: str) -> tuple:
    """检查压缩包是否符合删除条件

    Returns:
        tuple: (是否符合条件, 结构类型, 根目录文件列表)
    """
    try:
        # 1. 分析文件夹结构
        structure = ArchiveHandler._analyze_folder_structure(archive_path)

        # 2. 只处理单文件夹结构
        if structure != "single_folder":
            return False, structure, []

        # 3. 检查根目录是否有目标文件
        root_files = []
        target_extensions = ['.json', '.log', '.txt', '.yaml']

        try:
            result = subprocess.run(
                ['7z', 'l', archive_path],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore',
                check=True
            )
            for line in result.stdout.splitlines():
                if line.strip() and not line.startswith('-') and not line.startswith('Date'):
                    parts = line.split()
                    if len(parts) >= 6:
                        name = parts[-1]
                        # 只检查根目录文件（不包含路径分隔符）
                        if '/' not in name and '\\' not in name:
                            file_ext = Path(name).suffix.lower()
                            if file_ext in target_extensions:
                                root_files.append(name)
        except subprocess.CalledProcessError:
            pass

        # 4. 只有根目录存在目标文件才符合条件
        return len(root_files) > 0, structure, root_files

    except Exception as e:
        console.print(f"[red]检查压缩包失败 {archive_path}: {e}[/red]")
        return False, "error", []


def should_delete_file(filename: str, config: Dict[str, Any]) -> bool:
    """判断文件是否应该被删除"""
    delete_patterns = config.get('delete_patterns', {})

    # 检查文件扩展名
    file_ext = Path(filename).suffix.lower()
    if file_ext in delete_patterns.get('file_extensions', []):
        return True

    # 检查完整文件名
    if filename in delete_patterns.get('file_names', []):
        return True

    # 检查文件模式匹配
    for pattern in delete_patterns.get('file_patterns', []):
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            return True

    return False

def list_files_in_archive(archive: str, config: Dict[str, Any]) -> List[str]:
    """列出压缩包中需要删除的文件"""
    try:
        output = subprocess.check_output(
            ['7z', 'l', archive],
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        files = []

        for line in output.splitlines():
            parts = line.strip().split()
            if len(parts) > 0:
                filename = parts[-1]
                if should_delete_file(filename, config):
                    files.append(filename)

        return files
    except Exception as e:
        console.print(f"[red]列出文件失败 {archive}: {e}[/red]")
        return []

def delete_files_in_archive(archive: str, files: List[str]) -> Dict[str, int]:
    """删除压缩包中的文件"""
    results = {"success": 0, "failed": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("删除文件中...", total=len(files))

        for fname in files:
            try:
                subprocess.run(['7z', 'd', archive, fname],
                             check=True,
                             capture_output=True)
                console.print(f"  [green]✓[/green] 删除: {fname}")
                results["success"] += 1
            except subprocess.CalledProcessError as e:
                console.print(f"  [red]✗[/red] 删除失败: {fname}")
                results["failed"] += 1

            progress.advance(task)

    return results

def display_files_table(files: List[str], max_display: int = 50) -> None:
    """显示文件列表表格"""
    if not files:
        console.print("[yellow]没有找到匹配的文件[/yellow]")
        return

    table = Table(title="待删除文件列表", show_header=True, header_style="bold magenta")
    table.add_column("序号", style="dim", width=6)
    table.add_column("文件名", style="cyan")
    table.add_column("类型", style="green")

    display_files = files[:max_display]
    for idx, filename in enumerate(display_files, 1):
        file_ext = Path(filename).suffix or "无扩展名"
        table.add_row(str(idx), filename, file_ext)

    if len(files) > max_display:
        table.add_row("...", f"还有 {len(files) - max_display} 个文件", "...")

    console.print(table)

def main():
    """主函数"""
    console.print(Panel.fit(
        "[bold blue]压缩包文件清理工具 (简化版)[/bold blue]\n"
        "专门删除单文件夹结构压缩包中根目录的 json/log/txt/yaml 文件\n"
        "[dim]只处理: 单文件夹结构 + JSON文件在文件夹外的压缩包[/dim]",
        title="DelA - Delete Archive Files (Simplified)"
    ))

    # 加载配置
    config = load_config()
    console.print("[green]✓[/green] 配置文件加载成功")

    # 获取文件夹路径
    folder = Prompt.ask("请输入要处理的文件夹路径", default=".")
    folder_path = Path(folder)

    if not folder_path.exists() or not folder_path.is_dir():
        console.print("[red]路径无效或不是文件夹[/red]")
        sys.exit(1)

    # 查找压缩包
    archives = find_archives(str(folder_path), config)

    if not archives:
        console.print("[yellow]未找到任何压缩包文件[/yellow]")
        return

    console.print(f"[green]找到 {len(archives)} 个压缩包文件[/green]")

    # 统计信息
    total_deleted = 0
    total_failed = 0
    processed_archives = 0

    # 处理每个压缩包
    for idx, archive in enumerate(archives, 1):
        console.print(f"\n[bold cyan]处理压缩包 [{idx}/{len(archives)}][/bold cyan]")
        console.print(f"文件: {archive}")

        # 检查压缩包是否符合删除条件
        meets_conditions, structure, root_files = check_archive_conditions(archive)

        console.print(f"  结构类型: {structure}")
        if root_files:
            console.print(f"  根目录文件: {', '.join(root_files)}")

        if not meets_conditions:
            if structure != "single_folder":
                console.print(f"[dim]  跳过: 不是单文件夹结构 ({structure})[/dim]")
            else:
                console.print(f"[dim]  跳过: 根目录无目标文件 (json/log/txt/yaml)[/dim]")
            continue

        # 只删除根目录的目标文件
        target_files = root_files  # 直接使用检查出的根目录文件

        if not target_files:
            console.print("[dim]  没有找到需要删除的文件，跳过[/dim]")
            continue

        # 显示文件列表
        console.print(f"[yellow]找到 {len(target_files)} 个根目录目标文件:[/yellow]")
        for file in target_files:
            console.print(f"  - {file}")

        # 确认删除
        if config.get('ui_settings', {}).get('confirm_before_delete', True):
            if not Confirm.ask(f"是否删除这 {len(target_files)} 个根目录文件？"):
                console.print("[dim]  跳过该压缩包[/dim]")
                continue

        # 执行删除
        results = delete_files_in_archive(archive, target_files)
        total_deleted += results["success"]
        total_failed += results["failed"]
        processed_archives += 1

        console.print(f"[green]成功删除 {results['success']} 个文件[/green]", end="")
        if results["failed"] > 0:
            console.print(f", [red]失败 {results['failed']} 个[/red]")
        else:
            console.print()

    # 显示总结
    console.print(Panel.fit(
        f"[bold green]处理完成！[/bold green]\n"
        f"处理压缩包: {processed_archives}/{len(archives)}\n"
        f"成功删除文件: {total_deleted}\n"
        f"删除失败: {total_failed}",
        title="处理结果"
    ))

if __name__ == '__main__':
    main()