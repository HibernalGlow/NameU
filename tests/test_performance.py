import os
import time
import pytest
import shutil
import tempfile
from pathlib import Path
from nameu.core.file_processor import _build_plan

def create_mock_files(directory, count):
    """创建大量虚拟文件用于测试"""
    for i in range(count):
        # 创建各种格式的文件名，模拟真实情况
        filename = f"[{i:05d}] Test File (Artist) {{123p}}.zip"
        with open(os.path.join(directory, filename), 'w') as f:
            f.write("mock content")

@pytest.mark.benchmark
def test_build_plan_performance():
    """测试 _build_plan 在万级文件下的性能"""
    with tempfile.TemporaryDirectory() as temp_dir:
        file_count = 10000
        print(f"\n正在创建 {file_count} 个模拟文件...")
        create_mock_files(temp_dir, file_count)
        
        artist_name = "[TestArtist]"
        
        print("开始测试 _build_plan (核心算法性能)...")
        start_time = time.time()
        
        # 执行优化后的规划函数
        plan = _build_plan(
            directory=temp_dir,
            artist_name=artist_name,
            add_artist_name_enabled=True,
            convert_sensitive_enabled=False,
            track_ids=False  # 关闭 ID 跟踪以仅测试核心重命名算法
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"处理 {file_count} 个文件耗时: {duration:.4f} 秒")
        print(f"生成的规划包含 {len(plan)} 个需要处理的任务")
        
        # 断言耗时。在现代机器上，优化后的 O(N) 算法处理 1万个文件通常应在 0.5s 内完成（主要是磁盘扫描耗时）
        # 旧版 O(N^2) 在 1万文件下可能需要数十秒甚至分钟级
        assert duration < 5.0, f"性能未达标: {duration:.4f}s"
        assert len(plan) > 0, "规划不应为空"

if __name__ == "__main__":
    # 手动运行示例
    pytest.main([__file__, "-s"])
