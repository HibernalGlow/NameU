"""
文件名处理模块，提供文件名标准化、去重和格式化功能
"""

import os
import re
from loguru import logger
import pangu
from charset_normalizer import from_bytes
from .config import forbidden_artist_keywords
from .sensitive_word_processor import sensitive_processor
NAME_LEN = 80

_SAMENAME_PATTERN = re.compile(r'\[samename_\d+\]')
_TRAILING_COUNTER_PATTERN = re.compile(r'\s\(\d+\)$')
_BRACKET_CONTENT_PATTERN = re.compile(r'\[([^\[\]]+)\]')
_PAREN_CONTENT_PATTERN = re.compile(r'\(([^\(\)]+)\)')
_BASIC_REPLACEMENTS = [
    (re.compile(r'（'), '('),
    (re.compile(r'）'), ')'),
    (re.compile(r'\uff08'), '('),
    (re.compile(r'\uff09'), ')'),
    (re.compile(r'【'), '['),
    (re.compile(r'】'), ']'),
    (re.compile(r'［'), '['),
    (re.compile(r'］'), ']'),
    (re.compile(r'\uff3b'), '['),
    (re.compile(r'\uff3d'), ']'),
    (re.compile(r'｛'), '{'),
    (re.compile(r'｝'), '}'),
    (re.compile(r'〈'), '<'),
    (re.compile(r'〉'), '>'),
    (re.compile(r'\(\s*\)\s*'), ' '),
    (re.compile(r'\[\s*\]\s*'), ' '),
    (re.compile(r'\{\s*\}\s*'), ' '),
    (re.compile(r'\<\s*\>\s*'), ' '),
    (re.compile(r'\s{2,}'), ' '),
    (re.compile(r'【(?![々〇〈〉《》「」『』【】〔〕］［])([^【】]+)】'), r'[\1]'),
    (re.compile(r'（(?![々〇〈〉《》「」『』【】〔〕］［])([^（）]+)）'), r'(\1)'),
    (re.compile(r'【(.*?)】'), r'[\1]'),
    (re.compile(r'（(.*?)）'), r'(\1)'),
    (re.compile(r'［(.*?)］'), r'[\1]'),
    (re.compile(r'〈(.*?)〉'), r'<\1>'),
    (re.compile(r'｛(.*?)｝'), r'{\1}'),
    (re.compile(r'(单行本)'), ''),
    (re.compile(r'(同人志)'), ''),
    (re.compile(r'\{(.*?)\}'), ''),
    (re.compile(r'\{\d+w\}'), ''),
    (re.compile(r'\{\d+p\}'), ''),
    (re.compile(r'\{\d+px\}'), ''),
    (re.compile(r'\(\d+px\)'), ''),
    (re.compile(r'\{\d+de\}'), ''),
    (re.compile(r'\[cbr\]'), ''),
    (re.compile(r'\{\d+\.?\d*[kKwW]?@PX\}'), ''),
    (re.compile(r'\{\d+\.?\d*[kKwW]?@WD\}'), ''),
    (re.compile(r'\{\d+%?@DE\}'), ''),
    (re.compile(r'\[multi\]'), ''),
    (re.compile(r'\[trash\]'), ''),
    (re.compile(r'\[multi\-main\]'), ''),
    (_SAMENAME_PATTERN, ''),
    (_TRAILING_COUNTER_PATTERN, ''),
]
_ADVANCED_REPLACEMENTS = [
    (re.compile(r'Digital'), 'DL'),
    (re.compile(r'\[(\d{4})\.(\d{2})\]'), r'(\1.\2)'),
    (re.compile(r'\((\d{4})年(\d{1,2})月\)'), r'(\1.\2)'),
    (re.compile(r'Fate.*Grand.*Order'), 'FGO'),
    (re.compile(r'艦隊これくしょん.*-.*艦これ.*-'), '舰C'),
    (re.compile(r'PIXIV FANBOX'), 'FANBOX'),
    (re.compile(r'\((MJK[^\)]+)\)'), ''),
    (re.compile(r'^\) '), ''),
    (re.compile(r'ibm5100'), ''),
    (re.compile(r'20(\d+)年(\d+)月号'), r'\1-\2'),
    (re.compile(r'(单行本)'), ''),
    (re.compile(r'^／\s{1,6}'), ''),
]
_PREFIX_PRIORITY_PATTERNS = [
    re.compile(r'(\d{4}\.\d{2})'),
    re.compile(r'(\d{4}年\d{1,2}月)'),
    re.compile(r'(\d{2}\.\d{2})'),
    re.compile(r'(?<!\d)(\d{4})(?!\d)'),
    re.compile(r'(\d{2}\-\d{2})'),
    re.compile(r'(C\d+)'),
    re.compile(r'(COMIC1☆\d+)'),
    re.compile(r'(例大祭\d*)'),
    re.compile(r'(FF\d+)'),
    re.compile(r'([^()]*)COMIC[^()]*'),
    re.compile(r'([^()]*)快楽天[^()]*'),
    re.compile(r'([^()]*)Comic[^()]*'),
    re.compile(r'([^()]*)VOL[^()]*'),
    re.compile(r'([^()]*)永遠娘[^()]*'),
    re.compile(r'・'),
    re.compile(r'(.*?\d+.*?)'),
]
_SUFFIX_KEYWORD_PATTERNS = [
    re.compile(r'漢化'),
    re.compile(r'汉化'),
    re.compile(r'翻訳'),
    re.compile(r'无修'),
    re.compile(r'無修'),
    re.compile(r'DL版'),
    re.compile(r'掃圖'),
    re.compile(r'翻譯'),
    re.compile(r'Digital'),
    re.compile(r'製作'),
    re.compile(r'重嵌'),
    re.compile(r'CG集'),
    re.compile(r'掃'),
    re.compile(r'制作'),
    re.compile(r'排序 '),
    re.compile(r'截止'),
    re.compile(r'去码'),
    re.compile(r'^\s*[\d\.\-+\s]*\d+[\d\.\-+\s]*[pPvVmMbBgGnN][\s\d\.\-+\s pPvVmMbBgGnN]*$'),
    re.compile(r'\d+[GMK]B'),
]

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
    # 移除[samename_n]标记 (旧格式)
    base = _SAMENAME_PATTERN.sub('', base)
    # 移除 (n) 后缀 (新格式，仅匹配文件名末尾的数字括号)
    base = _TRAILING_COUNTER_PATTERN.sub('', base)
    # 移除所有空格并转换为小写
    normalized = ''.join(base.split()).lower()
    return normalized

def get_unique_filename_with_samename(directory: str, filename: str, original_path: str = None, existing_names: set = None, normalized_cache: dict = None) -> str:
    """
    检查文件名是否存在，如果存在则添加[samename_n]后缀
    Args:
        directory: 文件所在目录
        filename: 完整文件名（包含扩展名）
        original_path: 原始文件的完整路径，用于排除自身
        existing_names: 可选，目录下所有文件名的集合（用于加速）
        normalized_cache: 可选，标准化文件名到实际文件名的映射（用于加速）
    Returns:
        str: 唯一的文件名
    """
    base, ext = os.path.splitext(filename)
    # 对文件名进行pangu格式化
    base = pangu.spacing_text(base)
    new_filename = f"{base}{ext}"
    
    # 获取目录下文件名信息
    if existing_names is None:
        # 兼容模式：如果没有传入缓存，则现场查询磁盘
        new_path = os.path.join(directory, new_filename)
        # 如果文件不存在，直接返回
        if not os.path.exists(new_path):
            logger.debug(f"文件不存在，使用原始文件名: {new_filename}")
            return new_filename
        
        # 如果是同一个文件，直接返回
        if original_path and os.path.exists(new_path) and os.path.samefile(new_path, original_path):
            logger.debug(f"文件是自身，保留原始文件名: {new_filename}")
            return new_filename
        
        # 获取目录下所有项并检查是否真的重名
        existing_files = [f for f in os.listdir(directory)]
    else:
        # 加速模式：使用传入的文件名集合
        if new_filename not in existing_names:
            logger.debug(f"缓存检查：文件名不存在，使用: {new_filename}")
            return new_filename
            
        # 检查是否是自身 (Win: 路径比较)
        if original_path:
            orig_name = os.path.basename(original_path)
            if orig_name == new_filename:
                logger.debug(f"缓存检查：文件是自身，保留: {new_filename}")
                return new_filename
        
        existing_files = existing_names

    # 标准化当前文件名用于比较
    normalized_current = normalize_filename(new_filename)
    
    is_duplicate = False
    
    # 检查标准化名称冲突
    if normalized_cache is not None:
        # 加速模式：从字典查询
        if normalized_current in normalized_cache:
            # 确认冲突名不是自身
            conflict_names = normalized_cache[normalized_current]
            if isinstance(conflict_names, list):
                for c_name in conflict_names:
                    if original_path and c_name == os.path.basename(original_path):
                        continue
                    is_duplicate = True
                    break
            else:
                if not (original_path and conflict_names == os.path.basename(original_path)):
                    is_duplicate = True
    else:
        # 兼容模式：遍历所有文件
        for existing_file in existing_files:
            if original_path and existing_file == os.path.basename(original_path):
                continue
            
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
        # 使用系统自带样式的重名机制: "文件名 (1).ext"
        current_filename = f"{base} ({counter}){ext}"
        # 检查编号后的名字在磁盘/缓存中是否存在
        if existing_names is not None:
            if current_filename not in existing_names:
                logger.debug(f"检测到文件名重复，生成新文件名: {current_filename}")
                return current_filename
        else:
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
    # 先进行基本的替换规则
    patterns_and_replacements = [
        (r'\[\#s\]', '#'),
        (r'（', '('),
        (r'）', ')'),
        (r'【', '['),
        (r'】', ']'),
        (r'［', '['),
        (r'］', ']'),
        (r'｛', '{'),
        (r'｝', '}'),
        (r'｜', '|'),
        (r'～', '~'),
    ]
    
    formatted_name = folder_name
    for pattern, replacement in patterns_and_replacements:
        formatted_name = re.sub(pattern, replacement, formatted_name)
    
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

def truncate_filename_smart(filename, max_length):
    """
    智能截断文件名，保持末尾符号完整性
    
    Args:
        filename: 待截断的文件名（不含扩展名）
        max_length: 最大长度
        
    Returns:
        str: 截断后的文件名
    """
    if len(filename) <= max_length:
        return filename
    
    # 定义需要配对的符号
    bracket_pairs = {
        '(': ')',
        '[': ']',
        '{': '}',
        '<': '>',
        '（': '）',
        '【': '】',
        '［': '］',
        '｛': '｝',
        '〈': '〉'
    }
    
    # 反向映射
    closing_to_opening = {v: k for k, v in bracket_pairs.items()}
    all_brackets = set(bracket_pairs.keys()) | set(bracket_pairs.values())
    
    # 先截断到最大长度
    truncated = filename[:max_length]
    
    # 从截断位置开始向前检查，找到最后一个完整的符号对位置
    best_pos = max_length
    stack = []
    
    # 从后向前扫描，找到合适的截断点
    for i in range(len(truncated) - 1, -1, -1):
        char = truncated[i]
        
        # 如果是右括号，入栈
        if char in closing_to_opening:
            stack.append(char)
        # 如果是左括号
        elif char in bracket_pairs:
            # 检查是否有匹配的右括号
            if stack and stack[-1] == bracket_pairs[char]:
                stack.pop()
            else:
                # 找到不匹配的左括号，说明这里有未闭合的括号
                # 截断点应该在这个左括号之前
                best_pos = i
                break
    
    # 如果栈不为空，说明有未闭合的右括号，需要继续向前找
    if stack:
        # 从best_pos继续向前找，删除所有不完整的括号内容
        temp_result = truncated[:best_pos].rstrip()
        
        # 再次检查是否还有不完整的括号
        while temp_result:
            # 检查最后一个字符是否是左括号
            if temp_result[-1] in bracket_pairs:
                # 向前找到对应的开始位置
                bracket_start = len(temp_result) - 1
                # 删除这个不完整的括号及其内容
                temp_result = temp_result[:bracket_start].rstrip()
            else:
                break
        
        return temp_result.strip()
    
    # 如果没有不完整的括号，在最后一个完整单词或符号处截断
    result = truncated[:best_pos].rstrip()
    
    # 如果最后是空格，去除
    result = result.rstrip()
    
    # 再次检查末尾，如果有不完整的括号内容，继续清理
    # 例如: "xxx [yyy" -> "xxx"
    while result:
        last_char = result[-1]
        if last_char in bracket_pairs:
            # 找到左括号，但没有对应的右括号，删除它
            result = result[:-1].rstrip()
        else:
            break
    
    return result.strip()

def get_unique_filename(directory, filename, artist_name, is_excluded=False, existing_names=None, normalized_cache=None):
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
        return get_unique_filename_with_samename(directory, filename, existing_names=existing_names, normalized_cache=normalized_cache)

    # 应用基本替换规则
    for pattern, replacement in _BASIC_REPLACEMENTS:
        base = pattern.sub(replacement, base)

    # 对非排除文件夹应用高级替换规则
    for pattern, replacement in _ADVANCED_REPLACEMENTS:
        base = pattern.sub(replacement, base)

    # 以下是非排除文件夹的处理逻辑
    # 提取方括号和圆括号中的内容
    group1 = _BRACKET_CONTENT_PATTERN.findall(base)
    group3 = _BRACKET_CONTENT_PATTERN.sub('', base)
    group2 = _PAREN_CONTENT_PATTERN.findall(group3)
    group3 = _PAREN_CONTENT_PATTERN.sub('', group3).strip()
    
    # 将 group1 和 group2 组合为一个完整的列表
    all_groups = group1 + group2
    
    # 分离出 prefix 和 suffix 部分
    prefix_elements = []
    suffix_elements = []
    middle_elements = []

    # 收集所有元素及其优先级
    suffix_candidates = []
    prefix_candidates = []
    artist_elements = []
    remaining_elements = all_groups.copy()  # 创建待处理元素的副本
    
    # 先处理画师名
    for element in all_groups:
        if has_artist_name(element, artist_name):
            artist_elements.append(element)
            remaining_elements.remove(element)
    
    # 处理后缀
    for element in remaining_elements[:]:  # 使用切片创建副本进行迭代
        if any(pattern.search(element) for pattern in _SUFFIX_KEYWORD_PATTERNS):
            for i, pattern in enumerate(_PREFIX_PRIORITY_PATTERNS):
                if pattern.search(element):
                    suffix_candidates.append((element, i))
                    remaining_elements.remove(element)
                    break
            else:
                suffix_candidates.append((element, len(_PREFIX_PRIORITY_PATTERNS)))
                remaining_elements.remove(element)
    
    # 处理前缀
    for element in remaining_elements[:]:
        matched = False
        # 检查是否同时包含日期和C编号
        c_match = re.search(r'C(\d+)', element)
        date_match = re.search(r'(\d{4})\.(\d{2})', element)
        
        if c_match and date_match:
            # 如果同时包含，分别处理
            c_num = c_match.group(0)
            date = f"({date_match.group(1)}.{date_match.group(2)})"
            prefix_candidates.append((f"({c_num})", 0))  # C编号优先级最高
            prefix_candidates.append((date, 4))  # 日期次之
            remaining_elements.remove(element)
            matched = True
        else:
            # 如果不是同时包含，按原有逻辑处理
            for i, pattern in enumerate(_PREFIX_PRIORITY_PATTERNS):
                if pattern.search(element):
                    prefix_candidates.append((element, i))
                    remaining_elements.remove(element)
                    matched = True
                    break
        
        if not matched:
            middle_elements.append(f"[{element}]")
    
    # 按优先级排序并添加到前缀列表
    prefix_candidates.sort(key=lambda x: x[1])
    for element, priority in prefix_candidates:
        if f"({element})" not in prefix_elements:
            prefix_elements.append(f"({element})")
    
    # 按优先级排序并添加到后缀列表
    suffix_candidates.sort(key=lambda x: x[1])
    for element, priority in suffix_candidates:
        if f"[{element}]" not in suffix_elements:
            suffix_elements.append(f"[{element}]")
    
    # 最后添加画师元素（只在不包含禁止关键词时添加）
    if not has_forbidden_keyword(base):
        for element in artist_elements:
            if f"[{element}]" not in suffix_elements:
                suffix_elements.append(f"[{element}]")
    
    # 拼接新的文件名，prefix 在前，group3 在中间，suffix 在后
    prefix_part = f"{' '.join(prefix_elements)} " if prefix_elements else ""
    middle_part = f"{group3} {' '.join(middle_elements)}".strip()
    suffix_part = f" {' '.join(suffix_elements)}" if suffix_elements else ""
    
    new_base = f"{prefix_part}{middle_part}{suffix_part}".strip()
    
    # 最后再次清理可能残留的空括号和空方框
    new_base = re.sub(r'\(\s*\)\s*', ' ', new_base)  # 清理空括号
    new_base = re.sub(r'\[\s*\]\s*', ' ', new_base)  # 清理空方框
    new_base = re.sub(r'\s{2,}', ' ', new_base)  # 清理多余空格
    new_base = new_base.strip()
    
    # 限制文件名长度为NAME_LEN个字符（不包括扩展名）
    max_length = NAME_LEN - len(ext)
    if len(new_base) > max_length:
        logger.warning(f"文件名过长，将被截断: {new_base}")
        new_base = truncate_filename_smart(new_base, max_length)
        logger.info(f"截断后的文件名: {new_base}")
    
    # 检查文件是否存在，如果存在则添加[samename_n]后缀
    filename = f"{new_base}{ext}"
    return get_unique_filename_with_samename(directory, filename, existing_names=existing_names, normalized_cache=normalized_cache)

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


def get_unique_filename_with_pinyin_conversion(directory, filename, style='default', existing_names=None, normalized_cache=None):
    """
    将文件名中的敏感词转换为拼音并确保文件名唯一
    
    Args:
        directory: 文件所在目录
        filename: 原始文件名
        style: 拼音风格
        existing_names: 缓存的文件名集合
        normalized_cache: 缓存的标准化文件名映射
        
    Returns:
        str: 唯一的、已处理敏感词的文件名
    """
    # 转换敏感词为拼音
    converted_filename = convert_sensitive_words_to_pinyin(filename, style)
    
    # 确保文件名唯一
    return get_unique_filename_with_samename(directory, converted_filename, existing_names=existing_names, normalized_cache=normalized_cache)
