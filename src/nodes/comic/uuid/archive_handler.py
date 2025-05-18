import os
import subprocess
import shutil
import logging
import zipfile
from typing import Dict, Any, Optional, List, Tuple

# 导入本地模块
from nodes.comic.uuid.json_handler import JsonHandler
from nodes.comic.uuid.uuid_handler import UuidHandler

logger = logging.getLogger(__name__)

class ArchiveHandler:
    """压缩包处理类"""
    
    @staticmethod
    def check_archive_integrity(archive_path: str) -> bool:
        """检查压缩包完整性（已弃用）
        
        Args:
            archive_path: 压缩包路径
            
        Returns:
            bool: 始终返回True
        """
        return True    

    @staticmethod
    def delete_files_from_archive(archive_path: str, files_to_delete: List[str]) -> bool:
        """使用BandZip命令行删除文件"""
        if not files_to_delete:
            return True

        archive_name = os.path.basename(archive_path)
        logger.info(f"[#process]开始处理压缩包: {archive_name}")
        logger.info(f"[#process]需要删除的文件: {files_to_delete}")

        # 定义所有可能的临时文件路径
        backup_path = archive_path + ".bak"
        temp_path = archive_path + ".temp"
        success = False

        try:
            # 备份原文件
            shutil.copy2(archive_path, backup_path)
            logger.info(f"[#process][备份] 创建原文件备份: {backup_path}")

            # 使用BandZip删除文件
            deleted_count = 0
            for file in files_to_delete:
                try:
                    # 使用BandZip的bz命令删除文件
                    result = subprocess.run(
                        [
                            'bz', 'd',          # 删除命令
                            archive_path,        # 压缩包路径
                            file,               # 要删除的文件
                            '/q',               # 安静模式
                            '/y',               # 自动确认
                            '/utf8'             # 使用UTF-8编码
                        ],
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        errors='ignore'
                    )

                    # 检查是否成功
                    if result.returncode == 0:
                        deleted_count += 1
                        logger.info(f"[#process][删除成功] {file}")
                    else:
                        logger.warning(f"[#process]删除失败: {file}")
                        logger.debug(f"[#process]BandZip输出: {result.stdout}\n{result.stderr}")

                except Exception as e:
                    logger.error(f"[#process]删除文件失败 {file}: {e}")

            # 检查是否有文件被删除
            if deleted_count == 0:
                logger.warning("[#process]未成功删除任何文件")
                # 恢复备份
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, archive_path)
                    logger.info("[#process][恢复] 从备份恢复原文件")
                success = False
            else:
                logger.info(f"[#process][完成] 成功删除了 {deleted_count} 个文件")
                success = True

            return success

        except Exception as e:
            logger.error(f"[#process]处理过程中发生错误: {e}")
            # 恢复备份
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, archive_path)
                    logger.info("[#process][恢复] 从备份恢复原文件")
                except Exception as e:
                    logger.error(f"[#process]恢复备份失败: {e}")
            return False

        finally:
            # 清理所有临时文件和备份文件
            for path in [backup_path, temp_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.debug(f"[#process][清理] 删除临时文件: {os.path.basename(path)}")
                    except Exception as e:
                        logger.error(f"[#process]删除临时文件失败 {os.path.basename(path)}: {e}")
            
            # 清理同名的其他临时文件
            dir_path = os.path.dirname(archive_path)
            base_name = os.path.splitext(os.path.basename(archive_path))[0]
            for file in os.listdir(dir_path):
                if file.startswith(base_name) and (file.endswith('.bak') or file.endswith('.temp')):
                    try:
                        os.remove(os.path.join(dir_path, file))
                        logger.debug(f"[#process][清理] 删除相关临时文件: {file}")
                    except Exception as e:
                        logger.error(f"[#process]删除相关临时文件失败 {file}: {e}")
    
    @staticmethod
    def load_yaml_uuid_from_archive(archive_path: str) -> Optional[str]:
        """从压缩包中加载YAML文件的UUID"""
        # 首先检查压缩包完整性
        if not ArchiveHandler.check_archive_integrity(archive_path):
            return None
            
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.yaml'):
                        return os.path.splitext(name)[0]
        except zipfile.BadZipFile:
            # 如果不是zip文件，尝试使用7z
            return ArchiveHandler._load_uuid_from_7z(archive_path, '.yaml')
        except Exception as e:
            logger.error(f"[#process]读取压缩包失败: {archive_path}")
        return None
    
    @staticmethod
    def load_json_uuid_from_archive(archive_path: str) -> Optional[str]:
        """从压缩包中加载JSON文件的UUID"""
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('.json'):
                        return os.path.splitext(name)[0]
        except zipfile.BadZipFile:
            # 如果不是zip文件，尝试使用7z
            return ArchiveHandler._load_uuid_from_7z(archive_path, '.json')
        except Exception as e:
            logger.error(f"读取压缩包失败 {archive_path}: {e}")
        return None
    
    @staticmethod
    def _load_uuid_from_7z(archive_path: str, ext: str) -> Optional[str]:
        """使用7z命令行工具加载UUID"""
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                ['7z', 'l', archive_path],
                capture_output=True,
                text=True,
                encoding='gbk',
                errors='ignore',
                startupinfo=startupinfo,
                check=False
            )
            
            if result.returncode != 0:
                return None
            
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                if line.endswith(ext):
                    return os.path.splitext(line.split()[-1])[0]
                    
        except Exception as e:
            logger.error(f"使用7z读取压缩包失败 {archive_path}: {e}")
        return None
    
    @staticmethod
    def extract_yaml_from_archive(archive_path: str, yaml_uuid: str, temp_dir: str) -> Optional[str]:
        """从压缩包中提取YAML文件
        
        Args:
            archive_path: 压缩包路径
            yaml_uuid: YAML文件的UUID（不含扩展名）
            temp_dir: 临时目录路径
            
        Returns:
            Optional[str]: 提取的YAML文件路径，失败返回None
        """
        yaml_path = os.path.join(temp_dir, f"{yaml_uuid}.yaml")
        
        try:
            # 尝试使用zipfile
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extract(f"{yaml_uuid}.yaml", temp_dir)
                return yaml_path
        except Exception:
            # 如果zipfile失败，尝试使用7z
            try:
                subprocess.run(
                    ['7z', 'e', archive_path, f"{yaml_uuid}.yaml", f"-o{temp_dir}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                if os.path.exists(yaml_path):
                    return yaml_path
            except subprocess.CalledProcessError:
                logger.warning(f"[#process]提取YAML文件失败: {os.path.basename(archive_path)}")
        
        return None

    @staticmethod
    def add_json_to_archive(archive_path: str, json_path: str, json_name: str) -> bool:
        """添加JSON文件到压缩包
        
        Args:
            archive_path: 压缩包路径
            json_path: JSON文件路径
            json_name: 要保存在压缩包中的文件名
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 尝试使用zipfile
            with zipfile.ZipFile(archive_path, 'a') as zf:
                # 如果存在同名文件，先删除
                try:
                    zf.remove(json_name)
                except KeyError:
                    pass
                zf.write(json_path, json_name)
                logger.info(f"[#process]添加JSON文件: {json_name}")
                return True
        except Exception:
            # 如果zipfile失败，使用7z
            try:
                # 使用7z u命令更新文件
                subprocess.run(
                    ['7z', 'u', archive_path, json_path, f"-w{os.path.dirname(json_path)}"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True
                )
                logger.info(f"[#process]添加JSON文件: {json_name}")
                return True
            except subprocess.CalledProcessError:
                logger.error(f"[#process]添加JSON文件失败: {json_name}")
                return False

    @staticmethod
    def convert_yaml_archive_to_json(archive_path: str) -> Optional[Dict[str, Any]]:
        """转换压缩包中的YAML文件为JSON格式"""
        try:
            # 检查是否存在YAML文件
            yaml_uuid = ArchiveHandler.load_yaml_uuid_from_archive(archive_path)
            if not yaml_uuid:
                return None
            
            # 创建临时目录
            temp_dir = os.path.join(os.path.dirname(archive_path), '.temp_extract')
            os.makedirs(temp_dir, exist_ok=True)
            
            try:
                # 1. 提取YAML文件
                yaml_path = ArchiveHandler.extract_yaml_from_archive(archive_path, yaml_uuid, temp_dir)
                if not yaml_path or not os.path.exists(yaml_path):
                    logger.error(f"[#process]无法提取YAML文件: {os.path.basename(archive_path)}")
                    return None
                
                # 2. 读取并转换YAML数据
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    import yaml as yaml_module
                    yaml_data = yaml_module.safe_load(f)
                
                # 3. 检查是否存在同名JSON文件
                json_files = []
                try:
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        json_files = [f for f in zf.namelist() if f.endswith('.json')]
                except Exception:
                    # 如果zipfile失败，使用7z列出文件
                    try:
                        result = subprocess.run(
                            ['7z', 'l', archive_path],
                            capture_output=True,
                            text=True,
                            encoding='gbk',
                            errors='ignore',
                            check=True
                        )
                        if result.returncode == 0:
                            json_files = [line.split()[-1] for line in result.stdout.splitlines() 
                                        if line.strip() and line.endswith('.json')]
                    except subprocess.CalledProcessError:
                        pass
                
                # 如果存在JSON文件，删除它们并生成新的UUID
                if json_files:
                    logger.info(f"[#process]发现现有JSON文件，将删除并生成新UUID: {os.path.basename(archive_path)}")
                    ArchiveHandler.delete_files_from_archive(archive_path, json_files)
                    yaml_uuid = UuidHandler.generate_uuid(UuidHandler.load_existing_uuids())
                
                # 4. 转换为JSON格式
                json_data = JsonHandler.convert_yaml_to_json(yaml_data)
                json_data["uuid"] = yaml_uuid
                
                # 5. 保存JSON文件
                json_path = os.path.join(temp_dir, f"{yaml_uuid}.json")
                if not JsonHandler.save(json_path, json_data):
                    logger.error(f"[#process]保存JSON文件失败: {os.path.basename(archive_path)}")
                    return None
                
                # 6. 添加JSON到压缩包并删除YAML
                if ArchiveHandler.add_json_to_archive(archive_path, json_path, f"{yaml_uuid}.json"):
                    # 删除YAML文件
                    ArchiveHandler.delete_files_from_archive(archive_path, [f"{yaml_uuid}.yaml"])
                    logger.info(f"[#process]✅ YAML转换完成: {os.path.basename(archive_path)}")
                    return json_data
                
                logger.error(f"[#process]更新压缩包失败: {os.path.basename(archive_path)}")
                return None
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            logger.error(f"[#process]转换失败 {os.path.basename(archive_path)}: {str(e)}")
            return None
