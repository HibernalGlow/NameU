"""
压缩包ID处理模块
处理压缩包注释中的ID，包括读取、写入和生成
"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional
from loguru import logger
from nanoid import generate


class ArchiveIDHandler:
    """压缩包ID处理类"""
    
    @staticmethod
    def generate_id() -> str:
        """
        生成新的压缩包ID
        
        Returns:
            str: 新生成的唯一ID
        """
        # 使用nanoid生成URL安全的唯一ID
        return generate(size=12)
    
    @staticmethod
    def get_archive_comment(archive_path: str) -> Optional[str]:
        """
        获取压缩包注释
        
        Args:
            archive_path: 压缩包路径
            
        Returns:
            Optional[str]: 压缩包注释，失败返回None
        """
        try:
            # 方法1: 使用bz.exe读取（如果是ZIP文件）
            if archive_path.lower().endswith('.zip'):
                try:
                    result = subprocess.run(
                        [r"bz.exe", 'l', '-list:v', archive_path],
                        capture_output=True,
                        text=True,
                        encoding='utf-8'
                    )
                    
                    if result.returncode == 0:
                        # 解析bz.exe的输出查找注释
                        output = result.stdout
                        comment_start_marker = 'Archive comment:'
                        
                        # 找到注释开始位置
                        comment_index = output.find(comment_start_marker)
                        if comment_index != -1:
                            # 获取注释内容，需要处理多行注释
                            lines = output[comment_index:].splitlines()
                            if len(lines) > 1:  # 确保有注释内容行
                                # 跳过第一行（包含"Archive comment:"的行）
                                comment_lines = []
                                for line in lines[1:]:
                                    # 如果遇到新的段落标记，停止读取注释
                                    if line.strip() and (line.startswith('Archive:') or line.startswith('Type:') or 
                                                        line.startswith('Physical Size:') or line.startswith('Headers Size:')):
                                        break
                                    comment_lines.append(line)
                                
                                comment_part = '\n'.join(comment_lines).strip()
                                if comment_part:
                                    # 修复JSON格式：如果开头缺少大括号，补上
                                    if comment_part.startswith('"id":') or comment_part.startswith('"'):
                                        comment_part = '{' + comment_part
                                    logger.debug(f"使用bz.exe读取注释成功: {archive_path}")
                                    return comment_part
                        return None
                except Exception as e:
                    logger.debug(f"使用bz.exe读取注释失败: {e}")
            
            # 方法2: 回退到7z（用于其他格式的压缩包）
            result = subprocess.run(
                ['7z', 'l', '-slt', archive_path],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                return None
            
            # 解析输出查找注释
            for line in result.stdout.splitlines():
                if line.startswith('Comment = '):
                    comment = line[10:].strip()  # 去掉"Comment = "前缀
                    if comment:
                        logger.debug(f"使用7z读取注释成功: {archive_path}")
                        return comment
            
            return None
            
        except Exception as e:
            logger.error(f"获取压缩包注释失败 {archive_path}: {e}")
            return None
    
    @staticmethod
    def set_archive_comment(archive_path: str, comment: str) -> bool:
        """
        设置压缩包注释
        
        Args:
            archive_path: 压缩包路径
            comment: 要设置的注释
            
        Returns:
            bool: 是否设置成功
        """
        try:
            # 检查文件是否为ZIP格式（bandizip主要支持ZIP注释）
            if not archive_path.lower().endswith('.zip'):
                logger.warning(f"跳过非ZIP文件的注释设置: {archive_path}")
                return False
            
            # 使用临时文件方式，强制UTF-8编码
            bandizip_commands = [r"bz.exe"]
            
            for cmd in bandizip_commands:
                try:
                    # 创建UTF-8编码的临时注释文件
                    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as f:
                        f.write(comment)
                        comment_file = f.name
                    
                    try:
                        result = subprocess.run(
                            [cmd, 'a', '-y', f'-cmtfile:{comment_file}', archive_path],
                            capture_output=True,
                            text=True,
                            encoding='utf-8'
                        )
                        
                        if result.returncode == 0:
                            logger.debug(f"使用{cmd}文件方式设置压缩包注释成功: {archive_path}")
                            return True
                        else:
                            logger.debug(f"{cmd}文件方式设置注释失败: {result.stderr}")
                            
                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(comment_file)
                        except:
                            pass
                            
                except FileNotFoundError:
                    logger.debug(f"{cmd}未找到，跳过")
                    continue
                    
            logger.warning(f"未找到可用的Bandizip命令，无法设置注释: {archive_path}")
            return False
                    
        except Exception as e:
            logger.error(f"设置压缩包注释失败 {archive_path}: {e}")
            return False
    
    @staticmethod
    def extract_id_from_comment(comment: Optional[str]) -> Optional[str]:
        """
        从注释中提取ID
        
        Args:
            comment: 压缩包注释
            
        Returns:
            Optional[str]: 提取的ID，未找到返回None
        """
        if not comment:
            return None
        
        # 支持多种ID格式
        # 格式1: ID: xxxxx
        # 格式2: archive_id: xxxxx
        # 格式3: {"id": "xxxxx", ...}
        
        import re
        import json
        
        # 尝试JSON格式
        try:
            data = json.loads(comment)
            if isinstance(data, dict):
                return data.get('id') or data.get('archive_id')
        except:
            pass
        
        # 尝试简单的键值对格式
        patterns = [
            r'(?:^|\n)ID:\s*([^\n\r]+)',
            r'(?:^|\n)archive_id:\s*([^\n\r]+)',
            r'(?:^|\n)id:\s*([^\n\r]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, comment, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    @staticmethod
    def create_comment_with_id(archive_id: str, metadata: Optional[dict] = None) -> str:
        """
        创建包含ID的注释
        
        Args:
            archive_id: 压缩包ID
            metadata: 额外的元数据
            
        Returns:
            str: 格式化的注释内容
        """
        import json
        from datetime import datetime
        
        comment_data = {
            'id': archive_id,
            'created_by': 'nameu',
            'created_at': datetime.now().isoformat()
        }
        
        if metadata:
            comment_data.update(metadata)
        
        return json.dumps(comment_data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def get_or_create_archive_id(archive_path: str, metadata: Optional[dict] = None) -> Optional[str]:
        """
        获取或创建压缩包ID
        
        Args:
            archive_path: 压缩包路径
            metadata: 额外的元数据
            
        Returns:
            Optional[str]: 压缩包ID，失败返回None
        """
        # 首先尝试从注释获取现有ID
        comment = ArchiveIDHandler.get_archive_comment(archive_path)
        existing_id = ArchiveIDHandler.extract_id_from_comment(comment)
        
        if existing_id:
            logger.debug(f"找到现有ID: {existing_id} ({os.path.basename(archive_path)})")
            return existing_id
        
        # 生成新ID
        new_id = ArchiveIDHandler.generate_id()
        new_comment = ArchiveIDHandler.create_comment_with_id(new_id, metadata)
        
        # 设置注释
        if ArchiveIDHandler.set_archive_comment(archive_path, new_comment):
            logger.info(f"创建新ID: {new_id} ({os.path.basename(archive_path)})")
            return new_id
        else:
            logger.error(f"无法设置压缩包注释: {archive_path}")
            return None
    
    @staticmethod
    def update_comment_metadata(archive_path: str, metadata: dict) -> bool:
        """
        更新注释中的元数据（保持ID不变）
        
        Args:
            archive_path: 压缩包路径
            metadata: 要更新的元数据
            
        Returns:
            bool: 是否更新成功
        """
        try:
            import json
            from datetime import datetime
            
            # 获取现有注释
            comment = ArchiveIDHandler.get_archive_comment(archive_path)
            archive_id = ArchiveIDHandler.extract_id_from_comment(comment)
            
            if not archive_id:
                logger.warning(f"无法获取压缩包ID，无法更新元数据: {archive_path}")
                return False
            
            # 解析现有数据
            try:
                existing_data = json.loads(comment) if comment else {}
            except:
                existing_data = {}
            
            # 更新数据
            existing_data.update(metadata)
            existing_data['id'] = archive_id  # 确保ID不变
            existing_data['updated_at'] = datetime.now().isoformat()
            
            # 设置新注释
            new_comment = json.dumps(existing_data, ensure_ascii=False, indent=2)
            return ArchiveIDHandler.set_archive_comment(archive_path, new_comment)
            
        except Exception as e:
            logger.error(f"更新注释元数据失败 {archive_path}: {e}")
            return False
