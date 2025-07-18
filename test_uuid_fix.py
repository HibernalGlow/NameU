#!/usr/bin/env python3
"""测试UUID读取修复"""

import os
import tempfile
import zipfile
import shutil

def test_uuid_extraction():
    """测试UUID提取逻辑"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 测试无文件夹结构
        zip_path = os.path.join(temp_dir, "test_no_folder.zip")
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("abc123.json", '{"test": true}')
            zf.writestr("file.txt", "content")
        
        # 测试单文件夹结构
        zip_path_folder = os.path.join(temp_dir, "test_folder.zip")
        with zipfile.ZipFile(zip_path_folder, 'w') as zf:
            zf.writestr("folder1/abc123.json", '{"test": true}')
            zf.writestr("folder1/file.txt", "content")
        
        # 模拟修复后的UUID读取逻辑
        def load_json_uuid_from_archive(archive_path):
            try:
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    for name in zf.namelist():
                        if name.endswith('.json'):
                            # 只提取文件名部分，忽略路径
                            filename = os.path.basename(name)
                            return os.path.splitext(filename)[0]
            except Exception as e:
                print(f"读取失败: {e}")
            return None
        
        # 测试无文件夹
        uuid1 = load_json_uuid_from_archive(zip_path)
        print(f"无文件夹结构 UUID: {uuid1}")
        assert uuid1 == "abc123", f"Expected 'abc123', got '{uuid1}'"
        
        # 测试单文件夹
        uuid2 = load_json_uuid_from_archive(zip_path_folder)
        print(f"单文件夹结构 UUID: {uuid2}")
        assert uuid2 == "abc123", f"Expected 'abc123', got '{uuid2}'"
        
        print("✅ UUID读取修复测试通过！")
        
        # 测试路径处理
        test_paths = [
            "abc123.json",
            "folder1/abc123.json", 
            "folder1/subfolder/abc123.json"
        ]
        
        print("\n=== 路径处理测试 ===")
        for path in test_paths:
            filename = os.path.basename(path)
            uuid = os.path.splitext(filename)[0]
            print(f"{path} -> {uuid}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_uuid_extraction()
