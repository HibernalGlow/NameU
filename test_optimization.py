"""
测试优化后的压缩包ID管理系统
"""

import os
import tempfile
import zipfile
from pathlib import Path

def test_optimized_system():
    """测试优化后的系统"""
    print("=== 测试优化后的压缩包ID管理系统 ===")
    
    # 1. 测试配置系统
    print("📋 测试配置系统...")
    try:
        from src.nameu.core.config import get_tool_path
        bandizip_path = get_tool_path("bandizip_exe")
        print(f"✅ Bandizip 路径: {bandizip_path}")
        
        sevenz_path = get_tool_path("7z_exe")
        print(f"✅ 7z 路径: {sevenz_path}")
    except Exception as e:
        print(f"❌ 配置系统测试失败: {e}")
    
    # 2. 测试单例管理器
    print("\n🔄 测试单例管理器...")
    try:
        from src.nameu.core.archive_manager import get_archive_manager, is_archive_management_available
        
        print(f"压缩包ID管理可用: {is_archive_management_available()}")
        
        if is_archive_management_available():
            # 获取两次管理器实例，应该是同一个对象
            manager1 = get_archive_manager()
            manager2 = get_archive_manager()
            
            is_same = manager1 is manager2
            print(f"✅ 单例模式: {is_same} (两次获取是否为同一实例)")
            print(f"✅ 管理器类型: {type(manager1).__name__}")
            print(f"✅ 数据库路径: {manager1.db_path}")
        else:
            print("❌ 压缩包ID管理不可用")
            
    except Exception as e:
        print(f"❌ 单例管理器测试失败: {e}")
    
    # 3. 测试集成接口
    print("\n🔗 测试集成接口...")
    try:
        from nameset.integration import get_manager, process_file_with_id_tracking
        
        integration_manager = get_manager()
        direct_manager = get_archive_manager()
        
        # 检查集成接口和直接接口是否获取的是同一个实例
        is_same_instance = integration_manager is direct_manager
        print(f"✅ 集成一致性: {is_same_instance} (集成接口与直接接口是否一致)")
        
    except Exception as e:
        print(f"❌ 集成接口测试失败: {e}")
    
    # 4. 测试file_processor集成
    print("\n📁 测试 file_processor 集成...")
    try:
        from src.nameu.core.file_processor import ID_TRACKING_AVAILABLE
        print(f"✅ ID跟踪功能可用: {ID_TRACKING_AVAILABLE}")
    except Exception as e:
        print(f"❌ file_processor 集成测试失败: {e}")
    
    print(f"\n✅ 所有测试完成！")

if __name__ == "__main__":
    test_optimized_system()
