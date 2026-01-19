import os
import time
import sys
from pathlib import Path

# 模拟环境
src_path = str(Path(__file__).parent / "src")
sys.path.append(src_path)

from nameu.core.file_processor import process_folders
import tempfile
import shutil

def test_ui():
    with tempfile.TemporaryDirectory() as base_dir:
        # 创建模拟结构
        for artist in ["ArtistA", "ArtistB"]:
            artist_dir = os.path.join(base_dir, artist)
            os.makedirs(artist_dir)
            for i in range(5):
                with open(os.path.join(artist_dir, f"file_{i}.zip"), "w") as f:
                    f.write("test")
        
        # 运行处理
        print("开始测试 UI...")
        process_folders(base_dir, threads=4)
        print("测试结束。")

if __name__ == "__main__":
    test_ui()
