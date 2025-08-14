import os
import json
import shutil
import yaml
from datetime import datetime

from idu.core.json_handler import JsonHandler

from loguru import logger


class UuidRecordManager:
    """UUID记录管理类"""
    
    def __init__(self, uuid_directory: str = r'E:\1BACKUP\ehv\uuid'):
        self.uuid_directory = uuid_directory
    
    def reorganize_uuid_files(self) -> None:
        """根据最后修改时间重新组织UUID文件的目录结构"""
        logger.info("[#current_stats]🔄 开始重新组织UUID文件...")
        
        json_record_path = os.path.join(self.uuid_directory, 'uuid_records.json')
        if not os.path.exists(json_record_path):
            logger.error("[#process]❌ UUID记录文件不存在")
            return
            
        try:
            with open(json_record_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                
            total_records = len(records)
            processed = 0
            
            for uuid, data in records.items():
                if not data.get("timestamps"):
                    continue
                    
                latest_timestamp = max(data["timestamps"].keys())
                
                try:
                    date = datetime.strptime(latest_timestamp, "%Y-%m-%d %H:%M:%S")
                    year = str(date.year)
                    month = f"{date.month:02d}"
                    day = f"{date.day:02d}"
                    
                    year_dir = os.path.join(self.uuid_directory, year)
                    month_dir = os.path.join(year_dir, month)
                    day_dir = os.path.join(month_dir, day)
                    target_path = os.path.join(day_dir, f"{uuid}.json")
                    
                    current_json_path = None
                    for root, _, files in os.walk(self.uuid_directory):
                        if f"{uuid}.json" in files:
                            current_json_path = os.path.join(root, f"{uuid}.json")
                            break
                    
                    if current_json_path and current_json_path != target_path:
                        os.makedirs(day_dir, exist_ok=True)
                        shutil.move(current_json_path, target_path)
                        logger.info(f"[#process]✅ 已移动: {uuid}.json")
                    
                    processed += 1
                    logger.info(f"[@current_progress]重组进度 {processed}/{total_records} ({(processed/total_records*100):.1f}%)")
                        
                except ValueError:
                    logger.error(f"[#process]❌ UUID {uuid} 的时间戳格式无效: {latest_timestamp}")
                    
        except Exception as e:
            logger.error(f"[#process]重组UUID文件失败: {e}")
        
        logger.info("[#current_stats]✨ UUID文件重组完成")
    
    def update_json_records(self) -> None:
        """更新JSON记录文件，确保所有记录都被保存"""
        logger.info("[#current_stats]🔄 开始更新JSON记录...")
        
        json_record_path = os.path.join(self.uuid_directory, 'uuid_records.json')
        
        # 加载现有记录，确保基础结构正确
        try:
            existing_records = JsonHandler.load(json_record_path)
            if not isinstance(existing_records, dict):
                existing_records = {"record": {}}
            if "record" not in existing_records:
                existing_records["record"] = {}
        except Exception as e:
            logger.error(f"[#process]加载记录文件失败，将创建新记录: {e}")
            existing_records = {"record": {}}
        
        total_files = 0
        processed = 0
        
        # 首先计算总文件数
        for root, _, files in os.walk(self.uuid_directory):
            total_files += sum(1 for file in files if file.endswith('.json') and file != 'uuid_records.json')
        
        # 遍历目录结构查找所有JSON文件
        for root, _, files in os.walk(self.uuid_directory):
            for file in files:
                if file.endswith('.json') and file != 'uuid_records.json':
                    uuid = os.path.splitext(file)[0]
                    json_path = os.path.join(root, file)
                    try:
                        file_data = JsonHandler.load(json_path)
                        if not file_data:
                            logger.warning(f"[#process]跳过空文件: {file}")
                            continue
                            
                        # 无论是否需要更新，都确保记录存在于缓存中
                        if uuid not in existing_records["record"]:
                            # 新记录，直接添加
                            existing_records["record"][uuid] = file_data
                            logger.info(f"[#process]✅ 添加新记录: {uuid}")
                        else:
                            # 已存在的记录，合并时间戳
                            if "timestamps" not in existing_records["record"][uuid]:
                                existing_records["record"][uuid]["timestamps"] = {}
                            
                            if "timestamps" in file_data:
                                # 检查是否有新的时间戳需要更新
                                has_new_timestamps = False
                                for timestamp, data in file_data["timestamps"].items():
                                    if timestamp not in existing_records["record"][uuid]["timestamps"]:
                                        has_new_timestamps = True
                                        existing_records["record"][uuid]["timestamps"][timestamp] = data
                                
                                if has_new_timestamps:
                                    logger.info(f"[#process]✅ 更新记录: {uuid}")
                                else:
                                    logger.info(f"[#process]✓ 记录已存在且无需更新: {uuid}")
                            else:
                                logger.info(f"[#process]✓ 记录已存在且无需更新: {uuid}")
                            
                    except Exception as e:
                        logger.error(f"[#process]处理JSON文件失败 {json_path}: {e}")
                    
                    processed += 1
                    logger.info(f"[@current_progress]更新进度 {processed}/{total_files} ({(processed/total_files*100):.1f}%)")
        
        # 使用临时文件保证写入安全性
        temp_path = f"{json_record_path}.tmp"
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(existing_records, f, ensure_ascii=False, indent=2)
            
            # 原子性替换
            if os.path.exists(json_record_path):
                os.replace(temp_path, json_record_path)
            else:
                os.rename(temp_path, json_record_path)
            logger.info("[#current_stats]✅ JSON记录更新完成")
            
        except Exception as e:
            logger.error(f"[#process]❌ JSON记录更新失败: {e}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
    
    def convert_yaml_to_json_structure(self) -> None:
        """将现有的YAML文件结构转换为JSON结构"""
        logger.info("[#current_stats]🔄 开始转换YAML到JSON结构...")
        
        yaml_record_path = os.path.join(self.uuid_directory, 'uuid_records.yaml')
        json_record_path = os.path.join(self.uuid_directory, 'uuid_records.json')
        
        # 转换主记录文件
        if os.path.exists(yaml_record_path):
            try:
                with open(yaml_record_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                    
                total_records = len(yaml_data)
                processed = 0
                
                json_records = {"record": {}}
                for record in yaml_data:
                    uuid = record.get('UUID')
                    if not uuid:
                        continue
                        
                    if uuid not in json_records["record"]:
                        json_records["record"][uuid] = {"uuid": uuid, "timestamps": {}}
                        
                    timestamp = record.get('LastModified') or record.get('CreatedAt')
                    if timestamp:
                        json_records["record"][uuid]["timestamps"][timestamp] = {
                            "archive_name": record.get('ArchiveName', ''),
                            "artist_name": record.get('ArtistName', ''),
                            "relative_path": record.get('LastPath', '')
                        }
                    
                    processed += 1
                    logger.info(f"[@current_progress]转换进度 {processed}/{total_records} ({(processed/total_records*100):.1f}%)")
                
                JsonHandler.save(json_record_path, json_records)
                logger.info("[#current_stats]✅ 主记录文件转换完成")
                
            except Exception as e:
                logger.error(f"[#process]转换主记录文件失败: {e}")
        
        # 转换目录中的YAML文件
        yaml_files = []
        for root, _, files in os.walk(self.uuid_directory):
            yaml_files.extend([os.path.join(root, f) for f in files if f.endswith('.yaml') and f != 'uuid_records.yaml'])
        
        total_files = len(yaml_files)
        processed = 0
        
        for yaml_path in yaml_files:
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                    
                json_path = os.path.join(os.path.dirname(yaml_path), f"{os.path.splitext(os.path.basename(yaml_path))[0]}.json")
                
                # 转换单个YAML记录
                from idu.core.json_handler import JsonHandler
                json_data = JsonHandler.convert_yaml_to_json(yaml_data)
                json_data["uuid"] = os.path.splitext(os.path.basename(yaml_path))[0]
                
                if JsonHandler.save(json_path, json_data):
                    os.remove(yaml_path)
                    logger.info(f"[#process]✅ 转换完成: {os.path.basename(yaml_path)}")
                
                processed += 1
                logger.info(f"[@current_progress]文件转换进度 {processed}/{total_files} ({(processed/total_files*100):.1f}%)")
                
            except Exception as e:
                logger.error(f"[#process]转换文件失败 {os.path.basename(yaml_path)}: {e}")
        
        logger.info("[#current_stats]✨ YAML到JSON转换完成")
