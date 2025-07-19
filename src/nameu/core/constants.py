"""
Constants used across the comic file processing modules
定义漫画文件处理模块中使用的常量
"""

# 支持的压缩文件扩展名
ARCHIVE_EXTENSIONS = ('.zip', '.rar', '.7z', '.cbz', '.cbr')

# 排除关键词配置
exclude_keywords = ['[00待分类]', '[00去图]', '[01杂]', '[02COS]']

# 禁止添加画师名的关键词，如果文件名中包含这些关键词，也会删除已有的画师名
forbidden_artist_keywords = ['[02COS]']
