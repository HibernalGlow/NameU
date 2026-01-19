
import pytest
import os
import zipfile
import subprocess
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nameset.id_handler import ArchiveIDHandler
from nameu.core.config import exclude_keywords, path_blacklist, load_config

def test_config_loading():
    """测试配置加载功能"""
    print("\n测试配置加载...")
    # 确保重新加载
    load_config()
    print(f"当前排除关键词: {exclude_keywords}")
    print(f"当前路径黑名单: {path_blacklist}")
    
    # 这里可以根据 src/nameu/nameu.toml 的内容做断言
    # 比如我们知道 [weibo] 在 forbidden_artist_keywords 中
    import nameu.core.config as config
    print(f"当前禁止画师关键词: {config.forbidden_artist_keywords}")
    assert "[weibo]" in config.forbidden_artist_keywords

def test_bandizip_commenting():
    """测试 Bandizip 设置和读取注释的功能"""
    archive_path = "test_comment.zip"
    test_comment = '{"id": "TEST_ID_123", "artist": "Tester"}'
    
    # 1. 创建一个简单的 ZIP 文件
    if os.path.exists(archive_path):
        os.remove(archive_path)
    
    with zipfile.ZipFile(archive_path, 'w') as zf:
        zf.writestr("test.txt", "hello world")
    
    try:
        # 2. 尝试设置注释
        print(f"\n正在尝试为 {archive_path} 设置注释...")
        success = ArchiveIDHandler.set_archive_comment(archive_path, test_comment)
        
        if not success:
            pytest.fail("ArchiveIDHandler.set_archive_comment 返回 False")
        
        print("设置注释成功，正在尝试读取...")
        
        # 3. 尝试读取注释
        ArchiveIDHandler.clear_comment_cache()
        read_comment = ArchiveIDHandler.get_archive_comment(archive_path)
        
        print(f"读取到的注释: {read_comment}")
        
        assert read_comment is not None
        assert "TEST_ID_123" in read_comment
        
    finally:
        # 清理
        if os.path.exists(archive_path):
            os.remove(archive_path)

if __name__ == "__main__":
    # 直接运行以便看到打印输出
    try:
        test_bandizip_commenting()
        print("\n测试通过!")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
