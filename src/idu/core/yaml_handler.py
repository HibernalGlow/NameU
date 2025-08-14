import os
import yaml

from loguru import logger


class YamlHandler:
    """YAML文件处理类"""
    
    @staticmethod
    def read_yaml(yaml_path: str) -> list:
        """读取YAML文件内容，如果文件损坏则尝试修复"""
        if not os.path.exists(yaml_path):
            return []
            
        try:
            with open(yaml_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                if not isinstance(data, list):
                    data = [data] if data is not None else []
                return data
        except yaml.YAMLError:
            logger.error(f"YAML文件 {yaml_path} 已损坏，尝试修复...")
            return YamlHandler.repair_yaml_file(yaml_path)
        except Exception as e:
            logger.error(f"读取YAML文件时出错 {yaml_path}: {e}")
            return []
    
    @staticmethod
    def write_yaml(yaml_path: str, data: list) -> bool:
        """将数据写入YAML文件，确保写入完整性"""
        temp_path = yaml_path + '.tmp'
        try:
            with open(temp_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, allow_unicode=True)
            
            try:
                with open(temp_path, 'r', encoding='utf-8') as file:
                    yaml.safe_load(file)
            except yaml.YAMLError:
                logger.error(f"写入的YAML文件验证失败: {yaml_path}")
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                return False
                
            if os.path.exists(yaml_path):
                os.replace(temp_path, yaml_path)
            else:
                os.rename(temp_path, yaml_path)
            return True
                
        except Exception as e:
            logger.error(f"写入YAML文件时出错 {yaml_path}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
    
    @staticmethod
    def repair_yaml_file(yaml_path: str) -> list:
        """修复损坏的YAML文件"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            if not lines:
                return []

            valid_data = []
            current_record = []
            
            for line in lines:
                current_record.append(line)
                if line.strip() == '' or line == lines[-1]:
                    try:
                        record_str = ''.join(current_record)
                        parsed_data = yaml.safe_load(record_str)
                        if isinstance(parsed_data, list):
                            valid_data.extend(parsed_data)
                        elif parsed_data is not None:
                            valid_data.append(parsed_data)
                    except yaml.YAMLError:
                        pass
                    current_record = []

            if not valid_data:
                return []

            YamlHandler.write_yaml(yaml_path, valid_data)
            return valid_data

        except Exception as e:
            logger.error(f"修复YAML文件时出错 {yaml_path}: {e}")
            return []
    
    @staticmethod
    def repair_uuid_records(uuid_record_path: str) -> list:
        """修复损坏的UUID记录文件。"""
        backup_path = f"{uuid_record_path}.bak"
        
        # 如果存在备份文件，尝试从备份恢复
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'r', encoding='utf-8') as file:
                    records = yaml.safe_load(file) or []
                    if isinstance(records, list):
                        logger.info("[#process]从备份文件恢复记录成功")
                        return records
            except Exception:
                logger.error("[#process]从备份文件恢复记录失败")
                pass
        
        # 尝试修复原文件
        try:
            with open(uuid_record_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                # 尝试解析每个记录
                records = []
                current_record = {}
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        if current_record:
                            records.append(current_record)
                            current_record = {}
                        continue
                    
                    if line.startswith('- ') or line.startswith('UUID:'):
                        if current_record:
                            records.append(current_record)
                        current_record = {}
                    
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip('- ').strip()
                        value = value.strip()
                        if key and value:
                            current_record[key] = value
                
                if current_record:
                    records.append(current_record)
                
                # 验证记录
                valid_records = []
                for record in records:
                    if 'UUID' in record:
                        valid_records.append(record)
                
                logger.info(f"[#process]成功修复记录文件，恢复了 {len(valid_records)} 条记录")
                return valid_records
        except Exception as e:
            logger.error(f"[#process]修复UUID记录文件失败: {e}")
            return []
