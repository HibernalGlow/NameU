# src/nameu/core/config.py

# 纯 Python 结构的正则分组和类型映射

basic_patterns = {
    "all": [
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
        (r'^／\s{1,6}', '')
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