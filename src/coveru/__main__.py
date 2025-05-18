import os
import zipfile
import shutil
import subprocess
from pathlib import Path

def get_largest_zip(folder_path):
    """
    找到文件夹中最大的 .zip 文件。

    参数:
    folder_path (str): 要搜索的文件夹路径。

    返回:
    str: 最大的 .zip 文件的路径，如果未找到则返回 None。
    """
    largest_size = 0
    largest_zip = None
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.zip'):
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                if size > largest_size:
                    largest_size = size
                    largest_zip = file_path
    return largest_zip

def convert_to_jxl(image_path):
    """
    将图片转换为JXL格式。

    参数:
    image_path (str): 需要转换的图片路径。

    返回:
    str: 转换后的JXL图片路径。
    """
    output_path = os.path.splitext(image_path)[0] + '.jxl'
    try:
        # 使用cjxl命令行工具转换图片，如果系统中有此工具
        subprocess.run(['cjxl', image_path, output_path], check=True)
        # 转换成功后删除原图
        os.remove(image_path)
        return output_path
    except (subprocess.SubprocessError, FileNotFoundError):
        print(f"转换失败: {image_path}，请确保安装了cjxl工具")
        return image_path

def extract_first_image_from_zip(zip_path, destination_folder):
    """
    从指定的 .zip 文件中提取第一张图片到目标文件夹。
    如果提取的图片不是JXL或AVIF格式，则转换为JXL。

    参数:
    zip_path (str): .zip 文件的路径。
    destination_folder (str): 图片提取的目标文件夹路径。
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            image_files = sorted([f for f in zip_ref.namelist() if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.avif', '.jxl'))])
            if image_files:
                first_image = image_files[0]
                zip_ref.extract(first_image, destination_folder)
                # Move the image to the destination folder root
                extracted_path = os.path.join(destination_folder, first_image)
                final_path = os.path.join(destination_folder, os.path.basename(first_image))
                shutil.move(extracted_path, final_path)
                
                # 检查提取的图片是否需要转换为JXL
                ext = Path(final_path).suffix.lower()
                if ext not in ['.jxl', '.avif']:
                    print(f"正在将图片转换为JXL: {final_path}")
                    final_path = convert_to_jxl(final_path)
                
                # 清理多余的目录结构
                extracted_dir = os.path.dirname(extracted_path)
                while extracted_dir != destination_folder:
                    try:
                        os.rmdir(extracted_dir)
                    except OSError as e:
                        if e.errno == 145:  # 目录不是空的
                            break
                        else:
                            raise
                    extracted_dir = os.path.dirname(extracted_dir)
    except zipfile.BadZipFile:
        print(f"损坏的压缩包: {zip_path}")

def process_folder(root_folder):
    """
    处理文件夹，如果子文件夹中没有图片，则从最大的 .zip 文件中提取第一张图片。

    参数:
    root_folder (str): 需要处理的根文件夹路径。
    """
    # 检查一级文件夹本身
    if os.path.isdir(root_folder):
        # 检查是否为隐藏文件夹
        if not os.path.basename(root_folder).startswith('.') and not os.path.basename(root_folder).startswith('{'):
            # 检查当前文件夹是否包含图片
            contains_image = any(file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.avif', '.jxl')) for file in os.listdir(root_folder))
            
            if not contains_image:
                largest_zip = get_largest_zip(root_folder)
                if largest_zip:
                    extract_first_image_from_zip(largest_zip, root_folder)
                else:
                    print(f"在 {root_folder} 中未找到压缩包")
            else:
                print(f"{root_folder} 包含图片，无需处理")
        else:
            print(f"跳过隐藏文件夹或特殊目录: {root_folder}")

    # 检查子文件夹
    for sub_folder in os.listdir(root_folder):
        sub_folder_path = os.path.join(root_folder, sub_folder)
        
        if os.path.isdir(sub_folder_path):
            # 检查是否为隐藏文件夹
            if not sub_folder.startswith('.') and not sub_folder.startswith('{'):
                # 检查当前文件夹是否包含图片
                contains_image = any(file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.avif', '.jxl')) for file in os.listdir(sub_folder_path))
                
                if not contains_image:
                    largest_zip = get_largest_zip(sub_folder_path)
                    if largest_zip:
                        extract_first_image_from_zip(largest_zip, sub_folder_path)
                    else:
                        print(f"在 {sub_folder_path} 中未找到压缩包")
                else:
                    print(f"{sub_folder_path} 包含图片，无需处理")
            else:
                print(f"跳过隐藏文件夹或特殊目录: {sub_folder_path}")
        else:
            print(f"{sub_folder_path} 不是文件夹，跳过")

def main():
    """
    主函数，提供命令行界面，支持以下功能：
    1. 处理单个文件夹
    2. 批量处理多个文件夹
    3. 提供可选的命令行参数支持
    """
    import argparse
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='处理文件夹中的ZIP文件并提取封面图片')
    parser.add_argument('folders', nargs='*', help='要处理的文件夹路径，可以提供多个')
    parser.add_argument('-r', '--recursive', action='store_true', help='是否递归处理子文件夹')
    parser.add_argument('--no-convert', action='store_true', help='不将图片转换为JXL格式')

    args = parser.parse_args()
    
    # 如果没有提供文件夹路径，则提示用户输入
    if not args.folders:
        folder_input = input("请输入需要处理的根文件夹路径（多个路径用分号分隔）: ")
        folders = [f.strip() for f in folder_input.split(';') if f.strip()]
    else:
        folders = args.folders
    
    # 检查提供的文件夹是否存在
    valid_folders = []
    for folder in folders:
        if not os.path.isdir(folder):
            print(f"错误: 文件夹 '{folder}' 不存在或不是一个目录")
        else:
            valid_folders.append(folder)
    
    if not valid_folders:
        print("没有有效的文件夹路径，程序退出")
        return
    
    # 处理每个有效的文件夹
    for folder in valid_folders:
        print(f"\n开始处理文件夹: {folder}")
        process_folder(folder)
        print(f"完成处理文件夹: {folder}")
    
    print("\n所有文件夹处理完毕！")

if __name__ == "__main__":
    main()