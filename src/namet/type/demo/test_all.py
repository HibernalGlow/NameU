import os
import shutil
from nameu.type.filter_manager import FilterManager
from nameu.core.filename_processor import get_unique_filename, format_folder_name

def setup_demo_dir(base):
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    os.makedirs(os.path.join(base, "subfolder"))
    with open(os.path.join(base, "a.jpg"), "w") as f:
        f.write("img")
    with open(os.path.join(base, "b.txt"), "w") as f:
        f.write("txt")
    with open(os.path.join(base, "[#hb]c.mp4"), "w") as f:
        f.write("video")
    with open(os.path.join(base, "[#hb]d.mp4.nov"), "w") as f:
        f.write("video2")
    with open(os.path.join(base, "subfolder", "e.flv"), "w") as f:
        f.write("video3")
    os.makedirs(os.path.join(base, "folder#hb"))
    with open(os.path.join(base, "folder#hb", "f.mp4"), "w") as f:
        f.write("video4")

def list_all_paths(base):
    result = []
    for root, dirs, files in os.walk(base):
        for d in dirs:
            result.append(os.path.join(root, d))
        for f in files:
            result.append(os.path.join(root, f))
    return sorted(result)

def test_filter_and_patterns(paths, filter_args):
    fm = FilterManager(filter_args)
    print(f"\n过滤参数: {filter_args}")
    for p in paths:
        filtered = fm.should_filter_file(p)
        if not filtered:
            # 测试命名规则
            if os.path.isdir(p):
                new_name = format_folder_name(os.path.basename(p))
                print(f"[保留] 文件夹: {p} -> {new_name}")
            else:
                new_name = get_unique_filename(os.path.dirname(p), os.path.basename(p), artist_name="测试画师")
                print(f"[保留] 文件: {p} -> {new_name}")
        else:
            print(f"[过滤] {p}")

if __name__ == '__main__':
    base = './demo_test_patterns'
    setup_demo_dir(base)
    paths = list_all_paths(base)

    # 只处理视频
    test_filter_and_patterns(paths, {'--type': 'video'})
    # 只处理文件夹
    test_filter_and_patterns(paths, {'--include': ['folder']})
    # 只处理图片和视频
    test_filter_and_patterns(paths, {'--include': ['jpg', 'mp4', 'mkv', 'flv', 'video', 'image']})
    # 排除文件夹和txt
    test_filter_and_patterns(paths, {'--exclude': ['folder', 'txt']})

    shutil.rmtree(base)