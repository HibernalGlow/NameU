import os
import re
import shlex
import shutil
import subprocess
import zipfile
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image
import pillow_avif
import pillow_jxl
import toml

# Try to use rich for colored output; fallback to built-in print
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt

    RICH_AVAILABLE = True
except Exception:
    Console = None
    Panel = None
    Prompt = None
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def cprint(msg, style=None, end="\n"):
    if console:
        if style:
            console.print(msg, style=style, end=end)
        else:
            console.print(msg, end=end)
    else:
        print(msg, end=end)


DEFAULT_IMAGE_EXTENSIONS = [
    '.png',
    '.jpg',
    '.jpeg',
    '.webp',
    '.avif',
    '.jxl',
    '.gif',
    '.bmp',
    '.tif',
    '.tiff',
    '.heic',
    '.heif',
    '.jfif',
]

DEFAULT_EXCLUDE_KEYWORDS = ['画集', '合刊', '商业', '单行']
DEFAULT_MAX_WORKERS = 4

ORIGINAL_FORMAT_TOKEN = 'original'
VALID_FORMAT_CHOICES = ('jxl', 'avif', 'o', 'original')
FORMAT_ALIASES = {
    'o': ORIGINAL_FORMAT_TOKEN,
    'original': ORIGINAL_FORMAT_TOKEN,
}
SUPPORTED_CONVERT_FORMATS = {'jxl', 'avif'}

DELIMITER_PATTERN = re.compile(r'[;,|]+')


DEFAULT_FORMAT = 'jxl'
MAX_WORKERS = DEFAULT_MAX_WORKERS
EXCLUDE_KEYWORDS = DEFAULT_EXCLUDE_KEYWORDS
IMAGE_EXTS = tuple(DEFAULT_IMAGE_EXTENSIONS)
JXL_QUALITY = 45
JXL_EFFORT = 7
AVIF_QUALITY = 85


def _normalize_extensions(exts):
    normalized = []
    for ext in exts:
        if not ext:
            continue
        ext = ext.strip().lower()
        if not ext:
            continue
        if not ext.startswith('.'):
            ext = f'.{ext}'
        if ext not in normalized:
            normalized.append(ext)
    return tuple(normalized)


def _normalize_format_choice(value):
    if value is None:
        return None
    token = value.strip().lower()
    if not token:
        return None
    token = FORMAT_ALIASES.get(token, token)
    if token in SUPPORTED_CONVERT_FORMATS or token == ORIGINAL_FORMAT_TOKEN:
        return token
    return None


def _format_display_label(value):
    if value == ORIGINAL_FORMAT_TOKEN:
        return 'o (保持原格式)'
    return value


def normalize_user_path(raw_path: str) -> str:
    candidate = raw_path.strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {'"', "'"}:
        candidate = candidate[1:-1]
    candidate = os.path.expandvars(os.path.expanduser(candidate))
    return os.path.normpath(candidate)


def _parse_user_path_line(line: str):
    cleaned = line.strip()
    if not cleaned:
        return []

    if DELIMITER_PATTERN.search(cleaned):
        candidates = [segment.strip() for segment in DELIMITER_PATTERN.split(cleaned) if segment.strip()]
    else:
        try:
            candidates = shlex.split(cleaned)
        except ValueError:
            candidates = [cleaned]

    if len(candidates) == 1 and not any(q in cleaned for q in ('"', "'")):
        candidates = [cleaned]

    normalized = []
    for path in candidates:
        norm_path = normalize_user_path(path)
        if norm_path and norm_path not in normalized:
            normalized.append(norm_path)
    return normalized


def _flatten_folders(folders, recursive=False):
    if not recursive:
        for folder in folders:
            yield folder
        return

    queue = deque(folders)
    while queue:
        current = queue.popleft()
        yield current
        for sub in _iter_subdirectories(current):
            queue.append(sub)


def _process_folders_parallel(folders, convert_format, no_convert, max_workers):
    futures = []
    total = len(folders)
    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for folder in folders:
            futures.append(executor.submit(process_folder, folder, convert_format, no_convert))

        for future in as_completed(futures):
            completed += 1
            try:
                future.result()
                cprint(f"[并发] {completed}/{total} 个文件夹处理完成", style="green")
            except Exception as exc:
                cprint(f"并发任务失败: {exc}", style="bold red")


def _render_path_instructions():
    instructions = (
        "- 支持多行输入，每行可输入多个路径\n"
        "- 可使用引号包裹含空格的路径\n"
        "- 也可使用逗号/分号/竖线分隔多个路径\n"
        "- 输入空行结束输入"
    )
    if console and Panel:
        console.print(Panel(instructions, title="路径输入说明", expand=False, border_style="cyan"))
    else:
        cprint("请输入需要处理的文件夹路径：", style="bold")
        for line in instructions.split('\n'):
            cprint(line)


def _should_skip_folder(name: str) -> bool:
    return name.startswith('.') or name.startswith('{')


def _iter_subdirectories(folder):
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_dir():
                    yield entry.path
    except FileNotFoundError:
        return


def get_largest_zip(folder_path):
    """
    找到文件夹中最大的 .zip 文件。
    优先选择路径中不包含'画集'或'合刊'关键词的文件。

    参数:
    folder_path (str): 要搜索的文件夹路径。

    返回:
    str: 最大的 .zip 文件的路径，如果未找到则返回 None。
    """
    global EXCLUDE_KEYWORDS
    exclude_keywords = EXCLUDE_KEYWORDS
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
        cprint(f"警告: 只找到包含排除关键词的压缩包: {os.path.basename(largest_zip_excluded)}", style="yellow")
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
            img.save(output_path, format='JXL', quality=JXL_QUALITY, effort=JXL_EFFORT)

        # 转换成功后删除原图
        os.remove(image_path)
        cprint(f"已转换为JXL: {os.path.basename(output_path)}", style="green")
        return output_path
    except Exception as e:
        cprint(f"转换失败: {image_path}，错误: {str(e)}", style="bold red")
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
            img.save(output_path, format='AVIF', quality=AVIF_QUALITY)

        # 转换成功后删除原图
        os.remove(image_path)
        cprint(f"已转换为AVIF: {os.path.basename(output_path)}", style="green")
        return output_path
    except Exception as e:
        cprint(f"转换失败: {image_path}，错误: {str(e)}", style="bold red")
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
    global IMAGE_EXTS
    # 首先尝试使用 7z（性能/兼容路径更好），失败时回退到 Python 的 zipfile
    image_exts = IMAGE_EXTS
    first_image = None
    extracted_path = None

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
                    if filename.lower().endswith(image_exts):
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

            # 如果提取后文件不存在，触发后续回退逻辑
            if not os.path.exists(extracted_path):
                extracted_path = None

    except (subprocess.CalledProcessError, FileNotFoundError):
        # 7z 不可用或调用失败，回退到 zipfile
        extracted_path = None

    # 如果 7z 未能获取到文件路径，则使用 zipfile 回退
    if extracted_path is None:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # 过滤出图片文件
                candidates = [n for n in zf.namelist() if n.lower().endswith(image_exts)]
                if not candidates:
                    # 无图片，直接返回
                    return
                candidates.sort()
                first_image = candidates[0]

                # 安全提取为目标文件夹的 basename（防止路径穿越或目录结构）
                original_basename = os.path.basename(first_image)
                target_path = os.path.join(destination_folder, original_basename)

                # 读取并写入到目标文件
                with zf.open(first_image) as src, open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)

                extracted_path = target_path
        except Exception:
            cprint(f"无法处理压缩包: {zip_path}", style="bold red")
            return

    # 到这里 extracted_path 已存在且指向提取出的文件
    if extracted_path and os.path.exists(extracted_path):
        # 获取一级文件夹名称作为前缀
        folder_name = os.path.basename(destination_folder)
        original_filename = os.path.basename(extracted_path)
        name, ext = os.path.splitext(original_filename)

        # 添加前缀 (#cover)(文件夹名)
        new_filename = f"(#cover)({folder_name}){ext}"
        final_path = os.path.join(destination_folder, new_filename)

        # 如果目标文件已经存在，选择覆盖
        try:
            if os.path.exists(final_path):
                os.remove(final_path)
            shutil.move(extracted_path, final_path)
            cprint(f"已写入封面: {final_path}", style="green")
        except Exception as e:
            cprint(f"移动提取文件失败: {e}", style="bold red")
            return

        # 检查提取的图片是否需要转换
        ext = Path(final_path).suffix.lower()
        if not no_convert and convert_format != ORIGINAL_FORMAT_TOKEN and ext not in ['.jxl', '.avif']:
            if convert_format == 'jxl':
                cprint(f"正在将图片转换为JXL: {final_path}", style="cyan")
                final_path = convert_to_jxl(final_path)
            elif convert_format == 'avif':
                cprint(f"正在将图片转换为AVIF: {final_path}", style="cyan")
                final_path = convert_to_avif(final_path)

def folder_contains_image(folder_path):
    """
    判断文件夹（仅当前层级）是否包含图片文件或已生成的封面文件。
    返回 True/False。
    """
    global IMAGE_EXTS
    from pathlib import Path as _P
    image_exts = set(IMAGE_EXTS)
    try:
        with os.scandir(folder_path) as it:
            for entry in it:
                # 只检测常规文件（忽略子目录）
                if not entry.is_file():
                    continue
                name = entry.name
                # 如果已经有脚本生成的封面文件，认为文件夹已包含图片
                if '(#cover)(' in name:
                    return True
                # 检查扩展名
                if _P(name).suffix.lower() in image_exts:
                    return True
    except Exception:
        # 读取目录失败时，返回 False 以便上层能够尝试后续处理
        return False
    return False

def process_folder(root_folder, convert_format='jxl', no_convert=False):
    """
    处理文件夹，如果子文件夹中没有图片，则从最大的 .zip 文件中提取第一张图片。

    参数:
    root_folder (str): 需要处理的根文件夹路径。
    convert_format (str): 转换的目标格式，'jxl' 或 'avif'。
    no_convert (bool): 是否跳过格式转换。
    """    # 检查一级文件夹本身
    if os.path.isdir(root_folder):
        folder_name = os.path.basename(root_folder)
        if not _should_skip_folder(folder_name):
            # 检查当前文件夹是否包含图片
            contains_image = folder_contains_image(root_folder)

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
    for sub_folder_path in _iter_subdirectories(root_folder):
        sub_folder = os.path.basename(sub_folder_path)
        if _should_skip_folder(sub_folder):
            print(f"跳过隐藏文件夹或特殊目录: {sub_folder_path}")
            continue

        contains_image = folder_contains_image(sub_folder_path)
        if not contains_image:
            largest_zip = get_largest_zip(sub_folder_path)
            if largest_zip:
                extract_first_image_from_zip(largest_zip, sub_folder_path, convert_format, no_convert)
            else:
                print(f"在 {sub_folder_path} 中未找到压缩包")
        else:
            print(f"{sub_folder_path} 包含图片，无需处理")


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
    _render_path_instructions()
    
    folders = []
    line_number = 1
    
    while True:
        try:
            line = input(f"路径 {line_number}: ")
            if not line.strip():  # 空行，结束输入
                break
            
            parsed_paths = _parse_user_path_line(line)
            if not parsed_paths:
                print("未识别任何有效路径，请重试。")
                continue

            folders.extend(parsed_paths)
            
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

def get_format_from_user(default: str) -> str:
    """
    交互式选择图片转换格式，默认 avif。
    
    返回:
    str: 'jxl' 或 'avif'
    """
    choices_label = '/'.join(['jxl', 'avif', 'o'])
    prompt = f"选择转换格式 ({choices_label}) [默认: {_format_display_label(default)}]: "
    while True:
        try:
            choice = input(prompt).strip().lower()
            if choice == '':
                return default
            normalized = _normalize_format_choice(choice)
            if normalized:
                return normalized
            print("无效输入，请输入 'jxl'/'avif'/'o'，或直接回车使用默认值。")
        except (KeyboardInterrupt, EOFError):
            print("\n使用默认格式。")
            return default

def main():
    """
    主函数，提供命令行界面，支持以下功能：
    1. 处理单个文件夹
    2. 批量处理多个文件夹
    3. 提供可选的命令行参数支持
    """    
    import argparse
    
    # 加载配置
    config_path = Path(__file__).parent / "config.toml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
    except FileNotFoundError:
        print(f"配置文件 {config_path} 未找到，使用默认配置")
        config = {
            'general': {
                'default_format': 'jxl',
                'exclude_keywords': DEFAULT_EXCLUDE_KEYWORDS,
                'image_extensions': DEFAULT_IMAGE_EXTENSIONS,
                'max_workers': DEFAULT_MAX_WORKERS,
            },
            'jxl': {'quality': 45, 'effort': 7},
            'avif': {'quality': 85}
        }
    
    general_cfg = config.get('general', {})
    jxl_cfg = config.get('jxl', {})
    avif_cfg = config.get('avif', {})

    # 设置全局配置变量
    global EXCLUDE_KEYWORDS, IMAGE_EXTS, DEFAULT_FORMAT, JXL_QUALITY, JXL_EFFORT, AVIF_QUALITY, MAX_WORKERS
    EXCLUDE_KEYWORDS = general_cfg.get('exclude_keywords', DEFAULT_EXCLUDE_KEYWORDS)
    IMAGE_EXTS = _normalize_extensions(general_cfg.get('image_extensions', DEFAULT_IMAGE_EXTENSIONS))
    DEFAULT_FORMAT = general_cfg.get('default_format', 'jxl')
    MAX_WORKERS = general_cfg.get('max_workers', DEFAULT_MAX_WORKERS)
    JXL_QUALITY = jxl_cfg.get('quality', 45)
    JXL_EFFORT = jxl_cfg.get('effort', 7)
    AVIF_QUALITY = avif_cfg.get('quality', 85)
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='处理文件夹中的ZIP文件并提取封面图片')
    parser.add_argument('folders', nargs='*', help='要处理的文件夹路径，可以提供多个')
    parser.add_argument('-r', '--recursive', action='store_true', help='是否递归处理子文件夹')
    parser.add_argument('--no-convert', action='store_true', help='不转换图片格式')
    parser.add_argument('--format', choices=VALID_FORMAT_CHOICES, default=None, help='转换图片的目标格式；支持 jxl/avif/o (保持原格式)，未提供时将交互选择 (默认: 配置)')
    parser.add_argument('--max-workers', type=int, default=None, help='并发处理的最大线程数 (默认配置或 4)')

    args = parser.parse_args()
    
    # 如果没有提供文件夹路径，则提示用户输入
    if not args.folders:
        folders = get_folders_from_user()
    else:
        folders = []
        for raw_path in args.folders:
            folders.extend(_parse_user_path_line(raw_path))

    # 若未显式指定格式，则进行交互式选择（除非指定了不转换）
    target_format = DEFAULT_FORMAT if not args.no_convert else ORIGINAL_FORMAT_TOKEN

    if args.format is not None:
        normalized_cli_format = _normalize_format_choice(args.format)
        if not normalized_cli_format:
            raise SystemExit(f"无效的 --format 值: {args.format}")
        target_format = normalized_cli_format
    elif not args.no_convert:
        target_format = get_format_from_user(default=DEFAULT_FORMAT)
    else:
        target_format = ORIGINAL_FORMAT_TOKEN
    
    flattened = list(_flatten_folders(folders, recursive=args.recursive))

    # 检查提供的文件夹是否存在
    valid_folders = []
    for folder in flattened:
        if not os.path.isdir(folder):
            print(f"错误: 文件夹 '{folder}' 不存在或不是一个目录")
        else:
            valid_folders.append(folder)
    
    if not valid_folders:
        print("没有有效的文件夹路径，程序退出")
        return
    max_workers = max(1, args.max_workers or MAX_WORKERS)

    if len(valid_folders) > 1 and max_workers > 1:
        cprint(f"使用并发处理: {max_workers} 个线程", style="cyan")
        _process_folders_parallel(valid_folders, target_format, args.no_convert, max_workers)
    else:
        # 处理每个有效的文件夹
        for folder in valid_folders:
            print(f"\n开始处理文件夹: {folder}")
            process_folder(folder, target_format, args.no_convert)
            print(f"完成处理文件夹: {folder}")
    
    print("\n所有文件夹处理完毕！")

if __name__ == "__main__":
    main()