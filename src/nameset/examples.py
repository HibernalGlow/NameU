"""
压缩包ID管理系统使用示例
"""

import os
import tempfile
import zipfile
from nameset import ArchiveIDManager


def example_basic_usage():
    """基本使用示例"""
    print("=== 基本使用示例 ===")
    
    # 创建临时目录用于演示
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. 创建测试压缩包
        archive_path = os.path.join(temp_dir, "example_archive.zip")
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr('image1.jpg', b'fake image data')
            zf.writestr('image2.png', b'fake image data')
            zf.writestr('info.txt', 'This is a test archive')
        
        print(f"✅ 创建测试压缩包: {os.path.basename(archive_path)}")
        
        # 2. 初始化ID管理器
        db_path = os.path.join(temp_dir, "archives.db")
        with ArchiveIDManager(db_path) as manager:
            print(f"✅ 初始化ID管理器: {db_path}")
            
            # 3. 处理重命名（模拟nameu的工作流程）
            new_name = "[Artist] Formatted Title.zip"
            success, archive_id = manager.process_archive_rename(
                archive_path=archive_path,
                new_name=new_name,
                artist_name="Artist"
            )
            
            if success:
                print(f"✅ 重命名成功: {new_name}")
                print(f"📝 分配的ID: {archive_id}")
                
                # 4. 查看压缩包信息
                info = manager.get_archive_info(archive_id)
                if info:
                    print(f"📊 压缩包信息:")
                    print(f"   - ID: {info['id']}")
                    print(f"   - 当前名称: {info['current_name']}")
                    print(f"   - 画师: {info.get('artist_name', '未知')}")
                    print(f"   - 创建时间: {info['created_at']}")
                
                # 5. 查看历史记录
                history = manager.get_archive_history(archive_id)
                if history:
                    print(f"📚 历史记录 ({len(history)} 条):")
                    for record in history:
                        print(f"   - {record['timestamp']}: {record['old_name']} -> {record['new_name']}")
            else:
                print(f"❌ 重命名失败")


def example_search_and_stats():
    """搜索和统计示例"""
    print("\n=== 搜索和统计示例 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "archives.db")
        with ArchiveIDManager(db_path) as manager:
            
            # 创建多个测试压缩包
            test_files = [
                ("artist1_work1.zip", "Artist1"),
                ("artist1_work2.zip", "Artist1"),
                ("artist2_collection.zip", "Artist2"),
                ("misc_archive.zip", None),
            ]
            
            archive_ids = []
            for filename, artist in test_files:
                archive_path = os.path.join(temp_dir, filename)
                with zipfile.ZipFile(archive_path, 'w') as zf:
                    zf.writestr('content.txt', f'Content for {filename}')
                
                success, archive_id = manager.process_archive_rename(
                    archive_path, filename, artist
                )
                if success:
                    archive_ids.append(archive_id)
                    print(f"✅ 处理: {filename} (ID: {archive_id})")
            
            # 搜索示例
            print(f"\n🔍 搜索示例:")
            results = manager.search_archives("artist1")
            print(f"搜索 'artist1': 找到 {len(results)} 个结果")
            for result in results:
                print(f"   - {result['current_name']} (画师: {result.get('artist_name', '未知')})")
            
            # 统计信息
            print(f"\n📊 统计信息:")
            stats = manager.get_statistics()
            print(f"   - 总压缩包数: {stats['total_archives']}")
            print(f"   - 总历史记录: {stats['total_history_records']}")
            if stats['top_artists']:
                print(f"   - 热门画师:")
                for artist in stats['top_artists'][:3]:
                    print(f"     * {artist['name']}: {artist['count']} 个文件")


def example_id_persistence():
    """ID持久化示例"""
    print("\n=== ID持久化示例 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建压缩包
        archive_path = os.path.join(temp_dir, "persistent_test.zip")
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr('test.txt', 'Persistence test')
        
        db_path = os.path.join(temp_dir, "archives.db")
        
        # 第一次处理
        manager1 = ArchiveIDManager(db_path)
        success1, archive_id1 = manager1.process_archive_rename(
            archive_path, "renamed_v1.zip", "TestArtist"
        )
        print(f"✅ 第一次处理: ID = {archive_id1}")
        
        # 第二次处理（模拟重启或再次运行）
        new_path = os.path.join(temp_dir, "renamed_v1.zip")
        manager2 = ArchiveIDManager(db_path)
        success2, archive_id2 = manager2.process_archive_rename(
            new_path, "renamed_v2.zip", "TestArtist"
        )
        print(f"✅ 第二次处理: ID = {archive_id2}")
        
        # 验证ID一致性
        if archive_id1 == archive_id2:
            print(f"🎉 ID持久化成功: 两次处理使用相同ID")
            
            # 查看完整历史
            history = manager2.get_archive_history(archive_id1)
            print(f"📚 完整历史记录:")
            for i, record in enumerate(history, 1):
                print(f"   {i}. {record['timestamp']}: {record['old_name']} -> {record['new_name']}")
        else:
            print(f"❌ ID持久化失败: 两次处理使用了不同的ID")


def example_error_recovery():
    """错误恢复示例"""
    print("\n=== 错误恢复示例 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "archives.db")
        manager = ArchiveIDManager(db_path)
        
        # 模拟文件被移动的情况
        original_path = os.path.join(temp_dir, "original.zip")
        moved_path = os.path.join(temp_dir, "moved.zip")
        
        # 创建并首次处理
        with zipfile.ZipFile(original_path, 'w') as zf:
            zf.writestr('content.txt', 'Recovery test')
        
        success1, archive_id = manager.process_archive_rename(
            original_path, "processed.zip", "TestArtist"
        )
        processed_path = os.path.join(temp_dir, "processed.zip")
        print(f"✅ 首次处理: {archive_id}")
        
        # 模拟文件被移动
        os.rename(processed_path, moved_path)
        print(f"📁 文件已移动: processed.zip -> moved.zip")
        
        # 再次处理（应该能够通过文件哈希匹配）
        success2, archive_id2 = manager.process_archive_rename(
            moved_path, "recovered.zip", "TestArtist"
        )
        
        if archive_id == archive_id2:
            print(f"🔄 恢复成功: 通过文件哈希匹配到原有记录")
            
            # 查看历史记录
            history = manager.get_archive_history(archive_id)
            print(f"📚 历史记录显示文件路径变化:")
            for record in history:
                if record['metadata']:
                    import json
                    metadata = json.loads(record['metadata'])
                    if 'file_path' in metadata:
                        print(f"   - 路径: {metadata['file_path']}")
        else:
            print(f"❌ 恢复失败: 未能匹配原有记录")


if __name__ == "__main__":
    print("🚀 压缩包ID管理系统使用示例\n")
    
    example_basic_usage()
    example_search_and_stats()
    example_id_persistence()
    example_error_recovery()
    
    print(f"\n✅ 所有示例演示完成！")
    print(f"\n💡 提示:")
    print(f"   - 在实际使用中，数据库会保存在项目根目录")
    print(f"   - nameu会自动集成这个ID管理系统")
    print(f"   - 使用 'archive-id' 命令行工具管理压缩包ID")
