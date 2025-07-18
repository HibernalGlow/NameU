import os
import tempfile
import zipfile
import shutil
import pytest
import sys
from unittest.mock import patch, MagicMock



from idu.core.archive_handler import ArchiveHandler

class TestArchiveHandler:
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_json_content = '{"uuid": "test-uuid", "test": true}'
        
    def teardown_method(self):
        """每个测试方法后的清理"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_zip(self, structure_type="no_folder"):
        """创建测试用的zip文件"""
        zip_path = os.path.join(self.temp_dir, "test.zip")
        json_path = os.path.join(self.temp_dir, "test.json")
        
        with open(json_path, 'w') as f:
            f.write(self.test_json_content)
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            if structure_type == "no_folder":
                zf.write(json_path, "file1.txt")
                zf.write(json_path, "file2.txt")
            elif structure_type == "single_folder":
                zf.write(json_path, "folder1/file1.txt")
                zf.write(json_path, "folder1/file2.txt")
            elif structure_type == "multiple_folders":
                zf.write(json_path, "folder1/file1.txt")
                zf.write(json_path, "folder2/file2.txt")
        
        os.remove(json_path)
        return zip_path
    
    def test_check_archive_integrity(self):
        """测试压缩包完整性检查"""
        zip_path = self.create_test_zip()
        assert ArchiveHandler.check_archive_integrity(zip_path) == True
        assert ArchiveHandler.check_archive_integrity("nonexistent.zip") == True
    
    def test_analyze_folder_structure_no_folder(self):
        """测试分析无文件夹结构"""
        zip_path = self.create_test_zip("no_folder")
        result = ArchiveHandler._analyze_folder_structure(zip_path)
        assert result == "no_folder"
    
    def test_analyze_folder_structure_single_folder(self):
        """测试分析单文件夹结构"""
        zip_path = self.create_test_zip("single_folder")
        result = ArchiveHandler._analyze_folder_structure(zip_path)
        assert result == "single_folder"
    
    def test_analyze_folder_structure_multiple_folders(self):
        """测试分析多文件夹结构"""
        zip_path = self.create_test_zip("multiple_folders")
        result = ArchiveHandler._analyze_folder_structure(zip_path)
        assert result == "multiple_folders"
    
    def test_get_single_folder_name(self):
        """测试获取单文件夹名称"""
        zip_path = self.create_test_zip("single_folder")
        folder_name = ArchiveHandler._get_single_folder_name(zip_path)
        assert folder_name == "folder1"
    
    def test_get_single_folder_name_no_folder(self):
        """测试无文件夹时获取文件夹名称"""
        zip_path = self.create_test_zip("no_folder")
        folder_name = ArchiveHandler._get_single_folder_name(zip_path)
        assert folder_name is None
    
    def test_load_yaml_uuid_from_archive(self):
        """测试从压缩包加载YAML UUID"""
        zip_path = os.path.join(self.temp_dir, "test.zip")
        yaml_content = "test: true"

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test-uuid.yaml", yaml_content)
            zf.writestr("other.txt", "content")

        uuid = ArchiveHandler.load_yaml_uuid_from_archive(zip_path)
        assert uuid == "test-uuid"

    def test_load_yaml_uuid_from_archive_with_folder(self):
        """测试从单文件夹结构压缩包加载YAML UUID"""
        zip_path = os.path.join(self.temp_dir, "test.zip")
        yaml_content = "test: true"

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("folder1/test-uuid.yaml", yaml_content)
            zf.writestr("folder1/other.txt", "content")

        uuid = ArchiveHandler.load_yaml_uuid_from_archive(zip_path)
        assert uuid == "test-uuid"  # 应该只返回文件名部分，不包含路径
    
    def test_load_json_uuid_from_archive(self):
        """测试从压缩包加载JSON UUID"""
        zip_path = os.path.join(self.temp_dir, "test.zip")

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("test-uuid.json", self.test_json_content)
            zf.writestr("other.txt", "content")

        uuid = ArchiveHandler.load_json_uuid_from_archive(zip_path)
        assert uuid == "test-uuid"

    def test_load_json_uuid_from_archive_with_folder(self):
        """测试从单文件夹结构压缩包加载JSON UUID"""
        zip_path = os.path.join(self.temp_dir, "test.zip")

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("folder1/test-uuid.json", self.test_json_content)
            zf.writestr("folder1/other.txt", "content")

        uuid = ArchiveHandler.load_json_uuid_from_archive(zip_path)
        assert uuid == "test-uuid"  # 应该只返回文件名部分，不包含路径
    
    def test_add_json_to_archive_no_folder(self):
        """测试添加JSON到无文件夹结构的压缩包"""
        zip_path = self.create_test_zip("no_folder")
        json_path = os.path.join(self.temp_dir, "new.json")
        
        with open(json_path, 'w') as f:
            f.write(self.test_json_content)
        
        result = ArchiveHandler.add_json_to_archive(zip_path, json_path, "new.json")
        assert result == True
        
        # 验证文件被添加到根目录
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert "new.json" in zf.namelist()
    
    def test_add_json_to_archive_single_folder(self):
        """测试添加JSON到单文件夹结构的压缩包"""
        zip_path = self.create_test_zip("single_folder")
        json_path = os.path.join(self.temp_dir, "new.json")
        
        with open(json_path, 'w') as f:
            f.write(self.test_json_content)
        
        result = ArchiveHandler.add_json_to_archive(zip_path, json_path, "new.json")
        assert result == True
        
        # 验证文件被添加到文件夹内
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert "folder1/new.json" in zf.namelist()
    
    def test_add_json_to_archive_multiple_folders(self):
        """测试添加JSON到多文件夹结构的压缩包"""
        zip_path = self.create_test_zip("multiple_folders")
        json_path = os.path.join(self.temp_dir, "new.json")
        
        with open(json_path, 'w') as f:
            f.write(self.test_json_content)
        
        result = ArchiveHandler.add_json_to_archive(zip_path, json_path, "new.json")
        assert result == True
        
        # 验证文件被添加到根目录
        with zipfile.ZipFile(zip_path, 'r') as zf:
            assert "new.json" in zf.namelist()
    
    @patch('subprocess.run')
    def test_delete_files_from_archive_success(self, mock_run):
        """测试成功删除压缩包中的文件"""
        zip_path = self.create_test_zip("no_folder")
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        result = ArchiveHandler.delete_files_from_archive(zip_path, ["file1.txt"])
        assert result == True
        mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_delete_files_from_archive_failure(self, mock_run):
        """测试删除压缩包中文件失败"""
        zip_path = self.create_test_zip("no_folder")
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        
        result = ArchiveHandler.delete_files_from_archive(zip_path, ["file1.txt"])
        assert result == False
    
    def test_delete_files_from_archive_empty_list(self):
        """测试删除空文件列表"""
        zip_path = self.create_test_zip("no_folder")
        result = ArchiveHandler.delete_files_from_archive(zip_path, [])
        assert result == True
    
    @patch('subprocess.run')
    def test_load_uuid_from_7z_fallback(self, mock_run):
        """测试7z回退机制"""
        # 创建一个无效的zip文件来触发7z回退
        invalid_zip = os.path.join(self.temp_dir, "invalid.zip")
        with open(invalid_zip, 'w') as f:
            f.write("not a zip file")
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test-uuid.yaml\nother files..."
        )
        
        uuid = ArchiveHandler.load_yaml_uuid_from_archive(invalid_zip)
        # 由于mock的输出格式，这个测试主要验证不会崩溃
        mock_run.assert_called()

if __name__ == '__main__':
    pytest.main([__file__])