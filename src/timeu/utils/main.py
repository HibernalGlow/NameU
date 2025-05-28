from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
import os
from input_path import get_path
from extract_timestamp import extract_timestamp_from_name
from sync_file_time import sync_folder_file_time
from archive_folders import archive_folder, FORMATS
from datetime import datetime

console = Console()

def main():
    path = get_path()
    if not path:
        return
    
    base_dst = os.path.join(path, '归档')
    
    # 使用rich展示可用格式
    console.print("[bold]可用的归档格式:[/bold]")
    
    # 创建单个表格，包含所有格式
    format_table = Table(show_header=True)
    format_table.add_column("序号", style="cyan")
    format_table.add_column("格式名")
    format_table.add_column("类型")
    format_table.add_column("说明")
    format_table.add_column("示例")
    
    # 将格式名称与序号映射
    format_index_map = {}
    format_index = 1
    
    # 先添加单层格式
    for key, format_spec in FORMATS.items():
        if not isinstance(format_spec, list):
            # 单层格式
            sample = datetime.now().strftime(format_spec)
            format_table.add_row(
                str(format_index),
                key, 
                "单层",
                format_spec, 
                sample
            )
            format_index_map[format_index] = key
            format_index += 1
    
    # 再添加多层格式
    for key, format_spec in FORMATS.items():
        if isinstance(format_spec, list):
            # 多层格式
            example_path = ""
            for fmt in format_spec:
                example_path = os.path.join(example_path, datetime.now().strftime(fmt))
            format_table.add_row(
                str(format_index),
                key, 
                "多层",
                "→".join(format_spec), 
                example_path
            )
            format_index_map[format_index] = key
            format_index += 1
    
    console.print(format_table)
    
    # 使用数字选择格式
    max_index = max(format_index_map.keys())
    format_index = IntPrompt.ask(
        "请输入序号选择归档格式",
        default=1,
        show_choices=False,
        show_default=True
    )
    
    # 验证输入的序号是否有效
    while format_index not in format_index_map:
        console.print(f"[red]无效的序号，请输入1-{max_index}之间的数字")
        format_index = IntPrompt.ask(
            "请输入序号选择归档格式",
            default=1,
            show_choices=False,
            show_default=True
        )
    
    # 获取选择的格式
    format_key = format_index_map[format_index]
    console.print(f"已选择格式: [green]{format_key}")
    
    # 收集所有操作用于预览
    operations = []
    folders_with_timestamp = []
    
    for name in os.listdir(path):
        folder_path = os.path.join(path, name)
        if not os.path.isdir(folder_path) or folder_path == base_dst:
            continue
            
        dt = extract_timestamp_from_name(name)
        if not dt:
            console.print(f"[yellow]未识别到时间戳: {name}")
            continue
            
        folders_with_timestamp.append((folder_path, dt, name))
        
        # 预览
        preview_path = archive_folder(folder_path, dt, base_dst, format_key, dry_run=True)
        operations.append({
            "folder": name,
            "timestamp": dt,
            "destination": preview_path,
        })
    
    # 显示预览表格
    if not operations:
        console.print("[yellow]没有找到符合条件的文件夹")
        return
        
    console.print("\n[bold]预览将要执行的操作:[/bold]")
    preview_table = Table(show_header=True)
    preview_table.add_column("源文件夹")
    preview_table.add_column("识别时间戳")
    preview_table.add_column("目标位置")
    
    for op in operations:
        preview_table.add_row(
            op["folder"], 
            op["timestamp"].strftime("%Y-%m-%d"), 
            op["destination"]
        )
    
    console.print(preview_table)
    
    # 确认是否同步文件时间
    sync_time = Confirm.ask("是否同步文件时间？", default=True)
    
    # 确认是否执行移动操作
    if Confirm.ask("确认执行以上操作？", default=False):
        for folder_path, dt, name in folders_with_timestamp:
            console.print(f"[green]处理: {name} -> {dt}")
            
            if sync_time:
                sync_folder_file_time(folder_path, dt)
                console.print(f"[blue]已同步文件时间: {folder_path}")
                
            new_path = archive_folder(folder_path, dt, base_dst, format_key)
            console.print(f"[cyan]已归档到: {new_path}")
    else:
        console.print("[yellow]操作已取消")

if __name__ == "__main__":
    main()
