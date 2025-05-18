"""
文件处理模块，提供文件和文件夹处理功能
"""

import os
import logging
from tqdm import tqdm
from .constants import ARCHIVE_EXTENSIONS, exclude_keywords, forbidden_artist_keywords
from .filename_processor import (
    detect_and_decode_filename, get_unique_filename, get_unique_filename_with_samename,
    format_folder_name, has_artist_name
)

def process_files_in_directory(directory, artist_name, add_artist_name_enabled=True):
    """
    处理目录下的所有文件
    
    Args:
        directory: 目录路径
        artist_name: 画师名称
        add_artist_name_enabled: 是否添加画师名
        
    Returns:
        int: 修改的文件数量
    """
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f)) and f.lower().endswith(ARCHIVE_EXTENSIONS)]
    
    modified_files_count = 0
    
    # 检查是否是排除的文件夹（仅用于决定是否添加画师名）
    is_excluded = any(keyword in directory for keyword in exclude_keywords)
    
    # 检查是否包含禁止画师名的关键词
    has_forbidden = any(keyword in directory for keyword in forbidden_artist_keywords)
    
    # 先检查是否有需要修改的文件
    files_to_modify = []
    for filename in files:
        original_file_path = os.path.join(directory, filename)
        filename = detect_and_decode_filename(filename)
        new_filename = filename
        
        # 对所有文件应用格式化，包括排除文件夹中的文件
        new_filename = get_unique_filename(directory, new_filename, artist_name, is_excluded)
        
        # 只有在非排除文件夹、启用了画师名添加、不包含禁止关键词时才添加画师名
        if not is_excluded and not has_forbidden and add_artist_name_enabled and artist_name not in exclude_keywords and not has_artist_name(new_filename, artist_name):
            # 将画师名追加到文件名末尾
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}{artist_name}{ext}"
        
        # 确保文件名唯一（始终传入原始路径以排除自身）
        final_filename = get_unique_filename_with_samename(directory, new_filename, original_file_path)
        
        if final_filename != filename:
            files_to_modify.append((filename, final_filename, original_file_path))

    # 如果有文件需要修改，显示进度条并处理
    if files_to_modify:
        with tqdm(total=len(files_to_modify), desc=f"重命名文件", unit="file", ncols=0, leave=True) as pbar:
            for filename, new_filename, original_file_path in files_to_modify:
                # 获取原始文件的时间戳
                original_stat = os.stat(original_file_path)
                
                new_file_path = os.path.join(directory, new_filename)
                
                try:
                    # 重命名文件
                    os.rename(original_file_path, new_file_path)
                    
                    # 恢复时间戳
                    os.utime(new_file_path, (original_stat.st_atime, original_stat.st_mtime))
                    
                    try:
                        # 尝试获取相对路径以便更清晰的日志显示
                        base_path = os.path.dirname(os.path.dirname(directory))
                        rel_old_path = os.path.relpath(original_file_path, base_path)
                        rel_new_path = os.path.relpath(new_file_path, base_path)
                    except ValueError:
                        rel_old_path = original_file_path
                        rel_new_path = new_file_path
                        
                    log_message = f"重命名: {rel_old_path} -> {rel_new_path}"
                    logging.info(log_message)
                except OSError as e:
                    logging.error(f"重命名文件失败 {original_file_path}: {str(e)}")
                    continue
                    
                # 更新进度条，但不显示文件名（避免重复）
                pbar.update(1)
                modified_files_count += 1

    return modified_files_count

def process_artist_folder(artist_path, artist_name, add_artist_name_enabled=True):
    """递归处理画师文件夹及其所有子文件夹"""
    total_modified_files_count = 0

    try:
        # 检查当前文件夹是否在排除列表中
        if any(keyword in artist_path for keyword in exclude_keywords):
            return 0

        for root, dirs, files in os.walk(artist_path, topdown=True):
            # 如果当前目录包含排除关键词，跳过整个目录
            if any(keyword in root for keyword in exclude_keywords):
                continue
            
            # 处理子文件夹名称
            for i, dir_name in enumerate(dirs):
                # 跳过排除的文件夹
                if any(keyword in dir_name for keyword in exclude_keywords):
                    continue
                    
                # 获取完整路径
                old_path = os.path.join(root, dir_name)
                
                # 如果不是一级目录，则应用格式化
                if root != artist_path:
                    new_name = format_folder_name(dir_name)
                    if new_name != dir_name:
                        new_path = os.path.join(root, new_name)
                        try:
                            # 保存原始时间戳
                            dir_stat = os.stat(old_path)
                            # 重命名文件夹
                            os.rename(old_path, new_path)
                            # 恢复时间戳
                            os.utime(new_path, (dir_stat.st_atime, dir_stat.st_mtime))
                            # 更新 dirs 列表中的名称，确保 os.walk 继续正常工作
                            dirs[i] = new_name
                            logging.info(f"重命名文件夹: {old_path} -> {new_path}")
                        except Exception as e:
                            logging.error(f"重命名文件夹出错 {old_path}: {str(e)}")
                
            # 处理当前目录下的所有压缩文件
            modified_files_count = process_files_in_directory(root, artist_name, add_artist_name_enabled)
            total_modified_files_count += modified_files_count
    except Exception as e:
        logging.error(f"处理文件夹出错: {e}")

    return total_modified_files_count

def process_folders(base_path, add_artist_name_enabled=True):
    """
    处理基础路径下的所有画师文件夹。
    不使用多线程，逐个处理每个画师的文件。
    """
    # 获取所有画师文件夹
    artist_folders = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder))
    ]

    total_processed = 0
    total_modified = 0
    total_files = 0

    # 逐个处理画师文件夹
    for folder in artist_folders:
        try:
            artist_path = os.path.join(base_path, folder)
            artist_name = get_artist_name(base_path, artist_path)
            
            # 处理画师文件夹中的文件，并获取修改文件数量
            modified_files_count = process_artist_folder(artist_path, artist_name, add_artist_name_enabled)
            total_processed += 1
            total_modified += modified_files_count
            
            # 统计该文件夹中的压缩文件总数
            for root, _, files in os.walk(artist_path):
                total_files += len([f for f in files if f.lower().endswith(ARCHIVE_EXTENSIONS)])
            
        except Exception as e:
            logging.error(f"处理文件夹 {folder} 出错: {e}")
            
    print(f"\n处理完成:")
    print(f"- 总共处理了 {total_processed} 个文件夹")
    print(f"- 扫描了 {total_files} 个压缩文件")
    if total_modified > 0:
        print(f"- 重命名了 {total_modified} 个文件")
    else:
        print(f"- ✨ 所有文件名都符合规范，没有文件需要重命名")

def get_artist_name(target_directory, archive_path):
    """
    从压缩文件路径中提取艺术家名称。
    获取基于相对路径的第一部分作为艺术家名称。
    """
    try:
        # 获取相对路径的第一部分作为艺术家名称
        rel_path = os.path.relpath(archive_path, target_directory)
        artist_name = rel_path.split(os.sep)[0]
        
        # 如果是方括号包围的名称，直接返回
        if artist_name.startswith('[') and artist_name.endswith(']'):
            return artist_name
            
        # 如果不是方括号包围的，加上方括号
        return f"[{artist_name}]"
    except Exception as e:
        logging.error(f"提取艺术家名称时出错: {e}")
        return ""

def record_folder_timestamps(target_directory):
    """记录target_directory下所有文件夹的时间戳。"""
    folder_timestamps = {}
    for root, dirs, files in os.walk(target_directory):
        for dir in dirs:
            try:
                folder_path = os.path.join(root, dir)
                folder_stat = os.stat(folder_path)
                folder_timestamps[folder_path] = (folder_stat.st_atime, folder_stat.st_mtime)
            except FileNotFoundError:
                logging.warning(f"找不到文件夹: {folder_path}")
                continue
            except Exception as e:
                logging.error(f"处理文件夹时出错 {folder_path}: {str(e)}")
                continue
    
    return folder_timestamps

def restore_folder_timestamps(folder_timestamps):
    """恢复之前记录的文件夹时间戳。"""
    for folder_path, (atime, mtime) in folder_timestamps.items():
        try:
            if os.path.exists(folder_path):
                os.utime(folder_path, (atime, mtime))
        except Exception as e:
            logging.error(f"恢复文件夹时间戳时出错 {folder_path}: {str(e)}")
            continue
