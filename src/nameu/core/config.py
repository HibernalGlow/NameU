# src/nameu/core/config.py

# 纯 Python 结构的正则分组和类型映射

import os
import toml
from loguru import logger

# 默认配置
exclude_keywords = ['[00待分类]', '[00去图]', '[01杂]']
forbidden_artist_keywords = ['[圣枪嘉然]', '[00去图]', '[01杂]', '[bili]','[weibo]', '[02杂]']
path_blacklist = []

def load_config():
    """从主目录下的 nameu.toml 加载配置"""
    global exclude_keywords, forbidden_artist_keywords, path_blacklist
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "nameu.toml")
    if os.path.exists(config_path):
        try:
            config = toml.load(config_path)
            
            # 加载排除关键词
            if "exclude_keywords" in config:
                exclude_keywords = config["exclude_keywords"]
                logger.info(f"从 TOML 加载排除关键词: {exclude_keywords}")
                
            # 加载禁止画师关键词
            if "forbidden_artist_keywords" in config:
                forbidden_artist_keywords = config["forbidden_artist_keywords"]
                logger.info(f"从 TOML 加载禁止画师关键词: {forbidden_artist_keywords}")
                
            # 加载路径黑名单
            if "path_blacklist" in config:
                path_blacklist = config["path_blacklist"]
                logger.info(f"从 TOML 加载路径黑名单: {path_blacklist}")
                
        except Exception as e:
            logger.error(f"加载 TOML 配置失败: {e}")

# 执行初始化加载
load_config()

def is_path_blacklisted(path: str) -> bool:
    """检查路径是否在黑名单中"""
    if not path_blacklist:
        return False
    
    # 转换为绝对路径进行比较
    abs_path = os.path.abspath(path)
    for blacklisted_path in path_blacklist:
        abs_blacklisted = os.path.abspath(blacklisted_path)
        if abs_path == abs_blacklisted or abs_path.startswith(os.path.join(abs_blacklisted, '')):
            return True
    return False

basic_patterns = {
    "all": [
        (r'\s{0,6}／\s{0,6}', ' '),
        (r'（', '('),
        (r'）', ')'),
        (r'\uff08', '('),
        (r'\uff09', ')'),
        (r'【', '['),
        (r'】', ']'),
        (r'［', '['),
        (r'］', ']'),
        (r'\uff3b', '['),
        (r'\uff3d', ']'),
        (r'｛', '{'),
        (r'｝', '}'),
        (r'〈', '<'),
        (r'〉', '>'),
        (r'\(\s*\)\s*', ' '),
        (r'\[\s*\]\s*', ' '),
        (r'\{\s*\}\s*', ' '),
        (r'\<\s*\>\s*', ' '),
        (r'\s{2,}', ' '),
        (r'【(?![々〇〈〉《》「」『』【】〔〕］［])([^【】]+)】', r'[\1]'),
        (r'（(?![々〇〈〉《》「」『』【】〔〕］［])([^（）]+)）', r'(\1)'),
        (r'【(.*?)】', r'[\1]'),
        (r'（(.*?)）', r'(\1)'),
        (r'［(.*?)］', r'[\1]'),
        (r'〈(.*?)〉', r'<\1>'),
        (r'｛(.*?)｝', r'{\1}'),
        (r'\{(.*?)\}', ''),
        (r'\{\d+w\}', ''),
        (r'\{\d+p\}', ''),
        (r'\{\d+px\}', ''),
        (r'\(\d+px\)', ''),
        (r'\{\d+de\}', ''),
        (r'\[cbr\]', ''),
        (r'\{\d+\.?\d*[kKwW]?@PX\}', ''),
        (r'\{\d+\.?\d*[kKwW]?@WD\}', ''),
        (r'\{\d+%?@DE\}', ''),
        (r'\[multi\]', ''),
        (r'\[trash\]', ''),
        (r'\[multi\-main\]', ''),
        (r'\[samename_\d+\]', '')
    ],
    "image": [
        (r'(单行本)', ''),
        (r'(同人志)', '')
    ],
    "archive": [
        (r'(单行本)', ''),
        (r'(同人志)', '')
    ],
    "video": [
        (r'\[#hb\]', '')
    ]
}

advanced_patterns = {
    "all": [
        (r'Digital', 'DL'),
        (r'\[(\d{4})\.(\d{2})\]', r'(\1.\2)'),
        (r'\((\d{4})年(\d{1,2})月\)', r'(\1.\2)'),
        (r'Fate.*Grand.*Order', 'FGO'),
        (r'艦隊これくしょん.*-.*艦これ.*-', '舰C'),
        (r'PIXIV FANBOX', 'FANBOX'),
        (r'\((MJK[^\)]+)\)', ''),
        (r'^\) ', ''),
        (r'ibm5100', ''),
        (r'20(\d+)年(\d+)月号', r'\1-\2'),
        # (r'^／\s{1,6}', ''),
        
    ],
    "archive": [
        (r'(单行本)', '')
    ]
}

prefix_priority = {
    "all": [
        r'(\d{4}\.\d{2})',
        r'(\d{4}年\d{1,2}月)',
        r'(\d{2}\.\d{2})',
        r'(?<!\d)(\d{4})(?!\d)',
        r'(\d{2}\-\d{2})',
        r'(C\d+)',
        r'(COMIC1☆\d+)',
        r'(例大祭\d*)',
        r'(FF\d+)',
        r'([^()]*)COMIC[^()]*',
        r'([^()]*)快楽天[^()]*',
        r'([^()]*)Comic[^()]*',
        r'([^()]*)VOL[^()]*',
        r'([^()]*)永遠娘[^()]*',
        r'(.*?\d+.*?)'
    ]
}

suffix_keywords = {
    "all": [
        r'漢化', r'汉化', r'翻訳', r'无修', r'無修', r'DL版', r'掃圖', r'翻譯', r'Digital',
        r'製作', r'重嵌', r'CG集', r'掃', r'制作', r'排序 ', r'截止', r'去码', r'\d+[GMK]B'
    ],
    "archive": [
        r'(单行本)'
    ]
}

def get_patterns(group: str, file_type: str = 'all'):
    patterns_dict = globals().get(group, {})
    if file_type in patterns_dict:
        patterns = patterns_dict[file_type]
    else:
        patterns = patterns_dict.get('all', [])
    is_pair = bool(patterns and isinstance(patterns[0], tuple) and len(patterns[0]) == 2)
    return patterns, is_pair 