"""
文件处理模块，提供文件和文件夹处理功能
"""

import os
from loguru import logger
from tqdm import tqdm
from .constants import ARCHIVE_EXTENSIONS, exclude_keywords, forbidden_artist_keywords
from .filename_processor import (
    detect_and_decode_filename, get_unique_filename, get_unique_filename_with_samename,
    format_folder_name, has_artist_name, convert_sensitive_words_to_pinyin,
    check_sensitive_word, get_sensitive_words_in_filename, get_unique_filename_with_pinyin_conversion
)

def process_files_in_directory(directory, artist_name, add_artist_name_enabled=True, convert_sensitive_enabled=True, filter_manager=None):
    """
    处理目录下的所有文件（支持所有类型，不仅限压缩包）
    Args:
        directory: 目录路径
        artist_name: 画师名称
        add_artist_name_enabled: 是否添加画师名
        convert_sensitive_enabled: 是否将敏感词转换为拼音
        filter_manager: 过滤管理器（可选）
    Returns:
        int: 修改的文件数量
    """
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    modified_files_count = 0
    is_excluded = any(keyword in directory for keyword in exclude_keywords)
    has_forbidden = any(keyword in directory for keyword in forbidden_artist_keywords)
    files_to_modify = []
    for filename in files:
        original_file_path = os.path.join(directory, filename)
        # 过滤器支持
        if filter_manager and filter_manager.should_filter_file(original_file_path):
            continue
        filename = detect_and_decode_filename(filename)
        new_filename = filename
        new_filename = get_unique_filename(directory, new_filename, artist_name, is_excluded)
        if convert_sensitive_enabled and check_sensitive_word(new_filename):
            logger.info(f"文件名含有敏感词，开始转换为拼音: {new_filename}")
            sensitive_words = get_sensitive_words_in_filename(new_filename)
            logger.info(f"检测到的敏感词: {', '.join(sensitive_words)}")
            new_filename = convert_sensitive_words_to_pinyin(new_filename)
            logger.info(f"转换后的文件名: {new_filename}")
        if not is_excluded and not has_forbidden and add_artist_name_enabled and artist_name not in exclude_keywords and not has_artist_name(new_filename, artist_name):
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}{artist_name}{ext}"
        final_filename = get_unique_filename_with_samename(directory, new_filename, original_file_path)
        if final_filename != filename:
            files_to_modify.append((filename, final_filename, original_file_path))
    for old_name, new_name, old_path in files_to_modify:
        new_path = os.path.join(directory, new_name)
        try:
            os.rename(old_path, new_path)
            logger.info(f"重命名文件: {old_path} -> {new_path}")
            modified_files_count += 1
        except Exception as e:
            logger.error(f"重命名文件出错 {old_path}: {str(e)}")
    return modified_files_count

def process_artist_folder(artist_path, artist_name, add_artist_name_enabled=True, convert_sensitive_enabled=True, filter_manager=None):
    """递归处理画师文件夹及其所有子文件夹
    Args:
        artist_path: 画师文件夹路径
        artist_name: 画师名称
        add_artist_name_enabled: 是否添加画师名
        convert_sensitive_enabled: 是否将敏感词转换为拼音
        filter_manager: 过滤管理器
    """
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
                old_path = os.path.join(root, dir_name)
                # 过滤文件夹
                if filter_manager and filter_manager.should_filter_file(old_path):
                    continue
                # 跳过排除的文件夹
                if any(keyword in dir_name for keyword in exclude_keywords):
                    continue
                # 如果不是一级目录，则应用格式化
                if root != artist_path:
                    new_name = format_folder_name(dir_name)
                    # 检测目录名是否包含敏感词并转换
                    if convert_sensitive_enabled and check_sensitive_word(new_name):
                        logger.info(f"目录名含有敏感词，开始转换为拼音: {new_name}")
                        sensitive_words = get_sensitive_words_in_filename(new_name)
                        logger.info(f"检测到的敏感词: {', '.join(sensitive_words)}")
                        new_name = convert_sensitive_words_to_pinyin(new_name)
                        logger.info(f"转换后的目录名: {new_name}")
                    if new_name != dir_name:
                        new_path = os.path.join(root, new_name)
                        try:
                            dir_stat = os.stat(old_path)
                            os.rename(old_path, new_path)
                            os.utime(new_path, (dir_stat.st_atime, dir_stat.st_mtime))
                            dirs[i] = new_name
                            logger.info(f"重命名文件夹: {old_path} -> {new_path}")
                        except Exception as e:
                            logger.error(f"重命名文件夹出错 {old_path}: {str(e)}")
            # 处理当前目录下的所有压缩文件
            for filename in files:
                file_path = os.path.join(root, filename)
                if filter_manager and filter_manager.should_filter_file(file_path):
                    continue
            modified_files_count = process_files_in_directory(root, artist_name, add_artist_name_enabled, convert_sensitive_enabled, filter_manager=filter_manager)
            total_modified_files_count += modified_files_count
    except Exception as e:
        logger.error(f"处理文件夹出错: {e}")
    return total_modified_files_count

def process_folders(base_path, add_artist_name_enabled=True, convert_sensitive_enabled=True, filter_manager=None):
    """
    处理基础路径下的所有画师文件夹。
    不使用多线程，逐个处理每个画师的文件。
    Args:
        base_path: 基础路径
        add_artist_name_enabled: 是否添加画师名
        convert_sensitive_enabled: 是否将敏感词转换为拼音
        filter_manager: 过滤管理器
    """
    artist_folders = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder))
    ]
    total_processed = 0
    total_modified = 0
    total_files = 0
    total_sensitive = 0
    for folder in artist_folders:
        artist_path = os.path.join(base_path, folder)
        # 过滤画师文件夹
        if filter_manager and filter_manager.should_filter_file(artist_path):
            continue
        try:
            artist_name = get_artist_name(base_path, artist_path)
            modified_files_count = process_artist_folder(artist_path, artist_name, add_artist_name_enabled, convert_sensitive_enabled, filter_manager=filter_manager)
            total_processed += 1
            total_modified += modified_files_count
            for root, _, files in os.walk(artist_path):
                total_files += len([f for f in files if f.lower().endswith(ARCHIVE_EXTENSIONS)])
        except Exception as e:
            logger.error(f"处理文件夹 {folder} 出错: {e}")
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
        logger.error(f"提取艺术家名称时出错: {e}")
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
                logger.warning(f"找不到文件夹: {folder_path}")
                continue
            except Exception as e:
                logger.error(f"处理文件夹时出错 {folder_path}: {str(e)}")
                continue
    
    return folder_timestamps

def restore_folder_timestamps(folder_timestamps):
    """恢复之前记录的文件夹时间戳。"""
    for folder_path, (atime, mtime) in folder_timestamps.items():
        try:
            if os.path.exists(folder_path):
                os.utime(folder_path, (atime, mtime))
        except Exception as e:
            logger.error(f"恢复文件夹时间戳时出错 {folder_path}: {str(e)}")
            continue
