"""
NameSet 命令行工具
独立的压缩包ID管理系统命令行接口
"""

import argparse
import sys
import os
from typing import Optional

from . import ArchiveIDManager
from .id_handler import ArchiveIDHandler
from colorama import init, Fore, Style
from loguru import logger

# 初始化colorama
init()


def show_archive_info(file_path: str):
    """显示压缩包信息"""
    if not os.path.exists(file_path):
        print(f"{Fore.RED}文件不存在: {file_path}{Style.RESET_ALL}")
        return
    
    print(f"{Fore.CYAN}压缩包信息: {os.path.basename(file_path)}{Style.RESET_ALL}")
    
    # 获取ID
    comment = ArchiveIDHandler.get_archive_comment(file_path)
    archive_id = ArchiveIDHandler.extract_id_from_comment(comment)
    
    if archive_id:
        print(f"  ID: {Fore.GREEN}{archive_id}{Style.RESET_ALL}")
        
        # 获取详细信息
        with ArchiveIDManager() as manager:
            info = manager.get_archive_info(archive_id)
            if info:
                print(f"  当前名称: {info['current_name']}")
                print(f"  画师名称: {info.get('artist_name', '未知')}")
                print(f"  创建时间: {info['created_at']}")
                print(f"  更新时间: {info['updated_at']}")
                
                # 显示历史记录
                history = manager.get_archive_history(archive_id, 5)
                if history:
                    print(f"\n  {Fore.YELLOW}最近历史记录:{Style.RESET_ALL}")
                    for record in history:
                        old_name = record['old_name'] or '(初始)'
                        print(f"    {record['timestamp']}: {old_name} -> {record['new_name']}")
                        if record['reason']:
                            print(f"      原因: {record['reason']}")
            else:
                print(f"  {Fore.YELLOW}数据库中未找到详细信息{Style.RESET_ALL}")
    else:
        print(f"  {Fore.RED}未找到ID{Style.RESET_ALL}")


def search_archives(query: str, artist_name: Optional[str] = None):
    """搜索压缩包"""
    print(f"{Fore.CYAN}搜索结果: {query}{Style.RESET_ALL}")
    if artist_name:
        print(f"  画师过滤: {artist_name}")
    
    with ArchiveIDManager() as manager:
        results = manager.search_archives(query, artist_name)
        
        if not results:
            print(f"  {Fore.YELLOW}未找到匹配的记录{Style.RESET_ALL}")
            return
        
        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {Fore.GREEN}{result['current_name']}{Style.RESET_ALL}")
            print(f"     ID: {result['id']}")
            print(f"     画师: {result.get('artist_name', '未知')}")
            print(f"     创建: {result['created_at']}")


def show_statistics():
    """显示统计信息"""
    print(f"{Fore.CYAN}NameSet 统计信息{Style.RESET_ALL}")
    
    with ArchiveIDManager() as manager:
        stats = manager.get_statistics()
        
        print(f"  总压缩包数量: {Fore.GREEN}{stats['total_archives']}{Style.RESET_ALL}")
        print(f"  总历史记录数: {Fore.GREEN}{stats['total_history_records']}{Style.RESET_ALL}")
        
        if stats['top_artists']:
            print(f"\n  {Fore.YELLOW}画师排行榜:{Style.RESET_ALL}")
            for artist in stats['top_artists'][:5]:
                print(f"    {artist['name']}: {artist['count']} 个文件")


def cleanup_database():
    """清理数据库"""
    print(f"{Fore.CYAN}正在清理数据库...{Style.RESET_ALL}")
    
    # 这里需要实现清理逻辑
    import sqlite3
    with ArchiveIDManager() as manager:
        with sqlite3.connect(manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, file_path FROM archive_info')
            all_records = cursor.fetchall()
            
            orphaned_count = 0
            for record_id, file_path in all_records:
                if not os.path.exists(file_path):
                    cursor.execute('DELETE FROM archive_info WHERE id = ?', (record_id,))
                    cursor.execute('DELETE FROM archive_history WHERE archive_id = ?', (record_id,))
                    orphaned_count += 1
                    logger.debug(f"删除孤立记录: {record_id} ({file_path})")
            
            conn.commit()
            print(f"{Fore.GREEN}清理了 {orphaned_count} 条孤立记录{Style.RESET_ALL}")


def backup_db(backup_path: Optional[str] = None):
    """备份数据库"""
    print(f"{Fore.CYAN}正在备份数据库...{Style.RESET_ALL}")
    
    import shutil
    from datetime import datetime
    
    with ArchiveIDManager() as manager:
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{manager.db_path}.backup_{timestamp}"
        
        shutil.copy2(manager.db_path, backup_path)
        print(f"{Fore.GREEN}数据库备份完成: {backup_path}{Style.RESET_ALL}")


def assign_id_to_archive(file_path: str):
    """为压缩包分配ID"""
    if not os.path.exists(file_path):
        print(f"{Fore.RED}文件不存在: {file_path}{Style.RESET_ALL}")
        return
    
    existing_id = ArchiveIDHandler.extract_id_from_comment(
        ArchiveIDHandler.get_archive_comment(file_path)
    )
    if existing_id:
        print(f"{Fore.YELLOW}压缩包已有ID: {existing_id}{Style.RESET_ALL}")
        return
    
    # 生成新ID
    new_id = ArchiveIDHandler.get_or_create_archive_id(file_path)
    if new_id:
        print(f"{Fore.GREEN}已为压缩包分配ID: {new_id}{Style.RESET_ALL}")
        
        # 创建数据库记录
        with ArchiveIDManager() as manager:
            current_name = os.path.basename(file_path)
            if manager.db.create_archive_record(new_id, file_path, current_name):
                print(f"{Fore.GREEN}数据库记录已创建{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}无法为压缩包分配ID{Style.RESET_ALL}")


def process_archive(file_path: str, new_name: str, artist_name: Optional[str] = None):
    """处理压缩包重命名"""
    if not os.path.exists(file_path):
        print(f"{Fore.RED}文件不存在: {file_path}{Style.RESET_ALL}")
        return
    
    with ArchiveIDManager() as manager:
        success, archive_id = manager.process_archive_rename(file_path, new_name, artist_name)
        
        if success:
            print(f"{Fore.GREEN}处理成功: {new_name} (ID: {archive_id}){Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}处理失败{Style.RESET_ALL}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='NameSet - 压缩包ID管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # info命令
    info_parser = subparsers.add_parser('info', help='显示压缩包信息')
    info_parser.add_argument('file', help='压缩包文件路径')
    
    # search命令
    search_parser = subparsers.add_parser('search', help='搜索压缩包')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('--artist', help='画师名称过滤')
    
    # stats命令
    subparsers.add_parser('stats', help='显示统计信息')
    
    # cleanup命令
    subparsers.add_parser('cleanup', help='清理数据库')
    
    # backup命令
    backup_parser = subparsers.add_parser('backup', help='备份数据库')
    backup_parser.add_argument('--path', help='备份文件路径')
    
    # assign命令
    assign_parser = subparsers.add_parser('assign', help='为压缩包分配ID')
    assign_parser.add_argument('file', help='压缩包文件路径')
    
    # process命令
    process_parser = subparsers.add_parser('process', help='处理压缩包重命名')
    process_parser.add_argument('file', help='压缩包文件路径')
    process_parser.add_argument('new_name', help='新文件名')
    process_parser.add_argument('--artist', help='画师名称')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'info':
            show_archive_info(args.file)
        
        elif args.command == 'search':
            search_archives(args.query, args.artist)
        
        elif args.command == 'stats':
            show_statistics()
        
        elif args.command == 'cleanup':
            cleanup_database()
        
        elif args.command == 'backup':
            backup_db(args.path)
        
        elif args.command == 'assign':
            assign_id_to_archive(args.file)
        
        elif args.command == 'process':
            process_archive(args.file, args.new_name, args.artist)
        
    except Exception as e:
        print(f"{Fore.RED}执行命令时出错: {e}{Style.RESET_ALL}")
        logger.error(f"命令执行错误: {e}")


if __name__ == "__main__":
    main()
