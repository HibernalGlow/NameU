"""trename 单元测试"""

import tempfile
from pathlib import Path

import pytest

from trename.models import (
    DirNode,
    FileNode,
    RenameJSON,
    count_pending,
    count_ready,
    count_total,
)
from trename.renamer import FileRenamer
from trename.scanner import FileScanner
from trename.validator import ConflictValidator


class TestSanitizeFilename:
    """测试 Windows 禁止字符清理"""

    def test_sanitize_slash(self):
        """测试斜杠替换"""
        renamer = FileRenamer()
        result = renamer._sanitize_filename("Fate/Grand Order.zip")
        assert "/" not in result
        assert result == "Fate Grand Order.zip"

    def test_sanitize_colon(self):
        """测试冒号替换"""
        renamer = FileRenamer()
        result = renamer._sanitize_filename("file:name.txt")
        assert ":" not in result
        assert result == "file name.txt"

    def test_sanitize_question_mark(self):
        """测试问号替换"""
        renamer = FileRenamer()
        result = renamer._sanitize_filename("what?.txt")
        assert "?" not in result
        assert result == "what .txt"

    def test_sanitize_multiple_chars(self):
        """测试多个禁止字符"""
        renamer = FileRenamer()
        result = renamer._sanitize_filename('file<>:"/\\|?*.txt')
        # 所有禁止字符都应被替换
        for char in '<>:"/\\|?*':
            assert char not in result

    def test_sanitize_consecutive_spaces(self):
        """测试连续空格合并"""
        renamer = FileRenamer()
        result = renamer._sanitize_filename("a::b.txt")
        assert "  " not in result
        assert result == "a b.txt"

    def test_sanitize_complex_name(self):
        """测试复杂文件名"""
        renamer = FileRenamer()
        name = "(Fate/Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip"
        result = renamer._sanitize_filename(name)
        assert "/" not in result
        assert result == "(Fate Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip"

    def test_sanitize_no_change(self):
        """测试无需清理的文件名"""
        renamer = FileRenamer()
        name = "normal_file.txt"
        result = renamer._sanitize_filename(name)
        assert result == name


class TestFileScanner:
    """测试文件扫描器"""

    def test_scan_empty_dir(self):
        """测试扫描空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            scanner = FileScanner()
            result = scanner.scan(Path(tmpdir))
            assert isinstance(result, RenameJSON)
            assert result.root == []

    def test_scan_with_files(self):
        """测试扫描包含文件的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            (Path(tmpdir) / "test1.txt").touch()
            (Path(tmpdir) / "test2.pdf").touch()

            scanner = FileScanner()
            result = scanner.scan(Path(tmpdir))

            assert len(result.root) == 2
            names = {node.src for node in result.root}
            assert "test1.txt" in names
            assert "test2.pdf" in names

    def test_scan_with_subdir(self):
        """测试扫描包含子目录的目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录和文件
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file.txt").touch()

            scanner = FileScanner()
            result = scanner.scan(Path(tmpdir))

            assert len(result.root) == 1
            assert isinstance(result.root[0], DirNode)
            assert result.root[0].src_dir == "subdir"
            assert len(result.root[0].children) == 1

    def test_scan_ignore_hidden(self):
        """测试忽略隐藏文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".hidden").touch()
            (Path(tmpdir) / "visible.txt").touch()

            scanner = FileScanner(ignore_hidden=True)
            result = scanner.scan(Path(tmpdir))

            assert len(result.root) == 1
            assert result.root[0].src == "visible.txt"

    def test_scan_not_found(self):
        """测试扫描不存在的目录"""
        scanner = FileScanner()
        with pytest.raises(FileNotFoundError):
            scanner.scan(Path("/nonexistent/path"))


class TestConflictValidator:
    """测试冲突检测器"""

    def test_no_conflicts(self):
        """测试无冲突场景"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt="b.txt"),
                FileNode(src="c.txt", tgt="d.txt"),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").touch()
            (Path(tmpdir) / "c.txt").touch()

            validator = ConflictValidator()
            conflicts = validator.validate(rename_json, Path(tmpdir))
            assert len(conflicts) == 0

    def test_target_exists_conflict(self):
        """测试目标已存在冲突"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt="b.txt"),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").touch()
            (Path(tmpdir) / "b.txt").touch()  # 目标已存在

            validator = ConflictValidator()
            conflicts = validator.validate(rename_json, Path(tmpdir))
            assert len(conflicts) == 1
            assert "已存在" in conflicts[0].message

    def test_duplicate_target_conflict(self):
        """测试重复目标冲突"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt="same.txt"),
                FileNode(src="b.txt", tgt="same.txt"),  # 重复目标
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").touch()
            (Path(tmpdir) / "b.txt").touch()

            validator = ConflictValidator()
            conflicts = validator.validate(rename_json, Path(tmpdir))
            assert len(conflicts) == 2  # 两个源都报告冲突

    def test_smart_dedup(self):
        """测试智能去重"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt="same.txt"),
                FileNode(src="b.txt", tgt="same.txt"),
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.txt").touch()
            (Path(tmpdir) / "b.txt").touch()

            validator = ConflictValidator()
            operations, conflicts = validator.get_valid_operations(
                rename_json, Path(tmpdir), smart_dedup=True
            )
            # 智能去重后只有一个操作
            assert len(operations) == 1


class TestCountFunctions:
    """测试计数函数"""

    def test_count_pending(self):
        """测试待翻译计数"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt=""),  # pending
                FileNode(src="b.txt", tgt="c.txt"),  # not pending
                DirNode(
                    src_dir="dir",
                    tgt_dir="",  # pending
                    children=[
                        FileNode(src="d.txt", tgt=""),  # pending
                    ],
                ),
            ]
        )
        assert count_pending(rename_json) == 3

    def test_count_ready(self):
        """测试可重命名计数"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt=""),  # not ready
                FileNode(src="b.txt", tgt="c.txt"),  # ready
                FileNode(src="d.txt", tgt="d.txt"),  # not ready (same name)
            ]
        )
        assert count_ready(rename_json) == 1

    def test_count_total(self):
        """测试总数计数"""
        rename_json = RenameJSON(
            root=[
                FileNode(src="a.txt", tgt=""),
                DirNode(
                    src_dir="dir",
                    tgt_dir="",
                    children=[
                        FileNode(src="b.txt", tgt=""),
                        FileNode(src="c.txt", tgt=""),
                    ],
                ),
            ]
        )
        assert count_total(rename_json) == 4  # 1 file + 1 dir + 2 children


class TestJSONRoundTrip:
    """测试 JSON 序列化/反序列化"""

    def test_roundtrip_file_node(self):
        """测试文件节点 round-trip"""
        original = RenameJSON(
            root=[
                FileNode(src="test.txt", tgt="测试.txt"),
            ]
        )
        json_str = original.model_dump_json()
        parsed = RenameJSON.model_validate_json(json_str)

        assert len(parsed.root) == 1
        assert parsed.root[0].src == "test.txt"
        assert parsed.root[0].tgt == "测试.txt"

    def test_roundtrip_dir_node(self):
        """测试目录节点 round-trip"""
        original = RenameJSON(
            root=[
                DirNode(
                    src_dir="folder",
                    tgt_dir="文件夹",
                    children=[
                        FileNode(src="a.txt", tgt="甲.txt"),
                    ],
                ),
            ]
        )
        json_str = original.model_dump_json()
        parsed = RenameJSON.model_validate_json(json_str)

        assert len(parsed.root) == 1
        assert isinstance(parsed.root[0], DirNode)
        assert parsed.root[0].src_dir == "folder"
        assert parsed.root[0].tgt_dir == "文件夹"
        assert len(parsed.root[0].children) == 1


class TestFileRenamer:
    """测试文件重命名器"""

    def test_rename_single_file(self):
        """测试单文件重命名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "old.txt"
            src.write_text("test")

            rename_json = RenameJSON(
                root=[FileNode(src="old.txt", tgt="new.txt")]
            )

            renamer = FileRenamer()
            result = renamer.rename_batch(rename_json, Path(tmpdir))

            assert result.success_count == 1
            assert result.failed_count == 0
            assert not src.exists()
            assert (Path(tmpdir) / "new.txt").exists()

    def test_rename_with_sanitize(self):
        """测试带禁止字符的重命名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "old.txt"
            src.write_text("test")

            rename_json = RenameJSON(
                root=[FileNode(src="old.txt", tgt="new/file.txt")]
            )

            renamer = FileRenamer()
            result = renamer.rename_batch(rename_json, Path(tmpdir))

            assert result.success_count == 1
            # 斜杠被替换为空格
            assert (Path(tmpdir) / "new file.txt").exists()

    def test_dry_run(self):
        """测试模拟执行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / "old.txt"
            src.write_text("test")

            rename_json = RenameJSON(
                root=[FileNode(src="old.txt", tgt="new.txt")]
            )

            renamer = FileRenamer()
            result = renamer.rename_batch(rename_json, Path(tmpdir), dry_run=True)

            assert result.success_count == 1
            # dry_run 不实际执行
            assert src.exists()
            assert not (Path(tmpdir) / "new.txt").exists()



class TestJSONFix:
    """测试 JSON 修复功能"""

    def test_fix_trailing_comma(self):
        """测试修复末尾逗号"""
        from trename.scanner import fix_json

        # 末尾逗号
        bad_json = '{"root": [{"src": "a.txt", "tgt": "b.txt"},]}'
        fixed = fix_json(bad_json)
        assert ",]" not in fixed

    def test_fix_nested_trailing_comma(self):
        """测试修复嵌套末尾逗号"""
        from trename.scanner import fix_json

        bad_json = '''{"root": [
            {"src": "a.txt", "tgt": "b.txt"},
            {"src": "c.txt", "tgt": "d.txt"},
        ]}'''
        fixed = fix_json(bad_json)
        assert ",\n        ]" not in fixed

    def test_parse_with_trailing_comma(self):
        """测试解析带末尾逗号的 JSON"""
        bad_json = '{"root": [{"src": "test.txt", "tgt": "测试.txt"},]}'
        result = FileScanner.from_json(bad_json)
        assert len(result.root) == 1
        assert result.root[0].src == "test.txt"



class TestRealWorldJSON:
    """测试真实场景 JSON"""

    def test_parse_fate_json(self):
        """测试解析 Fate 相关 JSON（带斜杠和末尾逗号）"""
        json_str = '''{"root": [{"src_dir": "[阿薰kaori]","tgt_dir": "[阿薰kaori]","children": [{"src": "阿薰 kaOri - FGO 白 Saber.zip", "tgt": "(Fate/Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip"},{"src": "阿薰 kaOri NO.012 斯卡哈兔女郎 [18P-690MB].zip", "tgt": "012. (Fate/Grand Order · 斯卡哈#兔女郎) 斯卡哈兔女郎 [阿薰 kaOri] [18P-690MB].zip"},]}]}'''
        
        result = FileScanner.from_json(json_str)
        
        assert len(result.root) == 1
        assert result.root[0].src_dir == "[阿薰kaori]"
        assert len(result.root[0].children) == 2

    def test_sanitize_fate_filename(self):
        """测试清理 Fate 文件名中的斜杠"""
        from trename.validator import sanitize_filename
        
        name = "(Fate/Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip"
        result = sanitize_filename(name)
        
        assert "/" not in result
        assert result == "(Fate Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip"

    def test_rename_with_fate_filename(self):
        """测试重命名带斜杠的 Fate 文件名"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建源文件
            src_dir = Path(tmpdir) / "[阿薰kaori]"
            src_dir.mkdir()
            src_file = src_dir / "阿薰 kaOri - FGO 白 Saber.zip"
            src_file.write_text("test")

            rename_json = RenameJSON(
                root=[
                    DirNode(
                        src_dir="[阿薰kaori]",
                        tgt_dir="[阿薰kaori]",
                        children=[
                            FileNode(
                                src="阿薰 kaOri - FGO 白 Saber.zip",
                                tgt="(Fate/Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip",
                            )
                        ],
                    )
                ]
            )

            renamer = FileRenamer()
            result = renamer.rename_batch(rename_json, Path(tmpdir))

            assert result.success_count == 1
            assert result.failed_count == 0
            
            # 验证文件已重命名（斜杠被替换为空格）
            expected_name = "(Fate Grand Order · 阿尔托莉雅) FGO 白 Saber [阿薰 kaOri].zip"
            assert (src_dir / expected_name).exists()
            assert not src_file.exists()
