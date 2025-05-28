from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint
import os
import json
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
    
    # 创建JSON树结构
    preview_tree = {
        "根目录": path,
        "归档目录": base_dst,
        "格式": format_key,
        "文件夹": {}
    }
    
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
        
        # 提取相对路径，更好地展示变化
        rel_dst = os.path.relpath(preview_path, base_dst)
        
        operations.append({
            "folder": name,
            "timestamp": dt,
            "destination": preview_path,
            "rel_destination": rel_dst
        })
        
        # 添加到JSON树
        preview_tree["文件夹"][name] = {
            "识别时间": dt.strftime("%Y-%m-%d"),
            "目标路径": rel_dst
        }
    
    # 显示预览表格
    if not operations:
        console.print("[yellow]没有找到符合条件的文件夹")
        return
    
    # 保存预览JSON
    preview_json_path = os.path.join(path, "timeu_preview.json")
    with open(preview_json_path, "w", encoding="utf-8") as f:
        json.dump(preview_tree, f, ensure_ascii=False, indent=2)
    console.print(f"[blue]预览已保存到: {preview_json_path}")
        
    # 创建文件树形式的预览
    console.print("\n[bold]预览将要执行的操作:[/bold]")
    
    # 创建根树
    root_tree = Tree(f"[bold]{path}[/bold]")
    
    # 预览前三个文件夹（如果有的话）
    show_count = min(3, len(operations))
    for i, op in enumerate(operations[:show_count]):
        folder_node = root_tree.add(f"[yellow]{op['folder']}[/yellow] -> [green]{op['rel_destination']}[/green]")
        folder_node.add(f"[blue]识别时间戳: {op['timestamp'].strftime('%Y-%m-%d')}[/blue]")
    
    # 如果有更多文件夹，显示省略信息
    if len(operations) > show_count:
        root_tree.add(f"[dim]... 还有 {len(operations) - show_count} 个文件夹 (详见 timeu_preview.json)[/dim]")
    
    # 打印树
    rprint(root_tree)
    
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
