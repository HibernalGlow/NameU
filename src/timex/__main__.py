import os
import sys
import zipfile
import rarfile
import tarfile
import py7zr
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from loguru import logger
from tqdm import tqdm
from PIL import Image
from PIL.ExifTags import TAGS
import tempfile
import shutil

def setup_logger(app_name="timex", project_root=None, console_output=True):
    """配置 Loguru 日志系统"""
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    logger.remove()
    
    if console_output:
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
        )
    
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
    )
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger

logger = setup_logger()

class ArchiveTimeExtractor:
    """压缩包时间戳提取器"""
    
    # 支持的图片格式
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp'}
    
    # 支持的压缩包格式
    ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.tar.gz', '.tar.bz2', '.tar.xz'}
    
    def __init__(self):
        self.temp_dirs = []
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        
    def cleanup(self):
        """清理临时文件"""
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {temp_dir}, 错误: {e}")
        self.temp_dirs.clear()
    
    def get_image_creation_time(self, image_path: str) -> Optional[datetime]:
        """从图片文件获取创建时间"""
        try:
            # 先尝试从 EXIF 获取
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if exif_data:
                    for tag, value in exif_data.items():
                        if TAGS.get(tag) == 'DateTime':
                            try:
                                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                            except ValueError:
                                pass
                        elif TAGS.get(tag) == 'DateTimeOriginal':
                            try:
                                return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                            except ValueError:
                                pass
            
            # 如果 EXIF 中没有，使用文件的创建时间
            stat = os.stat(image_path)
            # Windows 下使用 st_ctime，其他系统使用 st_mtime
            if os.name == 'nt':
                return datetime.fromtimestamp(stat.st_ctime)
            else:
                return datetime.fromtimestamp(min(stat.st_mtime, stat.st_ctime))
                
        except Exception as e:
            logger.debug(f"获取图片时间失败: {image_path}, 错误: {e}")
            return None
    
    def extract_archive(self, archive_path: str, extract_to: str) -> bool:
        """提取压缩包到指定目录"""
        try:
            ext = Path(archive_path).suffix.lower()
            
            if ext == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_to)
            elif ext == '.rar':
                with rarfile.RarFile(archive_path) as rf:
                    rf.extractall(extract_to)
            elif ext == '.7z':
                with py7zr.SevenZipFile(archive_path, mode='r') as szf:
                    szf.extractall(extract_to)
            elif ext in ['.tar', '.tar.gz', '.tar.bz2', '.tar.xz']:
                mode = 'r'
                if ext == '.tar.gz':
                    mode = 'r:gz'
                elif ext == '.tar.bz2':
                    mode = 'r:bz2'
                elif ext == '.tar.xz':
                    mode = 'r:xz'
                
                with tarfile.open(archive_path, mode) as tf:
                    tf.extractall(extract_to)
            else:
                logger.warning(f"不支持的压缩包格式: {ext}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"提取压缩包失败: {archive_path}, 错误: {e}")
            return False
    
    def find_images_in_directory(self, directory: str) -> List[str]:
        """在目录中查找所有图片文件"""
        images = []
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if Path(file).suffix.lower() in self.IMAGE_EXTENSIONS:
                        images.append(os.path.join(root, file))
        except Exception as e:
            logger.error(f"搜索图片文件失败: {directory}, 错误: {e}")
        
        return images
    
    def get_earliest_image_time_from_archive(self, archive_path: str) -> Optional[datetime]:
        """从压缩包中获取最早的图片创建时间"""
        if not os.path.exists(archive_path):
            logger.error(f"压缩包不存在: {archive_path}")
            return None
            
        ext = Path(archive_path).suffix.lower()
        if ext not in self.ARCHIVE_EXTENSIONS:
            logger.debug(f"不是支持的压缩包格式: {archive_path}")
            return None
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='timex_')
        self.temp_dirs.append(temp_dir)
        
        logger.info(f"正在提取压缩包: {archive_path}")
        if not self.extract_archive(archive_path, temp_dir):
            return None
        
        # 查找图片文件
        images = self.find_images_in_directory(temp_dir)
        if not images:
            logger.info(f"压缩包中未找到图片文件: {archive_path}")
            return None
        
        logger.info(f"在压缩包中找到 {len(images)} 个图片文件")
        
        # 获取所有图片的创建时间
        earliest_time = None
        valid_times = []
        
        for image_path in tqdm(images, desc="分析图片时间"):
            image_time = self.get_image_creation_time(image_path)
            if image_time:
                valid_times.append(image_time)
                if earliest_time is None or image_time < earliest_time:
                    earliest_time = image_time
        
        if valid_times:
            logger.info(f"找到 {len(valid_times)} 个有效时间戳，最早时间: {earliest_time}")
            return earliest_time
        else:
            logger.warning(f"未能从压缩包中的图片获取有效时间戳: {archive_path}")
            return None
    
    def scan_folder_archives(self, folder_path: str) -> Dict[str, Dict[str, Any]]:
        """扫描文件夹中的所有压缩包，返回时间信息"""
        if not os.path.exists(folder_path):
            logger.error(f"文件夹不存在: {folder_path}")
            return {}
        
        results = {}
        archives_found = []
        
        # 查找所有压缩包
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                ext = Path(item).suffix.lower()
                if ext in self.ARCHIVE_EXTENSIONS:
                    archives_found.append(item_path)
        
        if not archives_found:
            logger.info(f"在文件夹中未找到压缩包: {folder_path}")
            return {}
        
        logger.info(f"找到 {len(archives_found)} 个压缩包")
        
        # 处理每个压缩包
        for archive_path in tqdm(archives_found, desc="扫描压缩包"):
            archive_name = os.path.basename(archive_path)
            logger.info(f"正在处理: {archive_name}")
            
            earliest_time = self.get_earliest_image_time_from_archive(archive_path)
            
            results[archive_path] = {
                'archive_name': archive_name,
                'earliest_image_time': earliest_time,
                'archive_size': os.path.getsize(archive_path)
            }
        
        return results

def scan_folders_with_archives(base_path: str, update_folder_times: bool = False) -> Dict[str, Dict[str, Any]]:
    """扫描指定路径下一级文件夹中的压缩包，分析其中的图片时间"""
    if not os.path.exists(base_path):
        logger.error(f"基础路径不存在: {base_path}")
        return {}
    
    results = {}
    
    # 获取一级子文件夹
    subfolders = []
    for item in os.listdir(base_path):
        item_path = os.path.join(base_path, item)
        if os.path.isdir(item_path):
            subfolders.append(item_path)
    
    if not subfolders:
        logger.info(f"在基础路径下未找到子文件夹: {base_path}")
        return {}
    
    logger.info(f"找到 {len(subfolders)} 个子文件夹")
    
    with ArchiveTimeExtractor() as extractor:
        for folder_path in tqdm(subfolders, desc="扫描文件夹"):
            folder_name = os.path.basename(folder_path)
            logger.info(f"正在扫描文件夹: {folder_name}")
            
            # 获取文件夹当前的时间戳
            folder_stat = os.stat(folder_path)
            folder_ctime = datetime.fromtimestamp(folder_stat.st_ctime)
            folder_mtime = datetime.fromtimestamp(folder_stat.st_mtime)
            
            # 扫描文件夹中的压缩包
            archive_results = extractor.scan_folder_archives(folder_path)
            
            # 找到最早的图片时间
            earliest_image_time = None
            for archive_path, archive_info in archive_results.items():
                if archive_info['earliest_image_time']:
                    if earliest_image_time is None or archive_info['earliest_image_time'] < earliest_image_time:
                        earliest_image_time = archive_info['earliest_image_time']
            
            # 决定是否需要更新文件夹时间
            should_update = False
            if earliest_image_time:
                # 如果图片时间早于文件夹的创建时间或修改时间，则需要更新
                if (earliest_image_time < folder_ctime or earliest_image_time < folder_mtime):
                    should_update = True
            
            folder_info = {
                'folder_name': folder_name,
                'folder_path': folder_path,
                'current_ctime': folder_ctime,
                'current_mtime': folder_mtime,
                'earliest_image_time': earliest_image_time,
                'archives_count': len(archive_results),
                'archives': archive_results,
                'should_update': should_update
            }
            
            # 如果需要且允许更新文件夹时间
            if should_update and update_folder_times:
                try:
                    timestamp = earliest_image_time.timestamp()
                    os.utime(folder_path, (timestamp, timestamp))
                    logger.info(f"已更新文件夹时间: {folder_name} -> {earliest_image_time}")
                    folder_info['time_updated'] = True
                except Exception as e:
                    logger.error(f"更新文件夹时间失败: {folder_name}, 错误: {e}")
                    folder_info['time_updated'] = False
            else:
                folder_info['time_updated'] = False
            
            results[folder_path] = folder_info
    
    return results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="扫描文件夹中压缩包的图片时间戳")
    parser.add_argument("path", help="要扫描的基础路径")
    parser.add_argument("--update", action="store_true", help="是否更新文件夹的时间戳")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG")
    
    logger.info(f"开始扫描路径: {args.path}")
    logger.info(f"更新文件夹时间: {'是' if args.update else '否'}")
    
    results = scan_folders_with_archives(args.path, args.update)
    
    # 输出结果摘要
    total_folders = len(results)
    folders_with_archives = sum(1 for r in results.values() if r['archives_count'] > 0)
    folders_to_update = sum(1 for r in results.values() if r['should_update'])
    folders_updated = sum(1 for r in results.values() if r.get('time_updated', False))
    
    print(f"\n=== 扫描结果摘要 ===")
    print(f"总文件夹数: {total_folders}")
    print(f"包含压缩包的文件夹: {folders_with_archives}")
    print(f"需要更新时间的文件夹: {folders_to_update}")
    if args.update:
        print(f"成功更新时间的文件夹: {folders_updated}")
    
    # 显示详细结果
    print(f"\n=== 详细结果 ===")
    for folder_path, info in results.items():
        print(f"\n文件夹: {info['folder_name']}")
        print(f"  路径: {folder_path}")
        print(f"  当前创建时间: {info['current_ctime']}")
        print(f"  当前修改时间: {info['current_mtime']}")
        print(f"  压缩包数量: {info['archives_count']}")
        
        if info['earliest_image_time']:
            print(f"  最早图片时间: {info['earliest_image_time']}")
            print(f"  需要更新: {'是' if info['should_update'] else '否'}")
            if args.update and info['should_update']:
                print(f"  更新状态: {'成功' if info.get('time_updated', False) else '失败'}")
        else:
            print(f"  最早图片时间: 未找到")

if __name__ == "__main__":
    main()
