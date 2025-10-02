#!/usr/bin/env python3
"""
压缩包名称恢复工具
用于将指定文件夹下的压缩包恢复到历史中的指定名称
"""

import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# 添加src到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

from nameset.restore.restore import ArchiveRestoreManager
from pathr.core import PathRestoreManager

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn


def create_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}", justify="right"),
        TimeElapsedColumn(),
    )


def print_archive_list(archives: List[Dict[str, Any]]):
    """打印压缩包列表"""
    print("\n📋 扫描到的压缩包:")
    print("-" * 80)
    
    for i, archive in enumerate(archives, 1):
        status = "✅" if archive.get('has_history') else "❌"
        display_name = archive.get('relative_path') or archive.get('current_file')
        print(f"{i:2d}. {status} {display_name}")
        
        if archive.get('has_history'):
            print(f"      ID: {archive['archive_id']}")
            print(f"      历史记录: {archive['history_count']} 条")
            if archive.get('artist_name'):
                print(f"      画师: {archive['artist_name']}")
        else:
            print(f"      {archive.get('message', '无历史记录')}")
        print()


def print_restore_options(options: List[Dict[str, Any]]):
    """打印恢复选项"""
    print("\n🔄 可恢复的历史名称:")
    print("-" * 80)
    
    for i, option in enumerate(options, 1):
        print(f"{i:2d}. {option['name']}")
        print(f"      时间: {option['timestamp']}")
        print(f"      原因: {option['reason']}")
        print(f"      说明: {option['description']}")
        print()


def interactive_mode():
    """交互式模式"""
    print("🔄 压缩包名称恢复工具")
    print("=" * 50)
    
    # 获取文件夹路径
    folder_path = input("📁 请输入文件夹路径: ").strip().strip('"')
    
    if not os.path.exists(folder_path):
        print("❌ 文件夹不存在!")
        return
    
    if not os.path.isdir(folder_path):
        print("❌ 路径不是文件夹!")
        return
    
    # 扫描压缩包
    with ArchiveRestoreManager() as restore_manager:
        while True:
            print(f"\n🔍 正在扫描文件夹: {folder_path}")

            with create_progress() as progress:
                task_scan = progress.add_task("扫描压缩包", total=None)

                archives = restore_manager.scan_folder_archives(
                    folder_path,
                    recursive=True,
                    on_progress=lambda _: progress.advance(task_scan),
                )

            archive_count = len(archives)
            print(f"✅ 扫描完成，共 {archive_count} 个压缩包候选")

            if not archives:
                print("❌ 未找到任何压缩包文件!")
                return

            # 过滤有历史记录的文件
            archives_with_history = [a for a in archives if a.get('has_history')]
            history_available = bool(archives_with_history)

            if not history_available:
                print("⚠️ 没有找到具有历史记录的压缩包，相关操作将被跳过，可直接使用路径恢复功能。")

            print_archive_list(archives)

            # 选择操作模式
            print("🎯 选择操作模式:")
            print("1. 单个文件恢复")
            print("2. 按日期批量恢复") 
            print("3. 预览恢复效果")
            print("4. 路径恢复 (基于UUID)")
            print("Q. 返回/退出")

            choice = input("请选择 (1-4 / Q): ").strip().lower()

            if choice in {"q", "quit", "exit"}:
                print("👋 已返回主界面")
                return

            if choice in {"1", "2", "3"} and not history_available:
                print("⚠️ 当前文件夹没有历史记录，无法执行该操作，请使用选项 4。")
                continue

            if choice == "1":
                single_file_restore(restore_manager, archives_with_history)
            elif choice == "2":
                batch_restore_by_date(restore_manager, folder_path)
            elif choice == "3":
                preview_restore(restore_manager, folder_path)
            elif choice == "4":
                path_restore_folder(folder_path)
            else:
                print("❌ 无效选择!")
                continue

            back = input("\n继续执行其他操作吗? (Y/n): ").strip().lower()
            if back in {"n", "no"}:
                print("👋 已返回主界面")
                return


def single_file_restore(restore_manager: ArchiveRestoreManager, archives: List[Dict[str, Any]]):
    """单个文件恢复"""
    print("\n📋 有历史记录的压缩包:")
    for i, archive in enumerate(archives, 1):
        display_name = archive.get('relative_path') or archive['current_file']
        print(f"{i}. {display_name} (历史记录: {archive['history_count']} 条)")
    
    try:
        file_index = int(input(f"\n请选择要恢复的文件 (1-{len(archives)}): ")) - 1
        if not 0 <= file_index < len(archives):
            print("❌ 无效选择!")
            return
        
        selected_archive = archives[file_index]
        archive_id = selected_archive['archive_id']
        
        # 获取恢复选项
        options = restore_manager.get_restore_options(archive_id)
        if not options:
            print("❌ 没有可恢复的历史记录!")
            return
        
        print_restore_options(options)
        
        option_index = int(input(f"请选择要恢复的名称 (1-{len(options)}): ")) - 1
        if not 0 <= option_index < len(options):
            print("❌ 无效选择!")
            return
        
        selected_option = options[option_index]
        target_name = selected_option['name']
        
        # 确认恢复
        current_name = selected_archive['current_file']
        print(f"\n📝 恢复确认:")
        print(f"当前名称: {current_name}")
        print(f"目标名称: {target_name}")
        
        if current_name == target_name:
            print("⚠️ 目标名称与当前名称相同，无需恢复!")
            return
        
        confirm = input("确认恢复? (y/N): ").strip().lower()
        if confirm == 'y':
            success, message = restore_manager.restore_archive_name(
                selected_archive['file_path'], 
                target_name,
                f"手动恢复到: {selected_option['timestamp']}"
            )
            
            if success:
                print(f"✅ {message}")
            else:
                print(f"❌ {message}")
        else:
            print("❌ 恢复已取消!")
            
    except ValueError:
        print("❌ 请输入有效数字!")
    except Exception as e:
        print(f"❌ 恢复过程中出错: {e}")


def batch_restore_by_date(restore_manager: ArchiveRestoreManager, folder_path: str):
    """按日期批量恢复"""
    target_date = input("\n📅 请输入目标日期 (格式: 2025-07-15): ").strip()
    
    try:
        # 验证日期格式
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print("❌ 日期格式错误! 请使用 YYYY-MM-DD 格式")
        return
    
    # 预览恢复效果
    preview = restore_manager.preview_restore_by_date(folder_path, target_date)
    changes = [p for p in preview if p['will_change']]
    
    if not changes:
        print("❌ 没有文件需要恢复!")
        return
    
    print(f"\n📋 将要恢复的文件 (目标日期: {target_date}):")
    print("-" * 80)
    
    for change in changes:
        print(f"📄 {change['current_name']}")
        print(f"  → {change['target_name']}")
        print()
    
    print(f"总计: {len(changes)} 个文件将被恢复")
    
    confirm = input("\n确认批量恢复? (y/N): ").strip().lower()
    if confirm == 'y':
        # 构建恢复规则
        restore_rules = [
            {
                'archive_id': change['archive_id'],
                'target_name': change['target_name'],
                'reason': f'批量恢复到 {target_date}'
            }
            for change in changes
        ]
        
        # 执行批量恢复
        results = restore_manager.batch_restore_folder(folder_path, restore_rules)
        
        print(f"\n🎯 批量恢复结果:")
        print(f"总计: {results['total']}")
        print(f"成功: {results['success']}")
        print(f"失败: {results['failed']}")
        
        if results['failed'] > 0:
            print("\n❌ 失败的文件:")
            for detail in results['details']:
                if not detail['success']:
                    print(f"  - {detail.get('current_name', detail['archive_id'])}: {detail['message']}")
    else:
        print("❌ 批量恢复已取消!")


def preview_restore(restore_manager: ArchiveRestoreManager, folder_path: str):
    """预览恢复效果"""
    target_date = input("\n📅 请输入目标日期 (格式: 2025-07-15): ").strip()
    
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print("❌ 日期格式错误! 请使用 YYYY-MM-DD 格式")
        return
    
    preview = restore_manager.preview_restore_by_date(folder_path, target_date)
    
    print(f"\n👀 恢复预览 (目标日期: {target_date}):")
    print("-" * 80)
    
    changes = 0
    for item in preview:
        status = "🔄" if item['will_change'] else "⏸️"
        print(f"{status} {item['current_name']}")
        
        if item['will_change']:
            print(f"    → {item['target_name']}")
            changes += 1
        else:
            print(f"    (无需更改)")
        print()
    
    print(f"📊 统计: 总计 {len(preview)} 个文件，其中 {changes} 个需要恢复")


def path_restore_folder(folder_path: str):
    """基于UUID匹配的路径恢复"""
    print("\n🛠️ 路径恢复预览")
    print("-" * 80)

    base_folder = os.path.abspath(folder_path)

    with PathRestoreManager() as path_manager:
        with create_progress() as progress:
            task_preview = progress.add_task("分析压缩包", total=None)

            def on_preview(_path: str, _outcome: Any) -> None:
                progress.advance(task_preview)

            outcomes = path_manager.restore_from_directory(
                folder_path,
                recursive=True,
                dry_run=True,
                on_progress=on_preview,
            )

        symbols = {
            "planned": "🔄",
            "aligned": "✅",
            "moved": "✅",
            "skipped": "⏸️",
            "no-match": "❌",
            "no-target": "❓",
            "ambiguous": "⚠️",
            "error": "💥",
        }

        print(f"✅ 预览完成，共 {len(outcomes)} 个候选条目")

        planned = []
        for i, outcome in enumerate(outcomes, 1):
            symbol = symbols.get(outcome.status, "•")
            try:
                rel_path = os.path.relpath(outcome.source_path, base_folder)
            except ValueError:
                rel_path = outcome.source_path
            print(f"{i:2d}. {symbol} {rel_path}")
            if outcome.target_path:
                target_rel = outcome.target_path
                if isinstance(target_rel, str) and os.path.isabs(target_rel):
                    try:
                        target_rel = os.path.relpath(target_rel, base_folder)
                    except ValueError:
                        pass
                print(f"      → {target_rel}")
            print(f"      状态: {outcome.status} - {outcome.message}")
            if outcome.archive_id:
                print(f"      UUID: {outcome.archive_id}")
            planned.append(outcome) if outcome.status == "planned" else None
            print()

        planned = [p for p in planned if p.status == "planned"]
        if not planned:
            print("✅ 没有需要移动的文件，或缺少目标路径信息。")
            return

        confirm = input("是否执行上述路径恢复? (y/N): ").strip().lower()
        if confirm != "y":
            print("❌ 路径恢复已取消。")
            return

        print("\n🚚 正在执行路径恢复...")
        results = []
        with create_progress() as progress:
            task_restore = progress.add_task("执行路径恢复", total=len(planned))
            for outcome in planned:
                result = path_manager.restore_file(outcome.source_path, dry_run=False)
                results.append(result)
                progress.advance(task_restore)

        for result in results:
            prefix = symbols.get(result.status, "•")
            try:
                result_rel = os.path.relpath(result.source_path, base_folder)
            except ValueError:
                result_rel = result.source_path
            target_display = result.target_path or '未知目标'
            if isinstance(target_display, str) and os.path.isabs(target_display):
                try:
                    target_display = os.path.relpath(target_display, base_folder)
                except ValueError:
                    pass
            print(f"{prefix} {result_rel} -> {target_display}")
            print(f"   状态: {result.status} - {result.message}")

        print("\n🎉 路径恢复完成!")


if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # 命令行模式
            folder_path = sys.argv[1]
            if not os.path.exists(folder_path):
                print(f"❌ 文件夹不存在: {folder_path}")
                sys.exit(1)
            
            with ArchiveRestoreManager() as restore_manager:
                archives = restore_manager.scan_folder_archives(folder_path)
                print_archive_list(archives)
        else:
            # 交互式模式
            interactive_mode()
            
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，退出程序")
    except Exception as e:
        print(f"\n❌ 程序出错: {e}")
        import traceback
        traceback.print_exc()
