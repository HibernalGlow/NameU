"""
文件名处理模块，提供文件名标准化、去重和格式化功能
"""

import os
import re
from loguru import logger
import pangu
from charset_normalizer import from_bytes
from .constants import forbidden_artist_keywords
from .sensitive_word_processor import sensitive_processor
from .pattern_config import get_patterns
from nameu.type.file_type_detector import get_file_type
NAME_LEN = 80
#         

def detect_and_decode_filename(filename):
    """
    解码文件名，处理特殊字符，统一转换为 UTF-8 编码。
    """
    try:
        # 如果已经是有效的UTF-8字符串，直接返回
        if isinstance(filename, str):
            return filename
            
        # 如果是bytes，尝试解码
        if isinstance(filename, bytes):
            try:
                return filename.decode('utf-8')
            except UnicodeDecodeError:
                pass
            
            # 尝试其他编码
            encodings = ['utf-8', 'gbk', 'shift-jis', 'euc-jp', 'cp932']
            for encoding in encodings:
                try:
                    return filename.decode(encoding)
                except UnicodeDecodeError:
                    continue
                    
            # 如果所有编码都失败，使用 charset_normalizer
            result = from_bytes(filename).best()
            if result:
                return str(result)
                
        return filename
    except Exception as e:
        logger.error(f"解码文件名出错: {filename}")
        return filename

def has_forbidden_keyword(filename):
    """检查文件名是否包含禁止画师名的关键词"""
    return any(keyword in filename for keyword in forbidden_artist_keywords)

def normalize_filename(filename):
    """
    标准化文件名以进行比较
    1. 移除所有空格
    2. 转换为小写
    3. 移除[samename_n]标记
    4. 移除扩展名
    """
    # 移除扩展名
    base = os.path.splitext(filename)[0]
    # 移除[samename_n]标记
    base = re.sub(r'\[samename_\d+\]', '', base)
    # 移除所有空格并转换为小写
    normalized = ''.join(base.split()).lower()
    return normalized

def get_unique_filename_with_samename(directory: str, filename: str, original_path: str = None) -> str:
    """
    检查文件名是否存在，如果存在则添加[samename_n]后缀
    Args:
        directory: 文件所在目录
        filename: 完整文件名（包含扩展名）
        original_path: 原始文件的完整路径，用于排除自身
    Returns:
        str: 唯一的文件名
    """
    base, ext = os.path.splitext(filename)
    # 对文件名进行pangu格式化
    base = pangu.spacing_text(base)
    new_filename = f"{base}{ext}"
    new_path = os.path.join(directory, new_filename)
    
    # 如果文件不存在，直接返回
    if not os.path.exists(new_path):
        logger.debug(f"文件不存在，使用原始文件名: {new_filename}")
        return new_filename
    
    # 如果是同一个文件，直接返回
    if original_path and os.path.samefile(new_path, original_path):
        logger.debug(f"文件是自身，保留原始文件名: {new_filename}")
        return new_filename
    
    # 标准化当前文件名用于比较
    normalized_current = normalize_filename(new_filename)
    
    # 获取目录下所有文件并检查是否真的重名
    existing_files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    is_duplicate = False
    
    for existing_file in existing_files:
        if existing_file == new_filename:
            continue  # 跳过自身
        
        normalized_existing = normalize_filename(existing_file)
        if normalized_existing == normalized_current:
            is_duplicate = True
            break
    
    # 如果不是真正的重名，直接返回原文件名
    if not is_duplicate:
        return new_filename
    
    # 如果确实重名，添加编号
    counter = 1
    while True:
        current_filename = f"{base}[samename_{counter}]{ext}"
        current_path = os.path.join(directory, current_filename)
        if not os.path.exists(current_path):
            logger.debug(f"检测到文件名重复，生成新文件名: {current_filename}")
            return current_filename
        counter += 1

def remove_duplicate_brackets(text):
    """删除重复的方括号内容"""
    # 使用正则表达式查找所有方括号内容
    bracket_contents = re.findall(r'\[([^\[\]]+)\]', text)
    
    # 如果没有方括号内容，直接返回原文本
    if not bracket_contents:
        return text
    
    # 记录已处理的方括号内容（忽略空格）
    seen_contents = set()
    result = text
    
    # 查找并替换重复的方括号内容
    for content in bracket_contents:
        bracket = f'[{content}]'
        # 计算该内容在文本中出现的次数
        count = result.count(bracket)
        
        # 为了比较时忽略空格，创建一个无空格版本
        content_no_space = ''.join(content.split())
        
        # 如果超过一次或已经处理过（忽略空格），则删除多余的
        if count > 1 or content_no_space in seen_contents:
            # 保留第一次出现，删除其余的
            first_pos = result.find(bracket)
            remaining = result[first_pos + len(bracket):]
            result = result[:first_pos + len(bracket)] + remaining.replace(bracket, '')
        
        # 标记为已处理（保存无空格版本）
        seen_contents.add(content_no_space)
    
    return result

def has_artist_name(filename, artist_name):
    """检查文件名是否包含画师名"""
    artist_name_lower = artist_name.lower()
    filename_lower = filename.lower()
    processed_artist_name = pangu.spacing_text(artist_name_lower)
    keywords = re.split(r'[\[\]\(\)\s]+', processed_artist_name)
    keywords = [keyword for keyword in keywords if keyword]
    return any(keyword in filename_lower for keyword in set(keywords))

def append_artist_name(filename, artist_name):
    """将画师名追加到文件名末尾"""
    base, ext = os.path.splitext(filename)
    return f"{base}{artist_name}{ext}"

def format_folder_name(folder_name):
    """格式化文件夹名称"""
    # 获取文件夹类型（可用'folder'，如需更细分可自定义）
    file_type = 'folder'
    # 动态获取 basic_patterns
    basic_patterns, is_pair = get_patterns('basic_patterns', file_type)
    formatted_name = folder_name
    if is_pair:
        for pattern, replacement in basic_patterns:
            formatted_name = re.sub(pattern, replacement, formatted_name)
    else:
        for pattern in basic_patterns:
            formatted_name = re.sub(pattern, '', formatted_name)
    # 删除重复的方括号内容
    formatted_name = remove_duplicate_brackets(formatted_name)
    # 然后使用 pangu 处理文字和数字之间的空格
    try:
        formatted_name = pangu.spacing_text(formatted_name)
    except Exception as e:
        logger.warning(f"pangu 格式化失败，跳过空格处理: {str(e)}")
    # 最后处理多余的空格
    formatted_name = re.sub(r'\s{2,}', ' ', formatted_name)
    return formatted_name.strip()

def get_unique_filename(directory, filename, artist_name, is_excluded=False):
    """生成唯一文件名"""
    base, ext = os.path.splitext(filename)
    
    # 预处理：清理所有花括号内容
    base = re.sub(r'\{[^}]*\}', '', base)
    
    # 删除重复的方括号内容
    base = remove_duplicate_brackets(base)
    
    # 如果包含禁止关键词，删除画师名
    if has_forbidden_keyword(base):
        base = base.replace(artist_name, '')
    # 如果不包含禁止关键词，且存在画师名，则删除以便后续统一处理
    elif artist_name in base:
        base = base.replace(artist_name, '')

    # 使用 pangu 处理文字和数字之间的空格
    base = pangu.spacing_text(base)

    # 如果是排除的文件夹，直接返回处理后的文件名
    if is_excluded:
        filename = f"{base}{ext}"
        return get_unique_filename_with_samename(directory, filename)

    # 动态获取文件类型
    file_type = get_file_type(filename)
    # 应用 basic_patterns
    basic_patterns, is_pair = get_patterns('basic_patterns', file_type)
    if is_pair:
        for pattern, replacement in basic_patterns:
            base = re.sub(pattern, replacement, base)
    else:
        for pattern in basic_patterns:
            base = re.sub(pattern, '', base)
    # 应用 advanced_patterns
    advanced_patterns, is_pair = get_patterns('advanced_patterns', file_type)
    if is_pair:
        for pattern, replacement in advanced_patterns:
            base = re.sub(pattern, replacement, base)
    else:
        for pattern in advanced_patterns:
            base = re.sub(pattern, '', base)
    # prefix_priority
    prefix_priority, _ = get_patterns('prefix_priority', file_type)
    # suffix_keywords
    suffix_keywords, _ = get_patterns('suffix_keywords', file_type)
    # 以下原有 prefix/suffix 处理逻辑保持不变
    pattern_brackets = re.compile(r'\[([^\[\]]+)\]')
    pattern_parentheses = re.compile(r'\(([^\(\)]+)\)')
    group1 = pattern_brackets.findall(base)
    group3 = pattern_brackets.sub('', base)
    group2 = pattern_parentheses.findall(group3)
    group3 = pattern_parentheses.sub('', group3).strip()
    all_groups = group1 + group2
    prefix_elements = []
    suffix_elements = []
    middle_elements = []
    suffix_candidates = []
    prefix_candidates = []
    artist_elements = []
    remaining_elements = all_groups.copy()
    for element in all_groups:
        if has_artist_name(element, artist_name):
            artist_elements.append(element)
            remaining_elements.remove(element)
    for element in remaining_elements[:]:
        if any(re.search(kw, element) for kw in suffix_keywords):
            for i, pattern in enumerate(prefix_priority):
                if re.search(pattern, element):
                    suffix_candidates.append((element, i))
                    remaining_elements.remove(element)
                    break
            else:
                suffix_candidates.append((element, len(prefix_priority)))
                remaining_elements.remove(element)
    for element in remaining_elements[:]:
        matched = False
        c_match = re.search(r'C(\d+)', element)
        date_match = re.search(r'(\d{4})\.(\d{2})', element)
        if c_match and date_match:
            c_num = c_match.group(0)
            date = f"({date_match.group(1)}.{date_match.group(2)})"
            prefix_candidates.append((f"({c_num})", 0))
            prefix_candidates.append((date, 4))
            remaining_elements.remove(element)
            matched = True
        else:
            for i, pattern in enumerate(prefix_priority):
                if re.search(pattern, element):
                    prefix_candidates.append((element, i))
                    remaining_elements.remove(element)
                    matched = True
                    break
        if not matched:
            middle_elements.append(f"[{element}]")
    prefix_candidates.sort(key=lambda x: x[1])
    for element, priority in prefix_candidates:
        if f"({element})" not in prefix_elements:
            prefix_elements.append(f"({element})")
    suffix_candidates.sort(key=lambda x: x[1])
    for element, priority in suffix_candidates:
        if f"[{element}]" not in suffix_elements:
            suffix_elements.append(f"[{element}]")
    if not has_forbidden_keyword(base):
        for element in artist_elements:
            if f"[{element}]" not in suffix_elements:
                suffix_elements.append(f"[{element}]")
    prefix_part = f"{' '.join(prefix_elements)} " if prefix_elements else ""
    middle_part = f"{group3} {' '.join(middle_elements)}".strip()
    suffix_part = f" {' '.join(suffix_elements)}" if suffix_elements else ""
    new_base = f"{prefix_part}{middle_part}{suffix_part}".strip()
    new_base = re.sub(r'\(\s*\)\s*', ' ', new_base)
    new_base = re.sub(r'\[\s*\]\s*', ' ', new_base)
    new_base = re.sub(r'\s{2,}', ' ', new_base)
    new_base = new_base.strip()
    max_length = NAME_LEN - len(ext)
    if len(new_base) > max_length:
        logger.warning(f"文件名过长，将被截断: {new_base}")
        new_base = new_base[:max_length]
        logger.info(f"截断后的文件名: {new_base}")
    filename = f"{new_base}{ext}"
    return get_unique_filename_with_samename(directory, filename)

def check_sensitive_word(filename):
    """
    检查文件名中是否包含敏感词
    
    Args:
        filename: 待检查的文件名
        
    Returns:
        bool: 如果包含敏感词返回True，否则返回False
    """
    return sensitive_processor.is_sensitive(filename)


def get_sensitive_words_in_filename(filename):
    """
    获取文件名中包含的敏感词列表
    
    Args:
        filename: 待检查的文件名
        
    Returns:
        List[str]: 文件名中包含的敏感词列表
    """
    return sensitive_processor.get_matching_sensitive_words(filename)


def convert_sensitive_words_to_pinyin(filename, style='default'):
    """
    将文件名中的敏感词转换为拼音
    
    Args:
        filename: 待处理的文件名
        style: 拼音风格，可选值：
              'default': 普通风格，不带声调
              'tone': 带声调
              'first_letter': 首字母
              'initials': 声母
              'finals': 韵母
              
    Returns:
        str: 处理后的文件名，敏感词已转换为拼音
    """
    if not sensitive_processor.is_sensitive(filename):
        return filename
    
    # 处理文件名
    base, ext = os.path.splitext(filename)
    
    # 获取所有敏感词
    sensitive_words = sensitive_processor.get_matching_sensitive_words(base)
      # 逐个替换敏感词为拼音
    converted_base = base
    for word in sensitive_words:
        pinyin = sensitive_processor.convert_to_pinyin(word, style)
        logger.debug(f"将敏感词 '{word}' 转换为拼音 '{pinyin}'")
        converted_base = converted_base.replace(word, pinyin)
    
    logger.debug(f"敏感词转换结果: '{base}' -> '{converted_base}'")
    return f"{converted_base}{ext}"


def get_unique_filename_with_pinyin_conversion(directory, filename, style='default'):
    """
    将文件名中的敏感词转换为拼音并确保文件名唯一
    
    Args:
        directory: 文件所在目录
        filename: 原始文件名
        style: 拼音风格
        
    Returns:
        str: 唯一的、已处理敏感词的文件名
    """
    # 转换敏感词为拼音
    converted_filename = convert_sensitive_words_to_pinyin(filename, style)
    
    # 确保文件名唯一
    return get_unique_filename_with_samename(directory, converted_filename)
