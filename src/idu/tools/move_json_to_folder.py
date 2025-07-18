#!/usr/bin/env python3
"""
移动压缩包内JSON文件脚本
将单文件夹结构压缩包中根目录的JSON文件移动到文件夹内
"""

import os
import sys
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional

# 添加项目路径

from idu.core.archive_handler import ArchiveHandler

def find_root_json_files(archive_path: str) -> List[str]:
    """查找压缩包根目录的JSON文件"""
    json_files = []
    
    try:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            for name in zf.namelist():
                # 只查找根目录的JSON文件（不包含路径分隔符）
                if name.endswith('.json') and '/' not in name:
                    json_files.append(name)
    except Exception as e:
        print(f"❌ 读取压缩包失败: {e}")
    
    return json_files


def move_json_to_folder(archive_path: str, backup: bool = True) -> bool:
    """
    将单文件夹结构压缩包中根目录的JSON文件移动到文件夹内
    
    Args:
        archive_path: 压缩包路径
        backup: 是否创建备份
        
    Returns:
        bool: 是否成功
    """
    
    # 1. 检查压缩包结构
    structure = ArchiveHandler._analyze_folder_structure(archive_path)
    if structure != "single_folder":
        print(f"❌ 跳过：{os.path.basename(archive_path)} - 不是单文件夹结构 ({structure})")
        return False
    
    # 2. 获取文件夹名
    folder_name = ArchiveHandler._get_single_folder_name(archive_path)
    if not folder_name:
        print(f"❌ 跳过：{os.path.basename(archive_path)} - 无法获取文件夹名")
        return False
    
    # 3. 查找根目录的JSON文件
    root_json_files = find_root_json_files(archive_path)
    if not root_json_files:
        print(f"✅ 跳过：{os.path.basename(archive_path)} - 根目录无JSON文件")
        return True
    
    print(f"🔄 处理：{os.path.basename(archive_path)}")
    print(f"   文件夹：{folder_name}")
    print(f"   根目录JSON文件：{root_json_files}")
    
    # 4. 创建备份
    if backup:
        backup_path = archive_path + ".backup"
        try:
            shutil.copy2(archive_path, backup_path)
            print(f"   ✅ 备份创建：{os.path.basename(backup_path)}")
        except Exception as e:
            print(f"   ❌ 备份失败：{e}")
            return False
    
    # 5. 重建压缩包
    temp_zip_path = archive_path + ".temp"
    
    try:
        with zipfile.ZipFile(archive_path, 'r') as old_zf:
            with zipfile.ZipFile(temp_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as new_zf:
                
                # 复制所有非根目录JSON文件
                for item in old_zf.infolist():
                    if item.filename not in root_json_files:
                        data = old_zf.read(item.filename)
                        new_zf.writestr(item, data)
                
                # 将根目录JSON文件移动到文件夹内
                for json_file in root_json_files:
                    data = old_zf.read(json_file)
                    new_path = f"{folder_name}/{json_file}"
                    
                    # 创建新的ZipInfo
                    new_info = zipfile.ZipInfo(new_path)
                    new_info.external_attr = 0o644 << 16  # 设置文件权限
                    
                    new_zf.writestr(new_info, data)
                    print(f"   📁 移动：{json_file} -> {new_path}")
        
        # 替换原文件
        os.replace(temp_zip_path, archive_path)
        print(f"   ✅ 完成：{os.path.basename(archive_path)}")
        return True
        
    except Exception as e:
        print(f"   ❌ 处理失败：{e}")
        
        # 清理临时文件
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        
        return False


def process_directory(directory: str, backup: bool = True) -> Tuple[int, int]:
    """
    批量处理目录中的压缩包
    
    Args:
        directory: 目录路径
        backup: 是否创建备份
        
    Returns:
        Tuple[int, int]: (成功数量, 总数量)
    """
    
    # 查找所有压缩包文件
    archive_extensions = ['.zip', '.7z', '.rar']
    archive_files = []
    
    for ext in archive_extensions:
        archive_files.extend(Path(directory).glob(f"*{ext}"))
        archive_files.extend(Path(directory).glob(f"**/*{ext}"))  # 递归查找
    
    if not archive_files:
        print(f"❌ 目录中未找到压缩包文件：{directory}")
        return 0, 0
    
    print(f"📦 找到 {len(archive_files)} 个压缩包文件")
    print("=" * 60)
    
    success_count = 0
    
    for archive_file in archive_files:
        archive_path = str(archive_file)
        
        # 只处理ZIP文件（其他格式需要额外工具）
        if not archive_path.lower().endswith('.zip'):
            print(f"⚠️ 跳过：{os.path.basename(archive_path)} - 仅支持ZIP格式")
            continue
        
        try:
            if move_json_to_folder(archive_path, backup):
                success_count += 1
        except Exception as e:
            print(f"❌ 处理异常：{os.path.basename(archive_path)} - {e}")
        
        print()  # 空行分隔
    
    return success_count, len([f for f in archive_files if str(f).lower().endswith('.zip')])


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="移动压缩包内JSON文件到单文件夹")
    parser.add_argument('path', help='压缩包文件或目录路径')
    parser.add_argument('--no-backup', action='store_true', help='不创建备份')
    parser.add_argument('--dry-run', action='store_true', help='只检查，不实际操作')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"❌ 路径不存在：{args.path}")
        return 1
    
    backup = not args.no_backup
    
    print("🚀 JSON文件移动工具")
    print("=" * 60)
    print(f"目标路径：{args.path}")
    print(f"创建备份：{'是' if backup else '否'}")
    print(f"预览模式：{'是' if args.dry_run else '否'}")
    print("=" * 60)
    
    if args.dry_run:
        print("⚠️ 预览模式：只检查结构，不实际修改文件")
        print()
    
    try:
        if os.path.isfile(args.path):
            # 处理单个文件
            if args.dry_run:
                structure = ArchiveHandler._analyze_folder_structure(args.path)
                folder_name = ArchiveHandler._get_single_folder_name(args.path)
                root_jsons = find_root_json_files(args.path)
                
                print(f"文件：{os.path.basename(args.path)}")
                print(f"结构：{structure}")
                print(f"文件夹：{folder_name}")
                print(f"根目录JSON：{root_jsons}")
                
                if structure == "single_folder" and root_jsons:
                    print("✅ 符合处理条件")
                else:
                    print("❌ 不符合处理条件")
            else:
                success = move_json_to_folder(args.path, backup)
                return 0 if success else 1
                
        else:
            # 处理目录
            if args.dry_run:
                print("🔍 预览模式：扫描目录...")
                # 这里可以添加预览逻辑
                return 0
            else:
                success_count, total_count = process_directory(args.path, backup)
                
                print("=" * 60)
                print(f"📊 处理完成：{success_count}/{total_count} 成功")
                
                if success_count == total_count:
                    print("🎉 所有文件处理成功！")
                    return 0
                else:
                    print("⚠️ 部分文件处理失败")
                    return 1
    
    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        return 1
    except Exception as e:
        print(f"❌ 程序异常：{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
