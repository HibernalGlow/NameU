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
from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        console_output: 是否输出到控制台，默认为True
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        )
    
    # 使用 datetime 构建日志路径
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    # 构建日志目录和文件路径
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    # 添加文件处理器
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="tsync", console_output=True)

def main():
    logger.info("开始执行时间戳文件同步与归档工具")
    path = get_path()
    if not path:
        logger.warning("未获取到有效路径，程序退出")
        return
    
    logger.info(f"工作目录: {path}")
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
        logger.warning(f"用户输入了无效的序号: {format_index}")
        console.print(f"[red]无效的序号，请输入1-{max_index}之间的数字")
        format_index = IntPrompt.ask(
            "请输入序号选择归档格式",
            default=1,
            show_choices=False,
            show_default=True
        )
    
    # 获取选择的格式
    format_key = format_index_map[format_index]
    logger.info(f"用户选择的归档格式: {format_key}")
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
            logger.warning(f"未识别到时间戳: {name}")
            console.print(f"[yellow]未识别到时间戳: {name}")
            continue
            
        logger.debug(f"从文件夹名 {name} 识别到时间戳: {dt}")
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
        logger.warning("没有找到符合条件的文件夹")
        console.print("[yellow]没有找到符合条件的文件夹")
        return
    
    # 保存预览JSON
    preview_json_path = os.path.join(path, "timeu_preview.json")
    with open(preview_json_path, "w", encoding="utf-8") as f:
        json.dump(preview_tree, f, ensure_ascii=False, indent=2)
    logger.info(f"预览已保存到: {preview_json_path}")
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
    logger.info(f"用户选择{'同步' if sync_time else '不同步'}文件时间")
    
    # 确认是否执行移动操作
    if Confirm.ask("确认执行以上操作？", default=False):
        logger.info("用户确认执行归档操作")
        for folder_path, dt, name in folders_with_timestamp:
            logger.info(f"处理文件夹: {name}, 时间戳: {dt}")
            console.print(f"[green]处理: {name} -> {dt}")
            
            if sync_time:
                logger.info(f"同步文件时间: {folder_path}")
                sync_folder_file_time(folder_path, dt)
                console.print(f"[blue]已同步文件时间: {folder_path}")
                
            new_path = archive_folder(folder_path, dt, base_dst, format_key)
            logger.info(f"已归档到: {new_path}")
            console.print(f"[cyan]已归档到: {new_path}")
    else:
        logger.warning("用户取消了操作")
        console.print("[yellow]操作已取消")

if __name__ == "__main__":
    main()
