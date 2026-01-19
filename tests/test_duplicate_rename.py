
import pytest
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nameu.core import filename_processor

def test_duplicate_handling_with_suffix():
    """测试重名处理逻辑，应使用 (n) 格式"""
    directory = "test_dup_dir"
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    filename = "test_file.zip"
    full_path = os.path.join(directory, filename)
    
    # 创建第一个文件
    with open(full_path, 'w') as f:
        f.write("test")
    
    # 创建一个模拟原始文件
    original_path = os.path.join(directory, "original.zip")
    with open(original_path, 'w') as f:
        f.write("original")
    
    try:
        # 1. 再次获取同一个文件名的唯一名 (应生成 (1))
        # 我们传入 original_path 指向另一个文件，模拟重名
        unique_name = filename_processor.get_unique_filename_with_samename(directory, filename, original_path=original_path)
        print(f"Unique name for duplicate: {unique_name}")
        assert unique_name == "test_file (1).zip"
        
        # 2. 如果文件已经存在 (1)，应生成 (2)
        with open(os.path.join(directory, "test_file (1).zip"), 'w') as f:
            f.write("test")
            
        unique_name_2 = filename_processor.get_unique_filename_with_samename(directory, filename, original_path=original_path)
        print(f"Unique name for duplicate 2: {unique_name_2}")
        assert unique_name_2 == "test_file (2).zip"
        
        # 3. 测试清理逻辑
        input_name = "test_file (1).zip"
        normalized = filename_processor.normalize_filename(input_name)
        print(f"Normalized '{input_name}': {normalized}")
        assert normalized == "test_file"
        
        old_input = "test_file[samename_5].zip"
        normalized_old = filename_processor.normalize_filename(old_input)
        print(f"Normalized old '{old_input}': {normalized_old}")
        assert normalized_old == "test_file"

    finally:
        # 清理
        import shutil
        shutil.rmtree(directory)

if __name__ == "__main__":
    try:
        test_duplicate_handling_with_suffix()
        print("\nDuplicate handling test passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
