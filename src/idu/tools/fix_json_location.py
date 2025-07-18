#!/usr/bin/env python3
"""
修复JSON文件位置 - 简化版本
将单文件夹结构压缩包中根目录的JSON文件移动到文件夹内
"""

import os
import zipfile
import shutil
from pathlib import Path


def analyze_zip_structure(zip_path: str) -> tuple:
    """分析ZIP结构，返回(结构类型, 文件夹名, 根目录JSON文件列表)"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            root_items = set()
            root_json_files = []
            
            for name in zf.namelist():
                if '/' in name:
                    root_items.add(name.split('/')[0])
                else:
                    root_items.add('')
                    if name.endswith('.json'):
                        root_json_files.append(name)
            
            # 判断结构类型
            if '' in root_items:
                if len(root_items) == 1:
                    structure = "no_folder"
                else:
                    structure = "multiple_folders"
            elif len(root_items) == 1:
                structure = "single_folder"
            else:
                structure = "multiple_folders"
            
            # 获取文件夹名
            folder_name = None
            if structure == "single_folder":
                for name in zf.namelist():
                    if '/' in name:
                        folder_name = name.split('/')[0]
                        break
            
            return structure, folder_name, root_json_files
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return "error", None, []


def fix_json_location(zip_path: str, create_backup: bool = True) -> bool:
    """修复JSON文件位置"""
    
    print(f"🔄 处理: {os.path.basename(zip_path)}")
    
    # 1. 分析结构
    structure, folder_name, root_json_files = analyze_zip_structure(zip_path)
    
    print(f"   结构: {structure}")
    print(f"   文件夹: {folder_name}")
    print(f"   根目录JSON: {root_json_files}")
    
    # 2. 检查是否需要处理
    if structure != "single_folder":
        print(f"   ⚠️ 跳过: 不是单文件夹结构")
        return True
    
    if not root_json_files:
        print(f"   ✅ 跳过: 根目录无JSON文件")
        return True
    
    if not folder_name:
        print(f"   ❌ 错误: 无法获取文件夹名")
        return False
    
    # 3. 创建备份
    if create_backup:
        backup_path = zip_path + ".backup"
        try:
            shutil.copy2(zip_path, backup_path)
            print(f"   💾 备份: {os.path.basename(backup_path)}")
        except Exception as e:
            print(f"   ❌ 备份失败: {e}")
            return False
    
    # 4. 重建ZIP文件
    temp_path = zip_path + ".temp"
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as old_zip:
            with zipfile.ZipFile(temp_path, 'w', compression=zipfile.ZIP_DEFLATED) as new_zip:
                
                # 复制所有非根目录JSON文件
                for item in old_zip.infolist():
                    if item.filename not in root_json_files:
                        data = old_zip.read(item.filename)
                        new_zip.writestr(item, data)
                
                # 移动根目录JSON文件到文件夹内
                for json_file in root_json_files:
                    data = old_zip.read(json_file)
                    new_path = f"{folder_name}/{json_file}"
                    
                    # 创建新的文件信息
                    new_info = zipfile.ZipInfo(new_path)
                    new_info.external_attr = 0o644 << 16
                    
                    new_zip.writestr(new_info, data)
                    print(f"   📁 移动: {json_file} -> {new_path}")
        
        # 替换原文件
        os.replace(temp_path, zip_path)
        print(f"   ✅ 完成")
        return True
        
    except Exception as e:
        print(f"   ❌ 处理失败: {e}")
        
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return False


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python fix_json_location.py <ZIP文件或目录>")
        print("示例: python fix_json_location.py archive.zip")
        print("示例: python fix_json_location.py /path/to/archives/")
        return 1
    
    target_path = sys.argv[1]
    
    if not os.path.exists(target_path):
        print(f"❌ 路径不存在: {target_path}")
        return 1
    
    print("🚀 JSON位置修复工具")
    print("=" * 50)
    
    success_count = 0
    total_count = 0
    
    if os.path.isfile(target_path):
        # 处理单个文件
        if target_path.lower().endswith('.zip'):
            total_count = 1
            if fix_json_location(target_path):
                success_count = 1
        else:
            print("❌ 只支持ZIP文件")
            return 1
    
    else:
        # 处理目录中的所有ZIP文件
        zip_files = list(Path(target_path).glob("*.zip"))
        
        if not zip_files:
            print(f"❌ 目录中未找到ZIP文件: {target_path}")
            return 1
        
        print(f"📦 找到 {len(zip_files)} 个ZIP文件")
        print()
        
        total_count = len(zip_files)
        
        for zip_file in zip_files:
            try:
                if fix_json_location(str(zip_file)):
                    success_count += 1
            except Exception as e:
                print(f"❌ 处理异常: {zip_file.name} - {e}")
            
            print()  # 空行分隔
    
    print("=" * 50)
    print(f"📊 处理结果: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("🎉 所有文件处理完成!")
        return 0
    else:
        print("⚠️ 部分文件处理失败")
        return 1


if __name__ == "__main__":
    main()
