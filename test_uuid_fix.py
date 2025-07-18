#!/usr/bin/env python3
"""测试UUID读取修复"""

import os
import tempfile
import shutil
import subprocess

def test_uuid_extraction():
    """测试UUID提取逻辑"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 测试无文件夹结构
        zip_path = os.path.join(temp_dir, "test_no_folder.zip")

        # 创建临时文件
        json_file = os.path.join(temp_dir, "abc123.json")
        txt_file = os.path.join(temp_dir, "file.txt")

        with open(json_file, 'w') as f:
            f.write('{"test": true}')
        with open(txt_file, 'w') as f:
            f.write("content")

        subprocess.run(['7z', 'a', zip_path, json_file, txt_file],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 测试单文件夹结构
        zip_path_folder = os.path.join(temp_dir, "test_folder.zip")

        # 创建文件夹结构
        folder_path = os.path.join(temp_dir, "folder1")
        os.makedirs(folder_path, exist_ok=True)

        json_file_folder = os.path.join(folder_path, "abc123.json")
        txt_file_folder = os.path.join(folder_path, "file.txt")

        with open(json_file_folder, 'w') as f:
            f.write('{"test": true}')
        with open(txt_file_folder, 'w') as f:
            f.write("content")

        subprocess.run(['7z', 'a', zip_path_folder, folder_path],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 模拟修复后的UUID读取逻辑
        def load_json_uuid_from_archive(archive_path):
            try:
                result = subprocess.run(['7z', 'l', archive_path],
                                      capture_output=True, text=True, encoding='gbk', errors='ignore')
                for line in result.stdout.splitlines():
                    if line.strip() and not line.startswith('-') and not line.startswith('Date'):
                        parts = line.split()
                        if len(parts) >= 6:
                            name = parts[-1]
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
