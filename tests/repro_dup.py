
import os
import shutil
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from nameu.core import file_processor

def test_serial_batch_conflict():
    """测试串行模式下的批量重命名冲突"""
    test_dir = "test_serial_conflict"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 场景：两个文件，经过格式化后都想变成相同的名字
    # a.zip -> target.zip
    # b.zip -> target.zip
    # 注意：我们需要构造能让 get_unique_filename 输出相同结果的输入
    
    # 比如：[Artist] a {123}.zip  -> [Artist] a.zip
    #      [Artist] a {456}.zip  -> [Artist] a.zip
    
    file1 = os.path.join(test_dir, "test {1}.zip")
    file2 = os.path.join(test_dir, "test {2}.zip")
    
    with open(file1, 'w') as f: f.write("1")
    with open(file2, 'w') as f: f.write("2")
    
    print(f"\nRunning process_files_in_directory (threads=1) on {test_dir}")
    # threads=1 强制走串行逻辑
    file_processor.process_files_in_directory(test_dir, "[Artist]", threads=1)
    
    # 检查结果
    files = os.listdir(test_dir)
    print(f"Files after processing: {files}")
    
    # 预期：一个是 test.zip (或 [Artist] test.zip)，另一个是 ... (1).zip
    # 如果有 bug，可能会报错或者两个都尝试改名导致其中一个失败
    
    has_target = any("test" in f and " (1)" not in f for f in files)
    has_suffix = any(" (1)" in f for f in files)
    
    if not (has_target and has_suffix):
        print("❌ FAILED: Duplicate detection in serial mode failed to produce (1) suffix.")
    else:
        print("✅ SUCCESS: Duplicate detection handled the batch (or at least one of them got a suffix).")

def test_folder_rename_conflict():
    """测试文件夹重命名冲突"""
    test_root = "test_folder_conflict"
    if os.path.exists(test_root):
        shutil.rmtree(test_root)
    os.makedirs(test_root)
    
    artist_dir = os.path.join(test_root, "Artist")
    os.makedirs(artist_dir)
    
    # 两个文件夹，格式化后名字相同
    sub1 = os.path.join(artist_dir, "Folder 1")
    sub2 = os.path.join(artist_dir, "Folder  1") # 多一个空格
    os.makedirs(sub1)
    os.makedirs(sub2)
    
    print(f"\nRunning process_artist_folder on {artist_dir}")
    file_processor.process_artist_folder(artist_dir, "[Artist]")
    
    # 检查结果
    dirs = os.listdir(artist_dir)
    print(f"Folders after processing: {dirs}")
    
    if len(dirs) != 2:
         print(f"❌ FAILED: One folder might have been lost or overwritten? {dirs}")
    elif "Folder 1" in dirs and any(" (1)" in d for d in dirs):
         print("✅ SUCCESS: Folder duplicates handled.")
    else:
         print("❌ FAILED: Folders still same or conflict not handled gracefully.")

if __name__ == "__main__":
    try:
        test_serial_batch_conflict()
        test_folder_rename_conflict()
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
