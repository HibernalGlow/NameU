"""
文件处理模块，提供文件和文件夹处理功能
"""

import os
from loguru import logger
from tqdm import tqdm
from .constants import ARCHIVE_EXTENSIONS, exclude_keywords, forbidden_artist_keywords
from .filename_processor import (
    detect_and_decode_filename, get_unique_filename, get_unique_filename_with_samename,
    format_folder_name, has_artist_name, convert_sensitive_words_to_pinyin,
    check_sensitive_word, get_sensitive_words_in_filename, get_unique_filename_with_pinyin_conversion
)
from .progress import init_progress, get_manager, FileStatus

# 导入压缩包ID管理模块
try:
    from nameset.integration import process_file_with_id_tracking
    ID_TRACKING_AVAILABLE = True
except ImportError:
    logger.warning("压缩包ID管理模块不可用，将使用传统重命名方式")
    ID_TRACKING_AVAILABLE = False

# 尝试直接导入ID处理以便在无需重命名时也能补写注释
if ID_TRACKING_AVAILABLE:
    try:
        from nameset.id_handler import ArchiveIDHandler as _ArchiveIDHandler
    except ImportError:  # 理论上不会发生，因为integration已可导入
        _ArchiveIDHandler = None
else:
    _ArchiveIDHandler = None

def process_files_in_directory(directory, artist_name, add_artist_name_enabled=True, convert_sensitive_enabled=True, threads: int = 1, track_ids: bool = True):
    """
    处理目录下的所有文件
    
    Args:
        directory: 目录路径
        artist_name: 画师名称
        add_artist_name_enabled: 是否添加画师名
        convert_sensitive_enabled: 是否将敏感词转换为拼音
        
    Returns:
        int: 修改的文件数量
    """
    # 获取目录下所有压缩文件 (使用 os.scandir 代替 os.listdir)
    files_info = []
    with os.scandir(directory) as it:
        for entry in it:
            if entry.is_file() and entry.name.lower().endswith(ARCHIVE_EXTENSIONS):
                files_info.append(entry.name)

    # 如果启用并行且文件数>1，走并行规划路径
    if threads and threads > 1 and len(files_info) > 1:
        return process_files_in_directory_parallel(
            directory=directory,
            artist_name=artist_name,
            add_artist_name_enabled=add_artist_name_enabled,
            convert_sensitive_enabled=convert_sensitive_enabled,
            threads=threads,
            track_ids=track_ids,
        )
    
    modified_files_count = 0
    
    # 检查是否是排除的文件夹（仅用于决定是否添加画师名）
    is_excluded = any(keyword in directory for keyword in exclude_keywords)
    
    # 检查是否包含禁止画师名的关键词
    has_forbidden = any(keyword in directory for keyword in forbidden_artist_keywords)
    
    # 先检查是否有需要修改的文件
    files_to_modify = []
    # 统计：未改名但补写ID
    auto_ids_created = 0
    auto_db_records_created = 0

    # 准备可复用的管理器（减少频繁打开）
    if ID_TRACKING_AVAILABLE and track_ids:
        try:
            from nameset.manager import ArchiveIDManager as _ArchiveIDManager
            _manager = _ArchiveIDManager()
        except ImportError:
            _manager = None
    else:
        _manager = None

    # 统计信息
    files = files_info
    pm = get_manager()
    for filename in files:
        original_file_path = os.path.join(directory, filename)
        if pm: pm.add_file(original_file_path, directory)
        
        filename = detect_and_decode_filename(filename)
        new_filename = filename
        
        # 对所有文件应用格式化，包括排除文件夹中的文件
        new_filename = get_unique_filename(directory, new_filename, artist_name, is_excluded)
        
        # 检查是否含有敏感词，如果启用了敏感词转换，则将敏感词转换为拼音
        if convert_sensitive_enabled and check_sensitive_word(new_filename):
            logger.info(f"文件名含有敏感词，开始转换为拼音: {new_filename}")
            sensitive_words = get_sensitive_words_in_filename(new_filename)
            logger.info(f"检测到的敏感词: {', '.join(sensitive_words)}")
            new_filename = convert_sensitive_words_to_pinyin(new_filename)
            logger.info(f"转换后的文件名: {new_filename}")
            
        # 只有在非排除文件夹、启用了画师名添加、不包含禁止关键词时才添加画师名
        if not is_excluded and not has_forbidden_keyword(directory) and add_artist_name_enabled and artist_name not in exclude_keywords and not has_artist_name(new_filename, artist_name):
            # 将画师名追加到文件名末尾
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}{artist_name}{ext}"
        
        # 确保文件名唯一（始终传入原始路径以排除自身）
        final_filename = get_unique_filename_with_samename(directory, new_filename, original_file_path)
        
        rename_needed = final_filename != filename
        if rename_needed:
            files_to_modify.append((filename, final_filename, original_file_path))
        else:
            # 文件名无需修改，但仍需确保压缩包已写入ID注释并同步数据库
            if track_ids and ID_TRACKING_AVAILABLE and _ArchiveIDHandler and original_file_path.lower().endswith(ARCHIVE_EXTENSIONS):
                try:
                    # 串行补写逻辑保留以兼容单线程
                    comment = _ArchiveIDHandler.get_archive_comment(original_file_path)
                    existing_id = _ArchiveIDHandler.extract_id_from_comment(comment)
                    if not existing_id:
                        created_id = _ArchiveIDHandler.get_or_create_archive_id(
                            original_file_path,
                            metadata={
                                'artist_name': artist_name if artist_name not in exclude_keywords else None,
                                'auto_add': True,
                                'reason': 'ensure_id_without_rename'
                            }
                        )
                        if created_id:
                            auto_ids_created += 1
                            logger.info(f"为未改名文件补写ID: {os.path.basename(original_file_path)} -> {created_id}")
                            existing_id = created_id
                    
                    if existing_id and _manager:
                        info = _manager.get_archive_info(existing_id)
                        if not info:
                            _manager.db.create_archive_record(
                                existing_id,
                                original_file_path,
                                os.path.basename(original_file_path),
                                artist_name if artist_name not in exclude_keywords else None
                            )
                            auto_db_records_created += 1
                    
                    if pm: pm.update_status(original_file_path, FileStatus.DONE)
                except Exception as e:
                    if pm: pm.update_status(original_file_path, FileStatus.FAILED)
                    logger.error(f"补写ID时出错 {original_file_path}: {e}")

    # 输出统计信息（仅当前目录作用域）
    if (auto_ids_created + auto_db_records_created) > 0:
        logger.info(
            f"未改名补写统计 -> 新建ID: {auto_ids_created} 个, 数据库补建记录: {auto_db_records_created} 个 (目录: {directory})"
        )

    # 关闭管理器
    if track_ids and ID_TRACKING_AVAILABLE and '_manager' in locals() and _manager:
        try:
            _manager.close()
        except Exception:
            pass

    # 如果有文件需要修改，显示进度条并处理
    if files_to_modify:
        with tqdm(total=len(files_to_modify), desc=f"重命名文件", unit="file", ncols=0, leave=True) as pbar:
            for filename, new_filename, original_file_path in files_to_modify:
                # 获取原始文件的时间戳
                original_stat = os.stat(original_file_path)
                
                new_file_path = os.path.join(directory, new_filename)
                
                try:
                    if pm: pm.update_status(original_file_path, FileStatus.PROCESSING)
                    # 检查是否为压缩文件并且启用了ID跟踪
                    is_archive = original_file_path.lower().endswith(ARCHIVE_EXTENSIONS)
                    
                    if is_archive and ID_TRACKING_AVAILABLE and track_ids:
                        # 使用ID跟踪的重命名方式
                        success = process_file_with_id_tracking(
                            original_file_path, 
                            new_filename, 
                            artist_name if artist_name not in exclude_keywords else None
                        )
                        if success:
                            new_file_path = os.path.join(directory, new_filename)
                            if pm: pm.update_status(original_file_path, FileStatus.DONE)
                        else:
                            logger.error(f"ID跟踪重命名失败，回退到传统方式: {filename}")
                            # 回退到传统重命名方式
                            os.rename(original_file_path, new_file_path)
                            if pm: pm.update_status(original_file_path, FileStatus.DONE)
                    else:
                        # 传统重命名方式
                        os.rename(original_file_path, new_file_path)
                        if pm: pm.update_status(original_file_path, FileStatus.DONE)
                    
                    # 恢复时间戳（对于传统方式）
                    if not (is_archive and ID_TRACKING_AVAILABLE and track_ids):
                        os.utime(new_file_path, (original_stat.st_atime, original_stat.st_mtime))
                    
                    try:
                        # 尝试获取相对路径以便更清晰的日志显示
                        base_path = os.path.dirname(os.path.dirname(directory))
                        rel_old_path = os.path.relpath(original_file_path, base_path)
                        rel_new_path = os.path.relpath(new_file_path, base_path)
                    except ValueError:
                        rel_old_path = original_file_path
                        rel_new_path = new_file_path
                        
                    log_message = f"重命名: {rel_old_path} -> {rel_new_path}"
                    logger.info(log_message)
                except OSError as e:
                    # 检查是否是文件已存在错误 (WinError 183)
                    if e.winerror == 183 or "文件已存在" in str(e):
                        # 记录冲突
                        with _conflict_lock:
                            _conflict_records.append({
                                'source': original_file_path,
                                'target': new_file_path,
                                'error': str(e)
                            })
                        logger.error(f"❌ 文件重命名失败: {e}: '{original_file_path}' -> '{new_file_path}'")
                    else:
                        logger.error(f"重命名文件失败 {original_file_path}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"重命名文件失败 {original_file_path}: {str(e)}")
                    continue
                    
                # 更新进度条，但不显示文件名（避免重复）
                pbar.update(1)
                modified_files_count += 1

    return modified_files_count

# ======================= 并行实现 =======================
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

_unique_name_lock = Lock()  # 仅在极端情况需要再计算唯一名时保护
_conflict_records = []  # 记录冲突的文件路径
_conflict_lock = Lock()  # 保护冲突记录列表

def _build_plan(directory, artist_name, add_artist_name_enabled, convert_sensitive_enabled, track_ids: bool = True):
    """第一阶段：串行计算最终目标文件名 & 需要重命名的列表。
    通过缓存 directory 内容避免 O(N^2) 重复扫描，并使用 os.scandir 加速。"""
    plan = []  # 每项: {original_path, original_name, target_name, is_archive, needs_rename}
    
    is_excluded = any(keyword in directory for keyword in exclude_keywords)
    has_forbidden = any(keyword in directory for keyword in forbidden_artist_keywords)

    # 1. 快速扫描目录并建立缓存
    from .filename_processor import normalize_filename
    existing_names = set()
    normalized_cache = {}  # normalized -> [actual_names]
    
    entries = []
    with os.scandir(directory) as it:
        for entry in it:
            if entry.is_file() and entry.name.lower().endswith(ARCHIVE_EXTENSIONS):
                name = entry.name
                existing_names.add(name)
                norm = normalize_filename(name)
                if norm not in normalized_cache:
                    normalized_cache[norm] = []
                normalized_cache[norm].append(name)
                entries.append(entry)

    # 2. 计算规划
    for entry in entries:
        filename = entry.name
        full_path = entry.path
        
        decoded = detect_and_decode_filename(filename)
        # 传入缓存加速计算
        new_filename = get_unique_filename(directory, decoded, artist_name, is_excluded, 
                                          existing_names=existing_names, normalized_cache=normalized_cache)
        
        if convert_sensitive_enabled and check_sensitive_word(new_filename):
            new_filename = convert_sensitive_words_to_pinyin(new_filename)
            
        if (not is_excluded and not has_forbidden and add_artist_name_enabled and artist_name not in exclude_keywords
                and not has_artist_name(new_filename, artist_name)):
            base, ext = os.path.splitext(new_filename)
            new_filename = f"{base}{artist_name}{ext}"
            
        # 传入缓存加速计算
        final_filename = get_unique_filename_with_samename(directory, new_filename, full_path,
                                                          existing_names=existing_names, normalized_cache=normalized_cache)
        
        rename_needed = final_filename != decoded
        
        # 无论是否改名，都加入 plan (ID 补写将在并行 worker 中处理)
        if rename_needed or (track_ids and ID_TRACKING_AVAILABLE):
            plan.append({
                'original_path': full_path,
                'original_name': decoded,
                'target_name': final_filename,
                'is_archive': True,
                'needs_rename': rename_needed
            })
            # 如果是改名，更新缓存以防后续冲突
            if rename_needed:
                existing_names.add(final_filename)
                norm_final = normalize_filename(final_filename)
                if norm_final not in normalized_cache:
                    normalized_cache[norm_final] = []
                normalized_cache[norm_final].append(final_filename)
        
        # 注册到进度管理器
        pm = get_manager()
        if pm:
            pm.add_file(full_path, directory)

    return plan

def _worker_rename(entry, directory, artist_name, track_ids: bool = True):
    original_path = entry['original_path']
    target_name = entry['target_name']
    target_path = os.path.join(directory, target_name)
    needs_rename = entry.get('needs_rename', True)
    
    pm = get_manager()
    if pm: pm.update_status(original_path, FileStatus.PROCESSING)
    
    try:
        if not os.path.exists(original_path):
            if pm: pm.update_status(original_path, FileStatus.FAILED)
            return False, 'missing'
        
        # 如果需要改名
        if needs_rename:
            original_stat = os.stat(original_path)
            if ID_TRACKING_AVAILABLE and track_ids:
                success = process_file_with_id_tracking(
                    original_path,
                    target_name,
                    artist_name if artist_name not in exclude_keywords else None
                )
                if success:
                    if pm: pm.update_status(original_path, FileStatus.DONE)
                    return True, 'renamed_with_id'
                else:
                    os.rename(original_path, target_path)
                    os.utime(target_path, (original_stat.st_atime, original_stat.st_mtime))
                    if pm: pm.update_status(original_path, FileStatus.DONE)
                    return True, 'fallback'
            else:
                os.rename(original_path, target_path)
                os.utime(target_path, (original_stat.st_atime, original_stat.st_mtime))
                if pm: pm.update_status(original_path, FileStatus.DONE)
                return True, 'renamed'
        else:
            # 不需要改名，但可能需要补 ID
            if track_ids and ID_TRACKING_AVAILABLE and _ArchiveIDHandler:
                comment = _ArchiveIDHandler.get_archive_comment(original_path)
                existing_id = _ArchiveIDHandler.extract_id_from_comment(comment)
                if not existing_id:
                    created_id = _ArchiveIDHandler.get_or_create_archive_id(
                        original_path,
                        metadata={'artist_name': artist_name if artist_name not in exclude_keywords else None,
                                  'auto_add': True,
                                  'reason': 'parallel_id_fill'}
                    )
                    if created_id:
                        if pm: pm.update_status(original_path, FileStatus.DONE)
                        return True, 'id_filled'
            if pm: pm.update_status(original_path, FileStatus.DONE)
            return True, 'no_change'

    except Exception as e:
        if pm: pm.update_status(original_path, FileStatus.FAILED)
        if isinstance(e, OSError) and (e.winerror == 183 or "文件已存在" in str(e)):
            with _conflict_lock:
                _conflict_records.append({'source': original_path, 'target': target_path, 'error': str(e)})
        return False, str(e)

def process_files_in_directory_parallel(directory, artist_name, add_artist_name_enabled=True, convert_sensitive_enabled=True, threads: int = 16, track_ids: bool = True):
    """并行处理目录下所有压缩包文件 (两阶段: 规划 + 并行执行)"""
    global _conflict_records
    # 每次处理新目录时清空冲突记录
    with _conflict_lock:
        _conflict_records = []
    
    plan = _build_plan(directory, artist_name, add_artist_name_enabled, convert_sensitive_enabled, track_ids=track_ids)
    if not plan:
        return 0
    total = len(plan)
    modified = 0
    from tqdm import tqdm as _tq
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [executor.submit(_worker_rename, entry, directory, artist_name, track_ids) for entry in plan]
        with _tq(total=total, desc=f"并行重命名 x{threads}", unit="file", ncols=0, leave=True) as bar:
            for fut in as_completed(futures):
                ok, info = fut.result()
                if ok:
                    modified += 1
                bar.update(1)
    logger.info(f"✅ 并行完成: {modified}/{total} (目录: {directory})")
    return modified

def process_artist_folder(artist_path, artist_name, add_artist_name_enabled=True, convert_sensitive_enabled=True, threads: int = 1, track_ids: bool = True):
    """递归处理画师文件夹及其所有子文件夹
    
    Args:
        artist_path: 画师文件夹路径
        artist_name: 画师名称
        add_artist_name_enabled: 是否添加画师名
        convert_sensitive_enabled: 是否将敏感词转换为拼音
    """
    total_modified_files_count = 0

    try:
        # 检查当前文件夹是否在排除列表中
        if any(keyword in artist_path for keyword in exclude_keywords):
            return 0

        for root, dirs, files in os.walk(artist_path, topdown=True):
            # 如果当前目录包含排除关键词，跳过整个目录
            if any(keyword in root for keyword in exclude_keywords):
                continue
            
            # 处理子文件夹名称
            for i, dir_name in enumerate(dirs):
                # 跳过排除的文件夹
                if any(keyword in dir_name for keyword in exclude_keywords):
                    continue
                    
                # 获取完整路径
                old_path = os.path.join(root, dir_name)
                
                # 如果不是一级目录，则应用格式化
                if root != artist_path:
                    new_name = format_folder_name(dir_name)
                    
                    # 检测目录名是否包含敏感词并转换
                    if convert_sensitive_enabled and check_sensitive_word(new_name):
                        logger.info(f"目录名含有敏感词，开始转换为拼音: {new_name}")
                        sensitive_words = get_sensitive_words_in_filename(new_name)
                        logger.info(f"检测到的敏感词: {', '.join(sensitive_words)}")
                        new_name = convert_sensitive_words_to_pinyin(new_name)
                        logger.info(f"转换后的目录名: {new_name}")
                    
                    if new_name != dir_name:
                        new_path = os.path.join(root, new_name)
                        try:
                            # 保存原始时间戳
                            dir_stat = os.stat(old_path)
                            # 重命名文件夹
                            os.rename(old_path, new_path)
                            # 恢复时间戳
                            os.utime(new_path, (dir_stat.st_atime, dir_stat.st_mtime))
                            # 更新 dirs 列表中的名称，确保 os.walk 继续正常工作
                            dirs[i] = new_name
                            logger.info(f"重命名文件夹: {old_path} -> {new_path}")
                        except Exception as e:
                            logger.error(f"重命名文件夹出错 {old_path}: {str(e)}")
                
            # 处理当前目录下的所有压缩文件
            pm = get_manager()
            if pm:
                pm.add_directory(root, os.path.dirname(root) if root != artist_path else None)

            modified_files_count = process_files_in_directory(root, artist_name, add_artist_name_enabled, convert_sensitive_enabled, threads=threads, track_ids=track_ids)
            total_modified_files_count += modified_files_count
    except Exception as e:
        logger.error(f"处理文件夹出错: {e}")

    return total_modified_files_count

def process_folders(base_path, add_artist_name_enabled=True, convert_sensitive_enabled=True, threads: int = 1, track_ids: bool = True):
    """
    处理基础路径下的所有画师文件夹。
    不使用多线程，逐个处理每个画师的文件。
    
    Args:
        base_path: 基础路径
        add_artist_name_enabled: 是否添加画师名
        convert_sensitive_enabled: 是否将敏感词转换为拼音
    """
    global _conflict_records
    # 开始处理前清空所有冲突记录
    with _conflict_lock:
        _conflict_records = []
    
    # 获取所有画师文件夹
    artist_folders = [
        folder for folder in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, folder))
    ]

    total_processed = 0
    total_modified = 0
    total_files = 0
    total_sensitive = 0

    # 逐个处理画师文件夹 (增加全局进度条)
    USE_TREE_UI = False  # 暂时关闭文件树显示
    pm = init_progress(enable=USE_TREE_UI)
    pm.start()
    try:
        with tqdm(total=len(artist_folders), desc="总体进度", unit="folder", position=0, leave=True, ncols=0, disable=USE_TREE_UI) as gbar:
            for folder in artist_folders:
                try:
                    artist_path = os.path.join(base_path, folder)
                    artist_name = get_artist_name(base_path, artist_path)
                    
                    # 注册画师目录
                    pm.add_directory(artist_path)

                    # 处理画师文件夹中的文件，并获取修改文件数量
                    modified_files_count = process_artist_folder(artist_path, artist_name, add_artist_name_enabled, convert_sensitive_enabled, threads=threads, track_ids=track_ids)
                    total_processed += 1
                    total_modified += modified_files_count
                    
                    # 统计该文件夹中的压缩文件总数
                    for root, _, files in os.walk(artist_path):
                        total_files += len([f for f in files if f.lower().endswith(ARCHIVE_EXTENSIONS)])
                    
                except Exception as e:
                    logger.error(f"处理文件夹 {folder} 出错: {e}")
                finally:
                    gbar.update(1)
    finally:
        pm.stop()
    
    # 输出冲突记录到 conflict.txt
    if _conflict_records:
        conflict_file_path = os.path.join(base_path, 'conflict.txt')
        try:
            with open(conflict_file_path, 'w', encoding='utf-8') as f:
                f.write(f"文件重命名冲突记录\n")
                f.write(f"生成时间: {_get_timestamp()}\n")
                f.write(f"总冲突数: {len(_conflict_records)}\n")
                f.write("=" * 80 + "\n\n")
                
                for i, conflict in enumerate(_conflict_records, 1):
                    f.write(f"冲突 #{i}\n")
                    f.write(f"源文件: {conflict['source']}\n")
                    f.write(f"目标文件: {conflict['target']}\n")
                    f.write(f"错误信息: {conflict['error']}\n")
                    f.write("-" * 80 + "\n")
            
            logger.warning(f"⚠️  发现 {len(_conflict_records)} 个文件重命名冲突，详情已保存到: {conflict_file_path}")
            print(f"\n⚠️  警告: 发现 {len(_conflict_records)} 个文件重命名冲突")
            print(f"   冲突详情已保存到: {conflict_file_path}")
        except Exception as e:
            logger.error(f"保存冲突记录失败: {e}")
            
    print(f"\n处理完成:")
    print(f"- 总共处理了 {total_processed} 个文件夹")
    print(f"- 扫描了 {total_files} 个压缩文件")
    if total_modified > 0:
        print(f"- 重命名了 {total_modified} 个文件")
    else:
        print(f"- ✨ 所有文件名都符合规范，没有文件需要重命名")

def _get_timestamp():
    """获取当前时间戳字符串"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def export_conflict_records(output_path: str = None) -> bool:
    """
    导出冲突记录到文件
    
    Args:
        output_path: 输出文件路径，如果为 None 则使用当前目录的 conflict.txt
        
    Returns:
        bool: 是否成功导出
    """
    global _conflict_records
    
    if not _conflict_records:
        logger.info("没有冲突记录需要导出")
        return False
    
    if output_path is None:
        output_path = os.path.join(os.getcwd(), 'conflict.txt')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"文件重命名冲突记录\n")
            f.write(f"生成时间: {_get_timestamp()}\n")
            f.write(f"总冲突数: {len(_conflict_records)}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, conflict in enumerate(_conflict_records, 1):
                f.write(f"冲突 #{i}\n")
                f.write(f"源文件: {conflict['source']}\n")
                f.write(f"目标文件: {conflict['target']}\n")
                f.write(f"错误信息: {conflict['error']}\n")
                f.write("-" * 80 + "\n")
        
        logger.info(f"✅ 冲突记录已导出到: {output_path}")
        return True
    except Exception as e:
        logger.error(f"导出冲突记录失败: {e}")
        return False

def get_conflict_count() -> int:
    """
    获取当前冲突记录数量
    
    Returns:
        int: 冲突数量
    """
    return len(_conflict_records)

def clear_conflict_records():
    """清空冲突记录"""
    global _conflict_records
    with _conflict_lock:
        _conflict_records = []
    logger.debug("冲突记录已清空")

def get_artist_name(target_directory, archive_path):
    """
    从压缩文件路径中提取艺术家名称。
    获取基于相对路径的第一部分作为艺术家名称。
    """
    try:
        # 获取相对路径的第一部分作为艺术家名称
        rel_path = os.path.relpath(archive_path, target_directory)
        artist_name = rel_path.split(os.sep)[0]
        
        # 如果是方括号包围的名称，直接返回
        if artist_name.startswith('[') and artist_name.endswith(']'):
            return artist_name
            
        # 如果不是方括号包围的，加上方括号
        return f"[{artist_name}]"
    except Exception as e:
        logger.error(f"提取艺术家名称时出错: {e}")
        return ""

def record_folder_timestamps(target_directory):
    """记录target_directory下所有文件夹的时间戳。"""
    folder_timestamps = {}
    for root, dirs, files in os.walk(target_directory):
        for dir in dirs:
            try:
                folder_path = os.path.join(root, dir)
                folder_stat = os.stat(folder_path)
                folder_timestamps[folder_path] = (folder_stat.st_atime, folder_stat.st_mtime)
            except FileNotFoundError:
                logger.warning(f"找不到文件夹: {folder_path}")
                continue
            except Exception as e:
                logger.error(f"处理文件夹时出错 {folder_path}: {str(e)}")
                continue
    
    return folder_timestamps

def restore_folder_timestamps(folder_timestamps):
    """恢复之前记录的文件夹时间戳。"""
    for folder_path, (atime, mtime) in folder_timestamps.items():
        try:
            if os.path.exists(folder_path):
                os.utime(folder_path, (atime, mtime))
        except Exception as e:
            logger.error(f"恢复文件夹时间戳时出错 {folder_path}: {str(e)}")
            continue
