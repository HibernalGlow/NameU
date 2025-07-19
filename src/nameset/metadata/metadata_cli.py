#!/usr/bin/env python3
"""
元数据管理命令行工具
用于查看和管理压缩包的完整历史元数据
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from nameset.manager import ArchiveManager
from nameset.id_handler import ArchiveIDHandler
from loguru import logger


def setup_logging(verbose: bool = False):
    """设置日志"""
    logger.remove()
    if verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")


def get_archive_id_from_path(archive_path: str) -> Optional[str]:
    """从压缩包路径获取ID"""
    if not os.path.exists(archive_path):
        print(f"❌ 文件不存在: {archive_path}")
        return None
    
    # 尝试从注释获取ID
    comment = ArchiveIDHandler.get_archive_comment(archive_path)
    archive_id = ArchiveIDHandler.extract_id_from_comment(comment)
    
    if not archive_id:
        print(f"❌ 无法从文件注释中获取ID: {archive_path}")
        return None
    
    return archive_id


def cmd_show_metadata(args):
    """显示完整元数据"""
    db_path = args.database or "nameset.db"
    
    with ArchiveManager(db_path) as manager:
        if args.file:
            # 从文件路径获取ID
            archive_id = get_archive_id_from_path(args.file)
            if not archive_id:
                return 1
        else:
            archive_id = args.id
        
        metadata = manager.get_complete_archive_metadata(archive_id)
        if not metadata:
            print(f"❌ 未找到ID为 {archive_id} 的元数据")
            return 1
        
        print(f"📊 压缩包完整元数据")
        print("=" * 50)
        
        # 基本信息
        print(f"🆔 压缩包ID: {metadata['archive_id']}")
        print(f"📅 首次创建: {metadata['first_created_at']}")
        print(f"🕒 查询时间: {metadata['current_timestamp']}")
        
        basic_info = metadata['basic_info']
        print(f"\n📄 基本信息:")
        print(f"  当前名称: {basic_info['current_name']}")
        print(f"  画师名称: {basic_info['artist_name'] or 'N/A'}")
        print(f"  文件路径: {basic_info['file_path']}")
        print(f"  文件哈希: {basic_info['file_hash'][:16]}..." if basic_info['file_hash'] else "  文件哈希: N/A")
        
        # 统计信息
        stats = metadata['statistics']
        print(f"\n📈 统计信息:")
        print(f"  总操作次数: {stats['total_operations']}")
        print(f"  重命名次数: {stats['total_renames']}")
        print(f"  使用过的名称数: {stats['unique_names']}")
        print(f"  首次操作: {stats['first_operation']}")
        print(f"  最后操作: {stats['last_operation']}")
        
        # 名称变更历史
        if metadata['name_history']:
            print(f"\n📝 名称变更历史:")
            for i, change in enumerate(metadata['name_history'], 1):
                print(f"  {i}. {change['from']} -> {change['to']}")
                print(f"     时间: {change['timestamp']}")
                print(f"     原因: {change['reason']}")
        
        # 详细操作历史
        if args.verbose and metadata['operation_history']:
            print(f"\n🔧 详细操作历史:")
            for i, op in enumerate(metadata['operation_history'], 1):
                print(f"  {i}. {op['timestamp']}")
                print(f"     操作: {op['old_name']} -> {op['new_name']}")
                print(f"     原因: {op['reason']}")
                if 'metadata' in op:
                    op_meta = op['metadata']
                    if isinstance(op_meta, dict):
                        print(f"     详情: 方法={op_meta.get('rename_method', 'N/A')}, "
                              f"大小={op_meta.get('file_size', 'N/A')}字节")
        
        # JSON输出
        if args.json:
            print(f"\n📋 JSON格式:")
            print(json.dumps(metadata, ensure_ascii=False, indent=2))
    
    return 0


def cmd_show_history(args):
    """显示名称变更历史"""
    db_path = args.database or "nameset.db"
    
    with ArchiveManager(db_path) as manager:
        if args.file:
            archive_id = get_archive_id_from_path(args.file)
            if not archive_id:
                return 1
        else:
            archive_id = args.id
        
        history = manager.get_archive_name_history(archive_id)
        if not history:
            print(f"❌ 未找到ID为 {archive_id} 的名称变更历史")
            return 1
        
        print(f"📝 名称变更历史 (ID: {archive_id})")
        print("=" * 50)
        
        for i, change in enumerate(history, 1):
            print(f"{i}. {change['timestamp']}")
            print(f"   {change['from']} -> {change['to']}")
            print(f"   原因: {change['reason']}")
            print()
    
    return 0


def cmd_show_stats(args):
    """显示统计信息"""
    db_path = args.database or "nameset.db"
    
    with ArchiveManager(db_path) as manager:
        if args.file:
            archive_id = get_archive_id_from_path(args.file)
            if not archive_id:
                return 1
        else:
            archive_id = args.id
        
        stats = manager.get_archive_statistics(archive_id)
        if not stats:
            print(f"❌ 未找到ID为 {archive_id} 的统计信息")
            return 1
        
        print(f"📈 统计信息 (ID: {archive_id})")
        print("=" * 30)
        print(f"总操作次数: {stats['total_operations']}")
        print(f"重命名次数: {stats['total_renames']}")
        print(f"使用过的名称数: {stats['unique_names']}")
        print(f"首次操作: {stats['first_operation']}")
        print(f"最后操作: {stats['last_operation']}")
    
    return 0


def cmd_search(args):
    """搜索压缩包"""
    db_path = args.database or "nameset.db"
    
    with ArchiveManager(db_path) as manager:
        results = manager.search_archives(args.query, args.artist)
        
        if not results:
            print(f"❌ 未找到匹配 '{args.query}' 的压缩包")
            return 1
        
        print(f"🔍 搜索结果: '{args.query}'")
        if args.artist:
            print(f"   画师过滤: {args.artist}")
        print("=" * 50)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['current_name']}")
            print(f"   ID: {result['id']}")
            print(f"   画师: {result['artist_name'] or 'N/A'}")
            print(f"   创建: {result['created_at']}")
            
            if args.verbose:
                # 显示统计信息
                stats = manager.get_archive_statistics(result['id'])
                if stats:
                    print(f"   操作次数: {stats['total_operations']}")
                    print(f"   重命名次数: {stats['total_renames']}")
            print()
    
    return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="压缩包元数据管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 显示文件的完整元数据
  python metadata_cli.py show /path/to/archive.zip
  
  # 显示指定ID的元数据
  python metadata_cli.py show --id ABC123DEF456
  
  # 显示名称变更历史
  python metadata_cli.py history /path/to/archive.zip
  
  # 显示统计信息
  python metadata_cli.py stats --id ABC123DEF456
  
  # 搜索压缩包
  python metadata_cli.py search "关键词" --artist "画师名"
        """
    )
    
    parser.add_argument('-d', '--database', help='数据库文件路径 (默认: nameset.db)')
    parser.add_argument('-v', '--verbose', action='store_true', help='详细输出')
    parser.add_argument('--json', action='store_true', help='JSON格式输出')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # show 命令
    show_parser = subparsers.add_parser('show', help='显示完整元数据')
    show_group = show_parser.add_mutually_exclusive_group(required=True)
    show_group.add_argument('file', nargs='?', help='压缩包文件路径')
    show_group.add_argument('--id', help='压缩包ID')
    
    # history 命令
    history_parser = subparsers.add_parser('history', help='显示名称变更历史')
    history_group = history_parser.add_mutually_exclusive_group(required=True)
    history_group.add_argument('file', nargs='?', help='压缩包文件路径')
    history_group.add_argument('--id', help='压缩包ID')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='显示统计信息')
    stats_group = stats_parser.add_mutually_exclusive_group(required=True)
    stats_group.add_argument('file', nargs='?', help='压缩包文件路径')
    stats_group.add_argument('--id', help='压缩包ID')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索压缩包')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('--artist', help='画师名称过滤')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    setup_logging(args.verbose)
    
    try:
        if args.command == 'show':
            return cmd_show_metadata(args)
        elif args.command == 'history':
            return cmd_show_history(args)
        elif args.command == 'stats':
            return cmd_show_stats(args)
        elif args.command == 'search':
            return cmd_search(args)
        else:
            print(f"❌ 未知命令: {args.command}")
            return 1
    
    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
