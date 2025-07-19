"""
压缩包ID管理系统测试脚本
"""

import os
import tempfile
import shutil
import zipfile
from pathlib import Path

from ..nameset.manager import ArchiveIDManager
from ..nameset.id_handler import ArchiveIDHandler
from ..nameset.database import ArchiveDatabase


def create_test_archive(path: str, name: str) -> str:
    """创建测试压缩包"""
    archive_path = os.path.join(path, name)
    
    with zipfile.ZipFile(archive_path, 'w') as zf:
        # 添加一些测试文件
        zf.writestr('test1.txt', 'Test content 1')
        zf.writestr('test2.txt', 'Test content 2')
        zf.writestr('folder/test3.txt', 'Test content 3')
    
    return archive_path


def test_id_handler():
    """测试ID处理器"""
    print("🧪 测试ID处理器...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建测试压缩包
        archive_path = create_test_archive(temp_dir, "test_archive.zip")
        
        # 测试ID生成
        new_id = ArchiveIDHandler.generate_id()
        print(f"  ✅ 生成ID: {new_id}")
        
        # 测试设置注释
        comment = ArchiveIDHandler.create_comment_with_id(new_id, {"test": True})
        success = ArchiveIDHandler.set_archive_comment(archive_path, comment)
        print(f"  ✅ 设置注释: {'成功' if success else '失败'}")
        
        # 测试获取注释
        retrieved_comment = ArchiveIDHandler.get_archive_comment(archive_path)
        print(f"  ✅ 获取注释: {'成功' if retrieved_comment else '失败'}")
        
        # 测试提取ID
        extracted_id = ArchiveIDHandler.extract_id_from_comment(retrieved_comment)
        print(f"  ✅ 提取ID: {extracted_id} {'✓' if extracted_id == new_id else '✗'}")


def test_database():
    """测试数据库"""
    print("\n🗄️ 测试数据库...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        db = ArchiveDatabase(db_path)
        
        # 测试创建记录
        test_id = "test123"
        test_path = "/test/path.zip"
        success = db.create_archive_record(test_id, test_path, "test.zip", "TestArtist")
        print(f"  ✅ 创建记录: {'成功' if success else '失败'}")
        
        # 测试获取信息
        info = db.get_archive_info(test_id)
        print(f"  ✅ 获取信息: {'成功' if info else '失败'}")
        
        # 测试更新名称
        success = db.update_archive_name(test_id, "new_name.zip", "test.zip", "测试重命名")
        print(f"  ✅ 更新名称: {'成功' if success else '失败'}")
        
        # 测试历史记录
        history = db.get_archive_history(test_id)
        print(f"  ✅ 历史记录: {len(history)} 条")
        
        # 测试搜索
        results = db.find_archive_by_name("test", "TestArtist")
        print(f"  ✅ 搜索结果: {len(results)} 条")


def test_manager():
    """测试管理器"""
    print("\n🎛️ 测试管理器...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        manager = ArchiveIDManager(db_path)
        
        # 创建测试压缩包
        archive_path = create_test_archive(temp_dir, "test_archive.zip")
        
        # 测试重命名处理
        success, archive_id = manager.process_archive_rename(
            archive_path, "renamed_archive.zip", "TestArtist"
        )
        print(f"  ✅ 重命名处理: {'成功' if success else '失败'} (ID: {archive_id})")
        
        if archive_id:
            # 测试获取信息
            info = manager.get_archive_info(archive_id)
            print(f"  ✅ 获取信息: {'成功' if info else '失败'}")
            
            # 测试历史记录
            history = manager.get_archive_history(archive_id)
            print(f"  ✅ 历史记录: {len(history)} 条")
            
            # 测试统计信息
            stats = manager.get_statistics()
            print(f"  ✅ 统计信息: {stats['total_archives']} 个压缩包")


def test_integration():
    """测试集成功能"""
    print("\n🔗 测试集成功能...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建多个测试压缩包
        archives = []
        for i in range(3):
            archive_path = create_test_archive(temp_dir, f"archive_{i}.zip")
            archives.append(archive_path)
        
        # 导入集成模块
        from ..nameset.integration import (
            process_file_with_id_tracking, get_archive_id_from_file,
            get_archive_statistics, init_archive_id_system
        )
        
        # 初始化系统
        db_path = os.path.join(temp_dir, "integration_test.db")
        init_archive_id_system(db_path)
        print(f"  ✅ 系统初始化: 完成")
        
        # 测试文件处理
        for i, archive_path in enumerate(archives):
            new_name = f"processed_archive_{i}.zip"
            success = process_file_with_id_tracking(archive_path, new_name, f"Artist{i}")
            print(f"  ✅ 处理文件 {i}: {'成功' if success else '失败'}")
            
            # 验证ID
            new_path = os.path.join(os.path.dirname(archive_path), new_name)
            if os.path.exists(new_path):
                archive_id = get_archive_id_from_file(new_path)
                print(f"    📄 文件ID: {archive_id}")
        
        # 测试统计
        stats = get_archive_statistics()
        print(f"  ✅ 最终统计: {stats}")


def test_error_handling():
    """测试错误处理"""
    print("\n🚨 测试错误处理...")
    
    # 测试不存在的文件
    result = ArchiveIDHandler.get_archive_comment("/nonexistent/file.zip")
    print(f"  ✅ 不存在文件: {'正确返回None' if result is None else '错误'}")
    
    # 测试无效注释
    invalid_id = ArchiveIDHandler.extract_id_from_comment("invalid comment")
    print(f"  ✅ 无效注释: {'正确返回None' if invalid_id is None else '错误'}")
    
    # 测试JSON格式注释
    json_comment = '{"id": "json_test_id", "other": "data"}'
    json_id = ArchiveIDHandler.extract_id_from_comment(json_comment)
    print(f"  ✅ JSON注释: {'成功' if json_id == 'json_test_id' else '失败'}")
    
    # 测试简单格式注释
    simple_comment = "ID: simple_test_id\nother info"
    simple_id = ArchiveIDHandler.extract_id_from_comment(simple_comment)
    print(f"  ✅ 简单注释: {'成功' if simple_id == 'simple_test_id' else '失败'}")


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始压缩包ID管理系统测试...\n")
    
    try:
        test_id_handler()
        test_database()
        test_manager()
        test_integration()
        test_error_handling()
        
        print(f"\n✅ 所有测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
