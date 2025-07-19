import os
import orjson  # 使用orjson进行更快的JSON处理
from typing import Dict, Any
from loguru import logger

class JsonHandler:
    """JSON文件处理类"""
    
    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """快速加载JSON文件"""
        try:
            with open(file_path, 'rb') as f:
                return orjson.loads(f.read())
        except Exception as e:
            logger.error(f"加载JSON文件失败 {file_path}: {e}")
            return {}
    
    @staticmethod
    def save(file_path: str, data: Dict[str, Any]) -> bool:
        """快速保存JSON文件"""
        temp_path = f"{file_path}.tmp"
        try:
            # 使用orjson进行快速序列化
            json_bytes = orjson.dumps(
                data,
                option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY
            )
            
            with open(temp_path, 'wb') as f:
                f.write(json_bytes)
            
            if os.path.exists(file_path):
                os.replace(temp_path, file_path)
            else:
                os.rename(temp_path, file_path)
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件失败 {file_path}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    @staticmethod
    def convert_yaml_to_json(yaml_data: list) -> Dict[str, Any]:
        """将YAML数据转换为新的JSON格式"""
        json_data = {
            "timestamps": {}
        }
        
        for record in yaml_data:
            timestamp = record.get('Timestamp', '')
            if not timestamp:
                continue
                
            json_data["timestamps"][timestamp] = {
                "archive_name": record.get('ArchiveName', ''),
                "artist_name": record.get('ArtistName', ''),
                "relative_path": record.get('RelativePath', '')
            }
        
        return json_data

    @staticmethod
    def check_and_update_record(json_content: Dict[str, Any], archive_name: str, artist_name: str, relative_path: str, timestamp: str) -> bool:
        """检查并更新JSON记录
        
        Returns:
            bool: True表示需要更新，False表示无需更新
        """
        if "timestamps" not in json_content:
            return True
            
        latest_record = None
        if json_content["timestamps"]:
            latest_timestamp = max(json_content["timestamps"].keys())
            latest_record = json_content["timestamps"][latest_timestamp]
            
        if not latest_record:
            return True
            
        # 检查是否需要更新
        need_update = False
        if latest_record.get("archive_name") != archive_name:
            need_update = True
        if latest_record.get("artist_name") != artist_name:
            need_update = True
        if latest_record.get("relative_path") != relative_path:
            need_update = True
            
        return need_update

    @staticmethod
    def update_record(json_content: Dict[str, Any], archive_name: str, artist_name: str, relative_path: str, timestamp: str) -> Dict[str, Any]:
        """更新JSON记录"""
        json_content["timestamps"][timestamp] = {
            "archive_name": archive_name,
            "artist_name": artist_name,
            "relative_path": relative_path
        }
        return json_content
