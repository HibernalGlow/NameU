# Implementation Plan

- [x] 1. 项目初始化和数据模型




  - [ ] 1.1 创建 trename 包结构和依赖配置
    - 创建 `src/trename/__init__.py`, `__main__.py`


    - 在 `pyproject.toml` 添加依赖: typer, pydantic, pyperclip, streamlit, hypothesis
    - _Requirements: 1.1, 2.1_
  - [ ] 1.2 实现 Pydantic 数据模型 (FileNode, DirNode, RenameJSON)
    - 创建 `src/trename/models.py`
    - 实现 FileNode, DirNode, RenameJSON 模型
    - 添加 is_pending computed_field




    - _Requirements: 1.4, 3.1_
  - [ ]* 1.3 编写属性测试: JSON Round-trip
    - **Property 5: JSON Round-trip Consistency**
    - **Validates: Requirements 3.2**

- [x] 2. 文件扫描功能




  - [ ] 2.1 实现 FileScanner 类
    - 创建 `src/trename/scanner.py`
    - 使用 pathlib 递归扫描目录
    - 生成 RenameJSON 结构
    - _Requirements: 1.1, 1.4_
  - [x]* 2.2 编写属性测试: 扫描完整性




    - **Property 1: Scan Completeness and Structure Preservation**
    - **Validates: Requirements 1.1, 1.4**

- [ ] 3. 冲突检测功能
  - [ ] 3.1 实现 ConflictValidator 类
    - 创建 `src/trename/validator.py`
    - 检测目标已存在冲突




    - 检测重复目标冲突
    - _Requirements: 2.4, 2.5_
  - [ ]* 3.2 编写属性测试: 冲突检测完整性
    - **Property 3: Conflict Detection Completeness**
    - **Validates: Requirements 2.4, 2.5**

- [x] 4. 文件重命名功能




  - [ ] 4.1 实现 FileRenamer 类
    - 创建 `src/trename/renamer.py`

    - 使用 shutil.move() 执行重命名
    - 子项先于父目录处理
    - _Requirements: 2.3, 2.7_
  - [ ]* 4.2 编写属性测试: 重命名执行和目录处理顺序
    - **Property 2: Rename Execution Correctness**


    - **Property 4: Directory Processing Order**




    - **Validates: Requirements 2.3, 2.7**

- [ ] 5. 撤销功能
  - [x] 5.1 实现 UndoManager 类 (SQLite 存储)

    - 创建 `src/trename/undo.py`
    - 初始化 SQLite 数据库和表结构
    - 实现 record(), undo(), get_history() 方法
    - _Requirements: 6.1, 6.2, 6.3_
  - [x]* 5.2 编写属性测试: 撤销 Round-trip 和记录完整性

    - **Property 7: Undo Round-trip Restoration**
    - **Property 8: Undo Record Completeness and Order**
    - **Validates: Requirements 6.1, 6.2, 6.3**





- [ ] 6. 剪贴板和工具函数
  - [x] 6.1 实现 ClipboardHandler 类

    - 创建 `src/trename/clipboard.py`
    - 使用 pyperclip 实现 copy/paste
    - _Requirements: 1.2, 2.1_

  - [ ] 6.2 实现 Pending 计数功能
    - 在 models.py 添加 count_pending() 函数
    - _Requirements: 5.1_
  - [x]* 6.3 编写属性测试: Pending 计数准确性

    - **Property 6: Pending Count Accuracy**
    - **Validates: Requirements 5.1**

- [x] 7. Checkpoint - 确保所有测试通过

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. CLI 实现
  - [x] 8.1 实现 scan 子命令

    - 创建 `src/trename/cli.py`
    - 使用 typer 定义 scan 命令
    - 支持 --output 参数指定输出文件

    - 默认复制到剪贴板
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 8.2 实现 rename 子命令



    - 添加 rename 命令到 cli.py
    - 支持 --input 参数指定输入文件
    - 默认从剪贴板读取
    - 显示冲突和结果摘要
    - _Requirements: 2.1, 2.2, 2.3_
  - [ ] 8.3 实现 undo 子命令
    - 添加 undo 命令到 cli.py
    - 支持 --list 显示历史
    - 支持指定 batch_id 撤销
    - _Requirements: 6.2_

- [ ] 9. Streamlit 界面
  - [ ] 9.1 创建 Streamlit 应用框架
    - 创建 `src/trename/app.py`
    - 实现基本布局: 侧边栏 + 主区域
    - _Requirements: 4.1_
  - [ ] 9.2 实现目录扫描功能
    - 添加目录选择器
    - 扫描并显示文件树
    - _Requirements: 4.7_
  - [ ] 9.3 实现 JSON 导入/导出功能
    - 添加 JSON 文本输入区
    - 添加文件上传组件
    - 添加导出到剪贴板按钮
    - _Requirements: 4.8, 4.9, 4.10_
  - [ ] 9.4 实现文件树可视化和编辑
    - 显示文件树结构
    - 区分已完成/待处理/冲突项目
    - 支持编辑 tgt 字段
    - _Requirements: 4.2, 4.3_
  - [ ] 9.5 实现冲突显示和重命名执行
    - 高亮显示冲突项目
    - 添加重命名按钮
    - 显示操作结果
    - _Requirements: 4.4, 4.5, 4.6_
  - [ ] 9.6 实现撤销历史和操作
    - 显示操作历史列表
    - 添加撤销按钮
    - _Requirements: 6.5, 6.6_
  - [ ] 9.7 实现进度追踪显示
    - 显示 pending 计数
    - 添加状态过滤器
    - _Requirements: 5.1, 5.2_

- [ ] 10. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.
