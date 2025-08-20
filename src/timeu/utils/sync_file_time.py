"""
文件夹时间同步工具
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger


def sync_folder_time(folder_path: str, target_time: datetime) -> bool:
    """
    将文件夹的创建时间和修改时间设置为指定时间
    
    Args:
        folder_path: 要修改时间的文件夹路径
        target_time: 目标时间
        
    Returns:
        bool: 是否成功
    """
    try:
        if not os.path.exists(folder_path):
            logger.error(f"文件夹不存在: {folder_path}")
            return False
            
        if not os.path.isdir(folder_path):
            logger.error(f"路径不是文件夹: {folder_path}")
            return False
        
        timestamp = target_time.timestamp()
        os.utime(folder_path, (timestamp, timestamp))
        
        logger.info(f"已更新文件夹时间: {folder_path} -> {target_time}")
        return True
        
    except Exception as e:
        logger.error(f"更新文件夹时间失败: {folder_path}, 错误: {e}")
        return False


def get_folder_times(folder_path: str) -> Optional[dict]:
    """
    获取文件夹的时间信息
    
    Args:
        folder_path: 文件夹路径
        
    Returns:
        dict: 包含创建时间和修改时间的字典，如果失败返回 None
    """
    try:
        if not os.path.exists(folder_path):
            logger.error(f"文件夹不存在: {folder_path}")
            return None
            
        stat = os.stat(folder_path)
        return {
            'ctime': datetime.fromtimestamp(stat.st_ctime),
            'mtime': datetime.fromtimestamp(stat.st_mtime),
            'atime': datetime.fromtimestamp(stat.st_atime)
        }
        
    except Exception as e:
        logger.error(f"获取文件夹时间失败: {folder_path}, 错误: {e}")
        return None


def sync_multiple_folders(folder_time_pairs: list) -> dict:
    """
    批量同步多个文件夹的时间
    
    Args:
        folder_time_pairs: [(folder_path, target_time), ...] 的列表
        
    Returns:
        dict: 结果字典，包含成功和失败的统计
    """
    results = {
        'success': [],
        'failed': [],
        'total': len(folder_time_pairs)
    }
    
    for folder_path, target_time in folder_time_pairs:
        if sync_folder_time(folder_path, target_time):
            results['success'].append(folder_path)
        else:
            results['failed'].append(folder_path)
    
    logger.info(f"批量同步完成: 成功 {len(results['success'])}, 失败 {len(results['failed'])}")
    return results


def archive_time_sync_workflow(base_path: str, update_folders: bool = True) -> dict:
    """
    压缩包时间同步工作流程
    
    1. 使用 timex 扫描文件夹中压缩包的图片时间
    2. 使用 timeu 更新文件夹时间
    
    Args:
        base_path: 要扫描的基础路径
        update_folders: 是否实际更新文件夹时间
        
    Returns:
        dict: 工作流程结果
    """
    from ..timex.__main__ import scan_folders_with_archives
    
    logger.info(f"开始压缩包时间同步工作流程: {base_path}")
    
    # 使用 timex 扫描
    scan_results = scan_folders_with_archives(base_path, update_folder_times=False)
    
    # 准备需要更新的文件夹列表
    folders_to_update = []
    for folder_path, folder_info in scan_results.items():
        if folder_info['should_update'] and folder_info['earliest_image_time']:
            folders_to_update.append((folder_path, folder_info['earliest_image_time']))
    
    workflow_results = {
        'scan_results': scan_results,
        'folders_to_update_count': len(folders_to_update),
        'sync_results': None
    }
    
    # 如果需要更新，执行同步
    if update_folders and folders_to_update:
        logger.info(f"准备更新 {len(folders_to_update)} 个文件夹的时间")
        sync_results = sync_multiple_folders(folders_to_update)
        workflow_results['sync_results'] = sync_results
    else:
        logger.info("仅进行扫描，不更新文件夹时间")
    
    return workflow_results
