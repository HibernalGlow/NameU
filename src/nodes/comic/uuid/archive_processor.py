import os
import time
import logging
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Set, List, Tuple

from nodes.comic.uuid.archive_handler import ArchiveHandler
from nodes.comic.uuid.json_handler import JsonHandler
from nodes.comic.uuid.path_handler import PathHandler
from nodes.comic.uuid.uuid_handler import UuidHandler

logger = logging.getLogger(__name__)

class ArchiveProcessor:
    """压缩文件处理类"""
    
    def __init__(self, target_directory: str, uuid_directory: str, 
                 max_workers: int = 5, order: str = 'mtime'):
        self.target_directory = target_directory
        self.uuid_directory = uuid_directory
        self.max_workers = max_workers
        self.order = order  # 保存排序方式
        self.total_archives = 0  # 总文件数
        self.processed_archives = 0  # 已处理文件数
    
    def process_archives(self) -> bool:
        """处理所有压缩文件（SSD优化版）"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            logger.info("[#current_stats]🔍 开始扫描压缩文件")
            
            # 直接快速扫描SSD
            archive_files = []
            for root, _, files in os.walk(self.target_directory):
                for file in files:
                    if file.endswith(('.zip', '.rar', '.7z')):
                        archive_files.append(os.path.join(root, file))
            
            self.total_archives = len(archive_files)
            self.processed_archives = 0
            logger.info(f"[#current_stats]共发现 {self.total_archives} 个压缩文件")
            
            # 使用内存缓存处理
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(self.process_single_archive, path, timestamp) 
                         for path in archive_files]
                
                for future in as_completed(futures):
                    future.result()
                    self.processed_archives += 1
                    progress = (self.processed_archives / self.total_archives) * 100
                    logger.info(f"[@current_progress]处理进度: ({self.processed_archives}/{self.total_archives}) {progress:.1f}%")
            
            return True
        finally:
            logger.info("[#current_stats]✨ 所有文件处理完成！")
    
    def process_single_archive(self, archive_path: str, timestamp: str) -> bool:
        """处理单个压缩文件
        
        Args:
            archive_path: 压缩包路径
            timestamp: 时间戳
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 获取文件信息
            artist_name = PathHandler.get_artist_name(self.target_directory, archive_path, 'multi')  # 默认为多人模式
            archive_name = os.path.basename(archive_path)
            relative_path = PathHandler.get_relative_path(self.target_directory, archive_path)
            
            # 检查压缩包中的JSON文件和YAML文件
            valid_json_files, yaml_files, all_json_files = self._find_valid_json_files(archive_path)
            
            # 检查是否存在重名但时间戳不同的JSON文件
            json_base_names = {}
            for name, _ in valid_json_files:
                base_name = os.path.splitext(name)[0]
                if base_name in json_base_names:
                    logger.info(f"[#process]发现重名JSON文件，将重新生成: {os.path.basename(archive_path)}")
                    return self._handle_multiple_json(archive_path, valid_json_files, yaml_files, all_json_files, archive_name, artist_name, relative_path, timestamp)
                json_base_names[base_name] = True
            
            # 如果存在YAML文件，需要删除并重新生成JSON
            if yaml_files:
                logger.info(f"[#process]发现YAML文件，将删除并生成新JSON: {os.path.basename(archive_path)}")
                return self._handle_multiple_json(archive_path, valid_json_files, yaml_files, all_json_files, archive_name, artist_name, relative_path, timestamp)
            
            # 根据JSON文件数量决定处理方式
            if len(valid_json_files) == 1 and len(all_json_files) == 1:
                return self._handle_single_json(archive_path, valid_json_files[0], archive_name, artist_name, relative_path, timestamp)
            else:
                return self._handle_multiple_json(archive_path, valid_json_files, yaml_files, all_json_files, archive_name, artist_name, relative_path, timestamp)
                
        except Exception as e:
            logger.error(f"[#process]处理压缩包时出错 {archive_path}: {str(e)}")
            return True
    
    def _find_valid_json_files(self, archive_path: str) -> tuple:
        """查找压缩包中的有效JSON文件和YAML文件
        
        Args:
            archive_path: 压缩包路径
            
        Returns:
            tuple: (有效JSON文件列表[(文件名, JSON内容)], YAML文件列表[文件名], 所有JSON文件列表[文件名])
        """
        import zipfile
        import subprocess
        import orjson
        
        valid_json_files = []
        yaml_files = []
        all_json_files = []  # 存储所有JSON文件，包括无效的
        
        try:
            # 尝试使用zipfile
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.json'):
                        all_json_files.append(name)
                        try:
                            with zf.open(name) as f:
                                json_content = orjson.loads(f.read())
                                if "uuid" in json_content and "timestamps" in json_content:
                                    valid_json_files.append((name, json_content))
                        except Exception:
                            continue
                    elif name.endswith('.yaml'):
                        yaml_files.append(name)
        except zipfile.BadZipFile:
            # 如果不是zip文件，使用7z
            try:
                temp_dir = os.path.join(os.path.dirname(archive_path), '.temp_extract')
                os.makedirs(temp_dir, exist_ok=True)
                try:
                    # 提取所有JSON和YAML文件
                    subprocess.run(
                        ['7z', 'e', archive_path, '*.json', '*.yaml', f"-o{temp_dir}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                    # 处理JSON文件
                    for file in os.listdir(temp_dir):
                        if file.endswith('.json'):
                            all_json_files.append(file)
                            try:
                                with open(os.path.join(temp_dir, file), 'rb') as f:
                                    json_content = orjson.loads(f.read())
                                    if "uuid" in json_content and "timestamps" in json_content:
                                        valid_json_files.append((file, json_content))
                            except Exception:
                                continue
                        elif file.endswith('.yaml'):
                            yaml_files.append(file)
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except subprocess.CalledProcessError:
                pass
                
        return valid_json_files, yaml_files, all_json_files
    
    def _handle_single_json(self, archive_path: str, json_file: tuple, archive_name: str, 
                          artist_name: str, relative_path: str, timestamp: str) -> bool:
        """处理单个JSON文件的情况
        
        Args:
            archive_path: 压缩包路径
            json_file: (文件名, JSON内容)元组
            archive_name: 压缩包名称
            artist_name: 艺术家名称
            relative_path: 相对路径
            timestamp: 时间戳
            
        Returns:
            bool: 处理是否成功
        """
        json_name, json_content = json_file
        
        # 检查是否需要更新
        if not JsonHandler.check_and_update_record(json_content, archive_name, artist_name, relative_path, timestamp):
            # logger.info(f"[#process]记录无需更新: {os.path.basename(archive_path)}")
            return True
            
        # 更新记录
        logger.info(f"[#process]检测到记录需要更新: {os.path.basename(archive_path)}")
        json_content = JsonHandler.update_record(json_content, archive_name, artist_name, relative_path, timestamp)
        
        # 创建临时文件并更新压缩包
        temp_dir = os.path.join(os.path.dirname(archive_path), '.temp_update')
        os.makedirs(temp_dir, exist_ok=True)
        try:
            temp_json = os.path.join(temp_dir, json_name)
            if JsonHandler.save(temp_json, json_content):
                if ArchiveHandler.add_json_to_archive(archive_path, temp_json, json_name):
                    logger.info(f"[#update]✅ 已更新压缩包中的JSON记录: {archive_name}")
                    return True
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _handle_multiple_json(self, archive_path: str, valid_json_files: List[tuple], yaml_files: List[str], 
                            all_json_files: List[str], archive_name: str, artist_name: str, 
                            relative_path: str, timestamp: str) -> bool:
        """处理多个JSON文件或需要生成新JSON的情况
        
        Args:
            archive_path: 压缩包路径
            valid_json_files: 有效的JSON文件列表
            yaml_files: YAML文件列表
            all_json_files: 所有JSON文件列表
            archive_name: 压缩包名称
            artist_name: 艺术家名称
            relative_path: 相对路径
            timestamp: 时间戳
            
        Returns:
            bool: 处理是否成功
        """
        # 删除所有JSON和YAML文件
        files_to_delete = all_json_files  # 删除所有JSON文件，包括无效的
        files_to_delete.extend(yaml_files)
        
        if files_to_delete:
            logger.info(f"[#process]删除现有文件: {os.path.basename(archive_path)}")
            # 强力删除：先尝试使用通配符删除
            try:
                ArchiveHandler.delete_files_from_archive(archive_path, ['*.json', '*.yaml'])
            except Exception:
                pass
            # 然后再逐个删除具体文件
            ArchiveHandler.delete_files_from_archive(archive_path, files_to_delete)
        
        # 创建新的UUID记录
        uuid_value = UuidHandler.generate_uuid(UuidHandler.load_existing_uuids())
        json_filename = f"{uuid_value}.json"
        
        # 获取按年月日分层的目录路径
        day_dir = PathHandler.get_uuid_path(self.uuid_directory, timestamp)
        json_path = os.path.join(day_dir, json_filename)
        
        # 准备新的记录数据
        new_record = {
            "archive_name": archive_name,
            "artist_name": artist_name,
            "relative_path": relative_path
        }
        
        # 创建新的JSON文件
        json_data = {
            "uuid": uuid_value,
            "timestamps": {
                timestamp: new_record
            }
        }
        
        # 保存并添加新JSON文件
        if JsonHandler.save(json_path, json_data):
            logger.info(f"[#process]创建新JSON: {json_filename}")
            if ArchiveHandler.add_json_to_archive(archive_path, json_path, json_filename):
                logger.info(f"[#update]✅ 已添加新JSON到压缩包: {archive_name}")
                return True
            else:
                logger.error(f"[#process]添加JSON到压缩包失败: {archive_name}")
        else:
            logger.error(f"[#process]JSON文件保存失败: {archive_name}")
            
        return False
