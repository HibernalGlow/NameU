"""
timex 核心功能：扫描压缩包内图片时间戳并生成 timeu 兼容的时间戳文件
"""
import os
import zipfile
import rarfile
import py7zr
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.svg'}

# 支持的压缩包格式
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z'}


class ArchiveImageScanner:
    """扫描压缩包内图片时间戳的核心类"""
    
    def __init__(self):
        self.results = {}
    
    def is_image_file(self, filename: str) -> bool:
        """检查文件是否为图片文件"""
        return Path(filename).suffix.lower() in IMAGE_EXTENSIONS
    
    def is_archive_file(self, filename: str) -> bool:
        """检查文件是否为压缩包文件"""
        return Path(filename).suffix.lower() in ARCHIVE_EXTENSIONS
    
    def scan_zip_images(self, zip_path: str) -> List[Tuple[str, float]]:
        """扫描ZIP文件中的图片时间戳"""
        image_times = []
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_file:
                for file_info in zip_file.infolist():
                    if not file_info.is_dir() and self.is_image_file(file_info.filename):
                        # 获取文件在压缩包内的修改时间
                        timestamp = time.mktime(file_info.date_time + (0, 0, -1))
                        image_times.append((file_info.filename, timestamp))
        except Exception as e:
            print(f"扫描ZIP文件 {zip_path} 时出错: {e}")
        return image_times
    
    def scan_rar_images(self, rar_path: str) -> List[Tuple[str, float]]:
        """扫描RAR文件中的图片时间戳"""
        image_times = []
        try:
            with rarfile.RarFile(rar_path, 'r') as rar_file:
                for file_info in rar_file.infolist(): 
                    if not file_info.is_dir() and self.is_image_file(file_info.filename):
                        # 获取文件在压缩包内的修改时间
                        if file_info.date_time:
                            timestamp = time.mktime(file_info.date_time + (0, 0, -1))
                            image_times.append((file_info.filename, timestamp))
        except Exception as e:
            print(f"扫描RAR文件 {rar_path} 时出错: {e}")
        return image_times
    
    def scan_7z_images(self, seven_z_path: str) -> List[Tuple[str, float]]:
        """扫描7Z文件中的图片时间戳"""
        image_times = []
        try:
            with py7zr.SevenZipFile(seven_z_path, 'r') as seven_z_file:
                for file_info in seven_z_file.list():
                    if not file_info.is_dir and self.is_image_file(file_info.filename):
                        # 获取文件在压缩包内的修改时间
                        if file_info.creationtime:
                            timestamp = file_info.creationtime.timestamp()
                            image_times.append((file_info.filename, timestamp))
        except Exception as e:
            print(f"扫描7Z文件 {seven_z_path} 时出错: {e}")
        return image_times
    
    def scan_archive_images(self, archive_path: str) -> List[Tuple[str, float]]:
        """根据文件扩展名选择合适的扫描方法"""
        ext = Path(archive_path).suffix.lower()
        if ext == '.zip':
            return self.scan_zip_images(archive_path)
        elif ext == '.rar':
            return self.scan_rar_images(archive_path)
        elif ext == '.7z':
            return self.scan_7z_images(archive_path)
        else:
            print(f"不支持的压缩包格式: {ext}")
            return []
    
    def get_folder_timestamps(self, folder_path: str) -> Tuple[float, float]:
        """获取文件夹的创建时间和修改时间"""
        stat = os.stat(folder_path)
        return stat.st_ctime, stat.st_mtime
    
    def find_earliest_image_time(self, folder_path: str) -> Optional[float]:
        """在文件夹中查找压缩包内图片的最早时间"""
        earliest_time = None
        
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path) and self.is_archive_file(item):
                print(f"扫描压缩包: {item}")
                image_times = self.scan_archive_images(item_path)
                
                for image_name, image_time in image_times:
                    print(f"  图片: {image_name}, 时间: {datetime.fromtimestamp(image_time)}")
                    if earliest_time is None or image_time < earliest_time:
                        earliest_time = image_time
        
        return earliest_time
    
    def scan_directory(self, base_path: str) -> Dict[str, Dict[str, float]]:
        """扫描指定路径下一级文件夹中的压缩包图片时间戳"""
        timestamp_data = {}
        
        if not os.path.exists(base_path):
            print(f"路径不存在: {base_path}")
            return timestamp_data
        
        print(f"开始扫描路径: {base_path}")
        
        # 遍历一级子文件夹
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                print(f"\n处理文件夹: {item}")
                
                # 获取文件夹当前的时间戳
                folder_ctime, folder_mtime = self.get_folder_timestamps(item_path)
                print(f"  文件夹创建时间: {datetime.fromtimestamp(folder_ctime)}")
                print(f"  文件夹修改时间: {datetime.fromtimestamp(folder_mtime)}")
                
                # 查找文件夹内压缩包中图片的最早时间
                earliest_image_time = self.find_earliest_image_time(item_path)
                
                if earliest_image_time is not None:
                    print(f"  压缩包内最早图片时间: {datetime.fromtimestamp(earliest_image_time)}")
                    
                    # 检查是否需要更新文件夹时间戳
                    need_update = False
                    new_time = earliest_image_time
                    
                    if earliest_image_time < folder_ctime or earliest_image_time < folder_mtime:
                        need_update = True
                        print(f"  需要更新文件夹时间戳")
                    else:
                        print(f"  文件夹时间戳不需要更新")
                    
                    if need_update:
                        # 生成 timeu 格式的时间戳数据
                        timestamp_data[item_path] = {
                            "access_time": new_time,
                            "mod_time": new_time
                        }
                        print(f"  已添加到更新列表")
                else:
                    print(f"  未找到压缩包内的图片")
        
        return timestamp_data
    
    def save_timestamp_file(self, timestamp_data: Dict[str, Dict[str, float]], output_path: str):
        """保存时间戳数据到JSON文件（timeu格式）"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(timestamp_data, f, ensure_ascii=False, indent=2)
            print(f"\n时间戳文件已保存到: {output_path}")
            print(f"共包含 {len(timestamp_data)} 个文件夹的时间戳更新信息")
        except Exception as e:
            print(f"保存时间戳文件时出错: {e}")


def main():
    """主函数示例"""
    scanner = ArchiveImageScanner()
    
    # 示例使用
    base_path = input("请输入要扫描的基础路径: ").strip()
    if not base_path:
        print("未提供路径，退出")
        return
    
    # 扫描目录
    timestamp_data = scanner.scan_directory(base_path)
    
    if timestamp_data:
        # 生成输出文件路径
        output_path = f"timestamps_timex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        scanner.save_timestamp_file(timestamp_data, output_path)
        
        print(f"\n可以使用以下命令应用时间戳:")
        print(f"python -m timeu {output_path}")
    else:
        print("\n未发现需要更新时间戳的文件夹")


if __name__ == "__main__":
    main()
