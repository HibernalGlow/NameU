import os
import shutil
from nameu.type.filter_manager import FilterManager

def setup_demo_dir(base):
    if os.path.exists(base):
        shutil.rmtree(base)
    os.makedirs(base)
    os.makedirs(os.path.join(base, "subfolder"))
    with open(os.path.join(base, "a.jpg"), "w") as f:
        f.write("img")
    with open(os.path.join(base, "b.txt"), "w") as f:
        f.write("txt")
    with open(os.path.join(base, "subfolder", "c.png"), "w") as f:
        f.write("img2")

def list_all_paths(base):
    result = []
    for root, dirs, files in os.walk(base):
        for d in dirs:
            result.append(os.path.join(root, d))
        for f in files:
            result.append(os.path.join(root, f))
    return sorted(result)

def test_filter(paths, filter_args):
    fm = FilterManager(filter_args)
    print(f"\n过滤参数: {filter_args}")
    for p in paths:
        filtered = fm.should_filter_file(p)
        print(f"{'[过滤]' if filtered else '[保留]'} {p}")

if __name__ == '__main__':
    base = './demo_test_folder'
    setup_demo_dir(base)
    paths = list_all_paths(base)

    # 只处理文件夹
    test_filter(paths, {'--include': ['folder']})
    # 排除文件夹
    test_filter(paths, {'--exclude': ['folder']})
    # 只处理图片和文件夹
    test_filter(paths, {'--include': ['jpg', 'folder']})
    # 排除图片和文件夹
    test_filter(paths, {'--exclude': ['jpg', 'folder']})
    # 只处理图片
    test_filter(paths, {'--include': ['jpg']})

    # 清理
    shutil.rmtree(base) 