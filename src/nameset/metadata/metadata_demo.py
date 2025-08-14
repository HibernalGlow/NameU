#!/usr/bin/env python3
"""
增强元数据功能演示脚本
展示如何使用完整的历史追溯功能
"""

import os
import sys
import tempfile
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from nameset.manager import ArchiveIDManager
from nameset.database import ArchiveDatabase
from loguru import logger


def create_test_archive(temp_dir: str, name: str) -> str:
    """创建测试用的压缩包文件"""
    archive_path = os.path.join(temp_dir, name)
    with open(archive_path, 'wb') as f:
        f.write(b'PK\x03\x04')  # ZIP文件头
        f.write(b'test content for ' + name.encode())
    return archive_path


def demo_complete_metadata_tracking():
    """演示完整的元数据追踪功能"""
    print("🔍 演示：完整元数据追踪功能")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "metadata_demo.db")
        
        with ArchiveIDManager(db_path) as manager:
            # 创建测试文件
            original_name = "artist_work_v1.zip"
            archive_path = create_test_archive(temp_dir, original_name)
            
            print(f"📁 创建测试文件: {original_name}")
            
            # 第一次重命名 - 添加画师信息
            new_name1 = "sakura_artist_work_v1.zip"
            success, archive_id = manager.process_archive_rename(
                archive_path, new_name1, artist_name="Sakura"
            )
            
            if success:
                print(f"✅ 第一次重命名成功: {original_name} -> {new_name1}")
                print(f"🆔 分配ID: {archive_id}")
                
                # 更新文件路径
                archive_path = os.path.join(temp_dir, new_name1)
                
                # 第二次重命名 - 版本更新
                new_name2 = "sakura_artist_work_v2_final.zip"
                success2, _ = manager.process_archive_rename(
                    archive_path, new_name2, artist_name="Sakura"
                )
                
                if success2:
                    print(f"✅ 第二次重命名成功: {new_name1} -> {new_name2}")
                    archive_path = os.path.join(temp_dir, new_name2)
                    
                    # 第三次重命名 - 分类整理
                    new_name3 = "[Sakura] artist_work_collection_2024.zip"
                    success3, _ = manager.process_archive_rename(
                        archive_path, new_name3, artist_name="Sakura"
                    )
                    
                    if success3:
                        print(f"✅ 第三次重命名成功: {new_name2} -> {new_name3}")
                        
                        # 获取完整的元数据
                        print(f"\n📊 获取完整历史元数据:")
                        complete_metadata = manager.get_complete_archive_metadata(archive_id)
                        
                        if complete_metadata:
                            print_metadata_summary(complete_metadata)
                            
                            # 获取名称变更历史
                            print(f"\n📝 名称变更历史:")
                            name_history = manager.get_archive_name_history(archive_id)
                            for i, change in enumerate(name_history, 1):
                                print(f"  {i}. {change['from']} -> {change['to']}")
                                print(f"     时间: {change['timestamp']}")
                                print(f"     原因: {change['reason']}")
                                print()
                            
                            # 获取统计信息
                            print(f"📈 统计信息:")
                            stats = manager.get_archive_statistics(archive_id)
                            if stats:
                                print(f"  总操作次数: {stats['total_operations']}")
                                print(f"  重命名次数: {stats['total_renames']}")
                                print(f"  使用过的名称数: {stats['unique_names']}")
                                print(f"  首次操作: {stats['first_operation']}")
                                print(f"  最后操作: {stats['last_operation']}")


def print_metadata_summary(metadata: dict):
    """打印元数据摘要"""
    print(f"  🆔 压缩包ID: {metadata.get('archive_id', 'N/A')}")
    print(f"  📅 首次创建: {metadata.get('first_created_at', 'N/A')}")
    print(f"  🕒 当前时间: {metadata.get('current_timestamp', 'N/A')}")
    
    basic_info = metadata.get('basic_info', {})
    print(f"  📄 当前名称: {basic_info.get('current_name', 'N/A')}")
    print(f"  🎨 画师名称: {basic_info.get('artist_name', 'N/A')}")
    print(f"  📂 文件路径: {basic_info.get('file_path', 'N/A')}")
    print(f"  🔐 文件哈希: {basic_info.get('file_hash', 'N/A')[:8]}..." if basic_info.get('file_hash') else "  🔐 文件哈希: N/A")
    
    current_op = metadata.get('current_operation', {})
    if current_op:
        print(f"  🔧 当前操作: {current_op.get('operation_type', 'N/A')}")
        print(f"  📏 文件大小: {current_op.get('file_size', 'N/A')} 字节")
        print(f"  📎 文件扩展名: {current_op.get('file_extension', 'N/A')}")


def demo_metadata_persistence():
    """演示元数据持久化和恢复"""
    print(f"\n🔄 演示：元数据持久化和恢复")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "persistence_demo.db")
        
        # 第一阶段：创建和修改
        archive_id = None
        with ArchiveIDManager(db_path) as manager:
            archive_path = create_test_archive(temp_dir, "test_persistence.zip")
            
            success, archive_id = manager.process_archive_rename(
                archive_path, "renamed_persistence.zip", artist_name="TestArtist"
            )
            
            if success:
                print(f"✅ 创建记录，ID: {archive_id}")
        
        # 第二阶段：重新打开数据库，验证数据持久化
        if archive_id:
            with ArchiveIDManager(db_path) as manager:
                metadata = manager.get_complete_archive_metadata(archive_id)
                
                if metadata:
                    print(f"✅ 成功恢复元数据")
                    print(f"  画师: {metadata['basic_info']['artist_name']}")
                    print(f"  创建时间: {metadata['first_created_at']}")
                    print(f"  操作历史: {len(metadata['operation_history'])} 条记录")
                else:
                    print(f"❌ 无法恢复元数据")


def demo_search_with_metadata():
    """演示基于元数据的搜索功能"""
    print(f"\n🔍 演示：基于元数据的搜索功能")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "search_demo.db")
        
        with ArchiveIDManager(db_path) as manager:
            # 创建多个测试文件
            test_files = [
                ("artist1_work1.zip", "Artist1"),
                ("artist1_work2.zip", "Artist1"),
                ("artist2_work1.zip", "Artist2"),
                ("collaboration_work.zip", "Artist1"),
            ]
            
            archive_ids = []
            for filename, artist in test_files:
                archive_path = create_test_archive(temp_dir, filename)
                success, archive_id = manager.process_archive_rename(
                    archive_path, filename, artist_name=artist
                )
                if success:
                    archive_ids.append(archive_id)
                    print(f"✅ 创建: {filename} (画师: {artist})")
            
            # 搜索测试
            print(f"\n🔍 搜索 'Artist1' 的作品:")
            results = manager.search_archives("work", "Artist1")
            for result in results:
                print(f"  - {result['current_name']} (ID: {result['id']})")
                
                # 获取详细元数据
                metadata = manager.get_complete_archive_metadata(result['id'])
                if metadata:
                    stats = metadata.get('statistics', {})
                    print(f"    操作次数: {stats.get('total_operations', 0)}")


if __name__ == "__main__":
    print("🚀 增强元数据功能演示")
    print("=" * 60)
    
    try:
        demo_complete_metadata_tracking()
        demo_metadata_persistence()
        demo_search_with_metadata()
        
        print(f"\n✅ 所有演示完成！")
        print(f"\n💡 新功能特点:")
        print(f"   - metadata 字段现在包含完整的历史信息")
        print(f"   - 可以追溯所有名称变更历史")
        print(f"   - 保留第一时间记录和画师信息")
        print(f"   - 提供统计信息和操作历史")
        print(f"   - 支持完整的数据恢复和追溯")
        
    except Exception as e:
        logger.error(f"演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
