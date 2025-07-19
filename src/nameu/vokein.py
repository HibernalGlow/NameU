#!/usr/bin/env python3
"""
一体化 Invoke 任务启动器 - 包含任务定义和启动器
"""

import sys
import subprocess
from pathlib import Path
from invoke import task, Collection, Context
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

# ==================== 任务定义 ====================

@task()
def standard_multi(c):
    """标准多画师模式 - 会添加画师名后缀"""
    cmd = f"python -m nameu --mode multi --clipboard --keep-timestamp"
    subprocess.run(cmd, shell=True)

@task()
def standard_single(c):
    """标准单画师模式 - 会添加画师名后缀"""
    cmd = f"python -m nameu --mode single --clipboard --keep-timestamp"
    subprocess.run(cmd, shell=True)

@task()
def no_artist_mode(c):
    """无画师模式 - 不添加画师名后缀的重命名模式"""
    cmd = f"python -m nameu --no-artist --clipboard --keep-timestamp"
    subprocess.run(cmd, shell=True)

@task()
def no_sensitive_convert(c):
    """无敏感词转换 - 不将敏感词转换为拼音的模式"""
    cmd = f"python -m nameu --mode multi --clipboard --keep-timestamp --no-convert-sensitive"
    subprocess.run(cmd, shell=True)
# ==================== 启动器 ====================

def vokein():
    """运行任务选择器"""
    # 直接使用当前模块作为任务集合
    import inspect
    current_module = inspect.getmodule(inspect.currentframe())
    
    # 创建Collection并从当前模块加载任务
    ns = Collection.from_module(current_module)
    
    # 过滤掉内部任务（以_开头的）
    tasks = [(name, task) for name, task in ns.tasks.items() 
             if not name.startswith('_')]
    
    while True:
        # 显示任务表格
        table = Table(title="NameU 自动唯一文件名工具", show_header=True)
        table.add_column("编号", style="cyan", width=4)
        table.add_column("任务名", style="yellow")
        table.add_column("描述", style="white")
        
        for i, (name, task_obj) in enumerate(tasks, 1):
            # 修复描述获取逻辑
            desc = task_obj.__doc__ or ""
            if desc:
                desc = desc.split('\n')[0].strip()
            else:
                desc = "无描述"
            table.add_row(str(i), name, desc)
        
        table.add_row("0", "退出", "")
        console.print(table)
        
        # 选择任务
        choice = Prompt.ask(
            "[green]请选择任务编号[/green]",
            choices=[str(i) for i in range(len(tasks) + 1)],
            default="0"
        )
        
        if choice == "0":
            return 0
        
        # 执行任务
        task_name, task_obj = tasks[int(choice) - 1]
        try:
            console.print(f"[blue]执行: {task_name}[/blue]")
            task_obj(Context())
            console.print(f"[green]✓ {task_name} 完成[/green]")
        except KeyboardInterrupt:
            console.print("\n[yellow]任务中断[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ {task_name} 失败: {e}[/red]")

if __name__ == "__main__":
    sys.exit(vokein())





