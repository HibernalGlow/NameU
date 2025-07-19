import os
import shutil
import subprocess
from pathlib import Path
from PIL import Image
import pillow_avif
import pillow_jxl
def get_largest_zip(folder_path):
    """
    找到文件夹中最大的 .zip 文件。
    优先选择路径中不包含'画集'或'合刊'关键词的文件。

    参数:
    folder_path (str): 要搜索的文件夹路径。

    返回:
    str: 最大的 .zip 文件的路径，如果未找到则返回 None。
    """
    exclude_keywords = ['画集', '合刊', '商业', '单行']
    largest_size = 0
    largest_zip = None
    largest_size_excluded = 0
    largest_zip_excluded = None
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.zip'):
                file_path = os.path.join(root, file)
                size = os.path.getsize(file_path)
                
                # 检查路径中是否包含排除关键词
                contains_excluded_keyword = any(keyword in file_path for keyword in exclude_keywords)
                
                if not contains_excluded_keyword:
                    # 优先选择不包含排除关键词的文件
                    if size > largest_size:
                        largest_size = size
                        largest_zip = file_path
                else:
                    # 记录包含排除关键词的最大文件作为备用
                    if size > largest_size_excluded:
                        largest_size_excluded = size
                        largest_zip_excluded = file_path
    
    # 如果没有找到不包含排除关键词的文件，则使用包含关键词的文件
    if largest_zip is None and largest_zip_excluded is not None:
        print(f"警告: 只找到包含排除关键词的压缩包: {os.path.basename(largest_zip_excluded)}")
        return largest_zip_excluded
    
    return largest_zip

def convert_to_jxl(image_path):
    """
    使用 Pillow 将图片转换为JXL格式。

    参数:
    image_path (str): 需要转换的图片路径。

    返回:
    str: 转换后的JXL图片路径。
    """
    output_path = os.path.splitext(image_path)[0] + '.jxl'
    try:
        # 使用 Pillow 打开并转换图片
        with Image.open(image_path) as img:
            # 如果图片有透明通道，保持透明度
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # 对于有透明度的图片，保持原模式或转换为RGBA
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
            else:
                # 对于不透明图片，转换为RGB
                img = img.convert('RGB')
            
            # 保存为JXL格式，使用较高的质量设置
            img.save(output_path, format='JXL', quality=45, effort=7)
        
        # 转换成功后删除原图
        os.remove(image_path)
        print(f"已转换为JXL: {os.path.basename(output_path)}")
        return output_path
    except Exception as e:
        print(f"转换失败: {image_path}，错误: {str(e)}")
        return image_path

def convert_to_avif(image_path):
    """
    使用 Pillow 将图片转换为AVIF格式。

    参数:
    image_path (str): 需要转换的图片路径。

    返回:
    str: 转换后的AVIF图片路径。
    """
    output_path = os.path.splitext(image_path)[0] + '.avif'
    try:
        # 使用 Pillow 打开并转换图片
        with Image.open(image_path) as img:
            # 如果图片有透明通道，保持透明度
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                # 对于有透明度的图片，保持原模式或转换为RGBA
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
            else:
                # 对于不透明图片，转换为RGB
                img = img.convert('RGB')
            
            # 保存为AVIF格式，使用较高的质量设置
            img.save(output_path, format='AVIF', quality=85)
        
        # 转换成功后删除原图
        os.remove(image_path)
        print(f"已转换为AVIF: {os.path.basename(output_path)}")
        return output_path
    except Exception as e:
        print(f"转换失败: {image_path}，错误: {str(e)}")
        return image_path

def extract_first_image_from_zip(zip_path, destination_folder, convert_format='jxl', no_convert=False):
    """
    从指定的 .zip 文件中提取第一张图片到目标文件夹。
    根据指定格式转换图片。

    参数:
    zip_path (str): .zip 文件的路径。
    destination_folder (str): 图片提取的目标文件夹路径。
    convert_format (str): 转换的目标格式，'jxl' 或 'avif'。
    no_convert (bool): 是否跳过格式转换。
    """
    try:
        # 使用7z列出压缩包中的文件
        result = subprocess.run(
            ['7z', 'l', zip_path],
            capture_output=True,
            text=True,
            encoding='gbk',
            errors='ignore',
            check=True
        )

        # 查找图片文件
        image_files = []
        for line in result.stdout.splitlines():
            if line.strip() and not line.startswith('-') and not line.startswith('Date'):
                parts = line.split()
                if len(parts) >= 6:
                    filename = parts[-1]
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.avif', '.jxl')):
                        image_files.append(filename)

        if image_files:
            image_files.sort()
            first_image = image_files[0]

            # 使用7z提取第一张图片
            subprocess.run(
                ['7z', 'e', zip_path, first_image, f"-o{destination_folder}"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )

            extracted_path = os.path.join(destination_folder, os.path.basename(first_image))

            # 获取一级文件夹名称作为前缀
            folder_name = os.path.basename(destination_folder)
            original_filename = os.path.basename(first_image)
            name, ext = os.path.splitext(original_filename)

            # 添加前缀 (#cover)(文件夹名)
            new_filename = f"(#cover)({folder_name}){ext}"
            final_path = os.path.join(destination_folder, new_filename)

            shutil.move(extracted_path, final_path)

            # 检查提取的图片是否需要转换
            ext = Path(final_path).suffix.lower()
            if not no_convert and ext not in ['.jxl', '.avif']:
                if convert_format == 'jxl':
                    print(f"正在将图片转换为JXL: {final_path}")
                    final_path = convert_to_jxl(final_path)
                elif convert_format == 'avif':
                    print(f"正在将图片转换为AVIF: {final_path}")
                    final_path = convert_to_avif(final_path)

    except subprocess.CalledProcessError:
        print(f"无法处理压缩包: {zip_path}")

def process_folder(root_folder, convert_format='jxl', no_convert=False):
    """
    处理文件夹，如果子文件夹中没有图片，则从最大的 .zip 文件中提取第一张图片。

    参数:
    root_folder (str): 需要处理的根文件夹路径。
    convert_format (str): 转换的目标格式，'jxl' 或 'avif'。
    no_convert (bool): 是否跳过格式转换。
    """    # 检查一级文件夹本身
    if os.path.isdir(root_folder):
        # 检查是否为隐藏文件夹
        if not os.path.basename(root_folder).startswith('.') and not os.path.basename(root_folder).startswith('{'):
            # 检查当前文件夹是否包含图片
            contains_image = any(file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.avif', '.jxl')) for file in os.listdir(root_folder))
            
            if not contains_image:
                largest_zip = get_largest_zip(root_folder)
                if largest_zip:
                    extract_first_image_from_zip(largest_zip, root_folder, convert_format, no_convert)
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
                        extract_first_image_from_zip(largest_zip, sub_folder_path, convert_format, no_convert)
                    else:
                        print(f"在 {sub_folder_path} 中未找到压缩包")
                else:
                    print(f"{sub_folder_path} 包含图片，无需处理")
            else:
                print(f"跳过隐藏文件夹或特殊目录: {sub_folder_path}")
        else:
            print(f"{sub_folder_path} 不是文件夹，跳过")

def get_folders_from_user():
    """
    从用户获取文件夹路径列表。
    支持以下输入格式：
    - 带引号的路径（支持包含空格的路径）
    - 多行输入，每行一个路径
    - 空行作为输入结束符
    
    返回:
    list: 有效的文件夹路径列表
    """
    import shlex
    
    print("请输入需要处理的文件夹路径：")
    print("- 支持多行输入，每行一个路径")
    print("- 路径包含空格时请用引号包围")
    print("- 输入空行结束输入")
    print()
    
    folders = []
    line_number = 1
    
    while True:
        try:
            line = input(f"路径 {line_number}: ").strip()
            if not line:  # 空行，结束输入
                break
            
            # 使用shlex.split来正确处理带引号的路径
            try:
                parsed_paths = shlex.split(line)
                for path in parsed_paths:
                    if path.strip():
                        folders.append(path.strip())
            except ValueError as e:
                print(f"路径解析错误: {e}")
                print("请检查引号是否正确匹配")
                continue
            
            line_number += 1
            
        except KeyboardInterrupt:
            print("\n\n输入被中断")
            break
        except EOFError:
            # 处理Ctrl+D或文件结束
            break
    
    if not folders:
        print("未输入任何路径")
    
    return folders

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
    parser.add_argument('--no-convert', action='store_true', help='不转换图片格式')
    parser.add_argument('--format', choices=['jxl', 'avif'], default='jxl', help='转换图片的目标格式 (默认: jxl)')

    args = parser.parse_args()
    
    # 如果没有提供文件夹路径，则提示用户输入
    if not args.folders:
        folders = get_folders_from_user()
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
        process_folder(folder, args.format, args.no_convert)
        print(f"完成处理文件夹: {folder}")
    
    print("\n所有文件夹处理完毕！")

if __name__ == "__main__":
    main()