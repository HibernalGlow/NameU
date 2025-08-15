#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Bandizip删除压缩包内特定文件的脚本
支持遍历目录下的所有压缩包
配置文件支持TOML格式
"""

import subprocess
import sys
import os
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback for older Python versions
    except ImportError:
        print("错误: 需要安装tomli库来解析TOML配置文件")
        print("请运行: pip install tomli")
        sys.exit(1)


def load_config():
    """
    加载TOML配置文件

    Returns:
        dict: 配置字典
    """
    config_path = Path(__file__).parent / "config.toml"
    
    # 尝试导入统一配置
    try:
        from ...nameu.core.config import get_tool_path
        default_bz_path = get_tool_path("bandizip_exe")
    except ImportError:
        default_bz_path = r"D:\1PRO\Bandizip\Bandizip\bz.exe"

    if not config_path.exists():
        print(f"警告: 配置文件不存在: {config_path}")
        print("使用默认配置...")
        return {
            'bandizip': {
                'executable': default_bz_path
            },
            'delete_patterns': {
                'default': ['*.json', '*.convert']
            },
            'archive': {
                'supported_extensions': ['*.zip', '*.rar', '*.7z', '*.tar', '*.gz', '*.bz2', '*.xz']
            }
        }

    try:
        with open(config_path, 'rb') as f:
            config = tomllib.load(f)
        print(f"已加载配置文件: {config_path}")
        return config
    except Exception as e:
        print(f"错误: 无法加载配置文件: {e}")
        print("使用默认配置...")
        return {
            'bandizip': {
                'executable': default_bz_path
            },
            'delete_patterns': {
                'default': ['*.json', '*.convert']
            },
            'archive': {
                'supported_extensions': ['*.zip', '*.rar', '*.7z', '*.tar', '*.gz', '*.bz2', '*.xz']
            }
        }


def find_archives_in_directory(directory_path, config, recursive=True):
    """
    在指定目录中查找所有压缩包文件

    Args:
        directory_path (str): 目录路径
        config (dict): 配置字典
        recursive (bool): 是否递归搜索子目录

    Returns:
        list: 压缩包文件路径列表
    """
    # 从配置文件获取支持的压缩包格式
    archive_extensions = config.get('archive', {}).get('supported_extensions',
                                                      ['*.zip', '*.rar', '*.7z', '*.tar', '*.gz', '*.bz2', '*.xz'])

    archives = []
    directory = Path(directory_path)

    if not directory.exists():
        print(f"错误: 目录不存在: {directory_path}")
        return []

    if not directory.is_dir():
        print(f"错误: 路径不是目录: {directory_path}")
        return []

    print(f"正在扫描目录: {directory_path}")
    print(f"递归搜索: {'是' if recursive else '否'}")
    print(f"支持的格式: {', '.join(archive_extensions)}")

    # 移除扩展名前的*号，用于Path.glob
    extensions = [ext.lstrip('*') for ext in archive_extensions]

    if recursive:
        # 递归搜索所有子目录
        for extension in extensions:
            pattern = f"**/*{extension}"
            found_files = list(directory.glob(pattern))
            archives.extend([str(f) for f in found_files if f.is_file()])
    else:
        # 只搜索当前目录
        for extension in extensions:
            pattern = f"*{extension}"
            found_files = list(directory.glob(pattern))
            archives.extend([str(f) for f in found_files if f.is_file()])

    # 去重并排序
    archives = sorted(list(set(archives)))

    print(f"找到 {len(archives)} 个压缩包文件:")
    for i, archive in enumerate(archives, 1):
        relative_path = os.path.relpath(archive, directory_path)
        print(f"  {i}. {relative_path}")

    return archives


def delete_files_from_archive(archive_path, file_patterns=None, config=None):
    """
    使用Bandizip删除压缩包内的文件

    Args:
        archive_path (str): 压缩包路径
        file_patterns (list): 要删除的文件模式列表
        config (dict): 配置字典

    Returns:
        tuple: (return_code, stdout, stderr)
    """
    if config is None:
        config = load_config()

    if file_patterns is None:
        file_patterns = config.get('delete_patterns', {}).get('default', ['*.json', '*.convert'])

    # 从配置文件获取Bandizip可执行文件路径
    bandizip_exe = config.get('bandizip', {}).get('executable', r"D:\1PRO\Bandizip\Bandizip\bz.exe")
    
    # 检查Bandizip是否存在
    if not os.path.exists(bandizip_exe):
        print(f"错误: Bandizip可执行文件不存在: {bandizip_exe}")
        return 1, "", f"Bandizip executable not found: {bandizip_exe}"
    
    # 检查压缩包是否存在
    if not os.path.exists(archive_path):
        print(f"错误: 压缩包文件不存在: {archive_path}")
        return 1, "", f"Archive file not found: {archive_path}"
    
    # 构建命令
    # bz.exe d "压缩包路径" 文件模式1 文件模式2 ...
    cmd = [bandizip_exe, "d", archive_path] + file_patterns
    
    print(f"执行命令: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        # 执行命令并实时显示输出
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 实时读取输出
        stdout_lines = []
        stderr_lines = []
        
        # 读取stdout
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                stdout_lines.append(output.strip())
        
        # 等待进程完成并获取stderr
        _, stderr = process.communicate()
        if stderr:
            print("错误输出:")
            print(stderr)
            stderr_lines.append(stderr)
        
        return_code = process.returncode
        stdout_text = '\n'.join(stdout_lines)
        stderr_text = '\n'.join(stderr_lines)
        
        print("-" * 50)
        if return_code == 0:
            print("操作完成成功!")
        else:
            print(f"操作失败，返回码: {return_code}")
        
        return return_code, stdout_text, stderr_text
        
    except Exception as e:
        error_msg = f"执行命令时发生错误: {str(e)}"
        print(error_msg)
        return 1, "", error_msg


def process_directory(directory_path, file_patterns=None, config=None):
    """
    处理目录下的所有压缩包

    Args:
        directory_path (str): 目录路径
        file_patterns (list): 要删除的文件模式列表
        config (dict): 配置字典

    Returns:
        tuple: (总数, 成功数, 失败数)
    """
    if config is None:
        config = load_config()

    if file_patterns is None:
        file_patterns = config.get('delete_patterns', {}).get('default', ['*.json', '*.convert'])

    # 从配置获取是否递归搜索
    recursive = config.get('archive', {}).get('recursive_search', True)
    archives = find_archives_in_directory(directory_path, config, recursive=recursive)

    if not archives:
        print("未找到任何压缩包文件。")
        return 0, 0, 0

    total_count = len(archives)
    success_count = 0
    failed_count = 0

    print(f"\n开始处理 {total_count} 个压缩包...")
    print("=" * 60)

    for i, archive_path in enumerate(archives, 1):
        print(f"\n[{i}/{total_count}] 处理: {os.path.basename(archive_path)}")
        print("-" * 40)

        return_code, _, _ = delete_files_from_archive(archive_path, file_patterns, config)

        if return_code == 0:
            success_count += 1
            print(f"✅ 成功处理: {os.path.basename(archive_path)}")
        else:
            failed_count += 1
            print(f"❌ 处理失败: {os.path.basename(archive_path)}")

    print("\n" + "=" * 60)
    print(f"处理完成! 总计: {total_count}, 成功: {success_count}, 失败: {failed_count}")

    return total_count, success_count, failed_count


def show_presets(config):
    """显示预定义的文件模式"""
    presets = config.get('delete_patterns', {}).get('presets', {})
    if not presets:
        print("没有可用的预设模式")
        return

    print("可用的预设模式:")
    for name, patterns in presets.items():
        print(f"  {name}: {' '.join(patterns)}")


def main():
    """主函数"""
    print("Bandizip压缩包文件删除工具")
    print("=" * 50)

    # 加载配置
    config = load_config()
    default_patterns = config.get('delete_patterns', {}).get('default', ['*.json', '*.convert'])

    if len(sys.argv) < 2:
        # 交互式输入
        input_path = input("请输入目录路径或压缩包路径: ").strip().strip('"')

        # 显示配置信息
        recursive = config.get('archive', {}).get('recursive_search', True)
        print(f"\n当前默认删除模式: {' '.join(default_patterns)}")
        print(f"递归搜索子目录: {'是' if recursive else '否'}")
        show_presets(config)

        # 询问文件模式选择
        print("\n选择删除模式:")
        print("1. 使用默认模式")
        print("2. 使用预设模式")
        print("3. 自定义模式")

        choice = input("请选择 (1-3) [默认: 1]: ").strip()

        if choice == '2':
            preset_name = input("请输入预设名称: ").strip()
            presets = config.get('delete_patterns', {}).get('presets', {})
            if preset_name in presets:
                file_patterns = presets[preset_name]
                print(f"使用预设 '{preset_name}': {' '.join(file_patterns)}")
            else:
                print(f"预设 '{preset_name}' 不存在，使用默认模式")
                file_patterns = default_patterns
        elif choice == '3':
            patterns_input = input("请输入要删除的文件模式 (用空格分隔): ").strip()
            file_patterns = patterns_input.split() if patterns_input else default_patterns
        else:
            file_patterns = default_patterns
    else:
        # 命令行参数
        input_path = sys.argv[1]
        if len(sys.argv) > 2:
            # 检查是否是预设名称
            if len(sys.argv) == 3 and not sys.argv[2].startswith('*'):
                preset_name = sys.argv[2]
                presets = config.get('delete_patterns', {}).get('presets', {})
                if preset_name in presets:
                    file_patterns = presets[preset_name]
                    print(f"使用预设 '{preset_name}': {' '.join(file_patterns)}")
                else:
                    file_patterns = [sys.argv[2]]
            else:
                file_patterns = sys.argv[2:]
        else:
            file_patterns = default_patterns

    # 处理路径中的引号
    input_path = input_path.strip('"')

    print(f"\n输入路径: {input_path}")
    print(f"删除文件模式: {' '.join(file_patterns)}")
    print(f"Bandizip路径: {config.get('bandizip', {}).get('executable', '未配置')}")
    print()

    # 判断是目录还是文件
    if os.path.isdir(input_path):
        # 处理目录下的所有压缩包
        _, _, failed = process_directory(input_path, file_patterns, config)
        exit_code = 0 if failed == 0 else 1
    elif os.path.isfile(input_path):
        # 处理单个压缩包文件
        print("检测到单个文件，直接处理...")
        return_code, _, _ = delete_files_from_archive(input_path, file_patterns, config)
        exit_code = return_code
    else:
        print(f"错误: 路径不存在: {input_path}")
        exit_code = 1

    # 返回退出码
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
