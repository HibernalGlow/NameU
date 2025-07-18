import os
import tempfile
import zipfile
import shutil

def test_logic():
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建测试文件
        zip_path = os.path.join(temp_dir, "test.zip")
        json_path = os.path.join(temp_dir, "test.json")
        
        with open(json_path, 'w') as f:
            f.write('{"test": true}')
        
        # 创建单文件夹结构的zip
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(json_path, "folder1/file1.txt")
            zf.write(json_path, "folder1/file2.txt")
        
        # 分析结构
        with zipfile.ZipFile(zip_path, 'r') as zf:
            root_items = set()
            for name in zf.namelist():
                if '/' in name:
                    root_items.add(name.split('/')[0])
                else:
                    root_items.add('')
            
            if '' in root_items:
                structure = "no_folder" if len(root_items) == 1 else "multiple_folders"
            elif len(root_items) == 1:
                structure = "single_folder"
            else:
                structure = "multiple_folders"
        
        print(f"结构分析: {structure}")
        print(f"根目录项: {root_items}")
        
        # 获取文件夹名
        folder_name = None
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for name in zf.namelist():
                if '/' in name:
                    folder_name = name.split('/')[0]
                    break
        
        print(f"文件夹名: {folder_name}")
        
        # 添加新文件
        new_json_path = os.path.join(temp_dir, "new.json")
        with open(new_json_path, 'w') as f:
            f.write('{"uuid": "new-uuid"}')
        
        target_path = "new.json"
        if structure == "single_folder" and folder_name:
            target_path = f"{folder_name}/new.json"
        
        print(f"目标路径: {target_path}")
        
        with zipfile.ZipFile(zip_path, 'a') as zf:
            zf.write(new_json_path, target_path)
        
        # 验证结果
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()
            print(f"最终文件列表: {files}")
            
            if "folder1/new.json" in files:
                print("✅ 测试通过：JSON文件成功添加到单文件夹内")
                return True
            else:
                print("❌ 测试失败：JSON文件未添加到正确位置")
                return False
                
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_logic()
