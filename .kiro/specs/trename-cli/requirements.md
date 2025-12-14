# Requirements Document

## Introduction

trename 是一个文件批量重命名工具，支持扫描文件树生成 JSON 结构、通过剪贴板与 AI 翻译工具交互、以及基于 JSON 执行批量重命名操作。该工具提供 CLI 核心功能和 Streamlit 可视化界面。

## Glossary

- **File_Tree**: 文件系统中的目录和文件层级结构
- **Rename_JSON**: 描述源文件名和目标文件名映射关系的 JSON 数据结构
- **Clipboard**: 系统剪贴板，用于在工具和 AI 翻译服务之间传递数据
- **Conflict**: 重命名操作中目标文件名已存在或多个源文件映射到同一目标名的情况
- **Pending_Item**: 在 Rename_JSON 中 tgt 字段为空的待翻译项目

## Requirements

### Requirement 1

**User Story:** As a user, I want to scan a directory and generate a JSON structure of the file tree, so that I can send it to AI for translation.

#### Acceptance Criteria

1. WHEN a user executes the scan subcommand with a directory path THEN the trename system SHALL generate a Rename_JSON structure containing all files and subdirectories
2. WHEN the scan operation completes THEN the trename system SHALL copy the generated Rename_JSON to the Clipboard by default
3. WHEN a user specifies an output file option THEN the trename system SHALL write the Rename_JSON to the specified file instead of the Clipboard
4. WHEN scanning a directory THEN the trename system SHALL preserve the hierarchical structure with src_dir, tgt_dir, src, tgt, and children fields
5. WHEN scanning encounters an inaccessible directory THEN the trename system SHALL skip the directory and log a warning message

### Requirement 2

**User Story:** As a user, I want to rename files based on a JSON mapping, so that I can batch rename files after AI translation.

#### Acceptance Criteria

1. WHEN a user executes the rename subcommand THEN the trename system SHALL read the Rename_JSON from the Clipboard by default
2. WHEN a user specifies an input file option THEN the trename system SHALL read the Rename_JSON from the specified file
3. WHEN processing a Rename_JSON THEN the trename system SHALL rename each file where both src and tgt fields are non-empty
4. WHEN a target filename already exists THEN the trename system SHALL skip the rename operation and report the Conflict
5. WHEN multiple source files map to the same target name THEN the trename system SHALL detect and report all Conflicts before executing any rename
6. WHEN the Rename_JSON contains invalid paths THEN the trename system SHALL skip invalid entries and continue processing valid ones
7. WHEN renaming directories THEN the trename system SHALL process child items first before renaming the parent directory

### Requirement 3

**User Story:** As a user, I want to parse and serialize Rename_JSON, so that the tool can reliably read and write the JSON format.

#### Acceptance Criteria

1. WHEN parsing a Rename_JSON string THEN the trename system SHALL validate the JSON structure against the expected schema
2. WHEN serializing a file tree to Rename_JSON THEN the trename system SHALL produce valid JSON that can be parsed back to an equivalent structure
3. WHEN parsing encounters malformed JSON THEN the trename system SHALL report a clear error message with the location of the syntax error

### Requirement 4

**User Story:** As a user, I want a Streamlit web interface, so that I can perform all operations visually without using CLI.

#### Acceptance Criteria

1. WHEN a user launches the Streamlit interface THEN the trename system SHALL display a file tree view of the current Rename_JSON
2. WHEN displaying the file tree THEN the trename system SHALL visually distinguish between renamed items, Pending_Items, and Conflicts
3. WHEN a user edits a tgt field in the interface THEN the trename system SHALL update the Rename_JSON in real-time
4. WHEN Conflicts exist THEN the trename system SHALL highlight all conflicting items and display a summary of Conflicts
5. WHEN a user clicks the rename button THEN the trename system SHALL execute the rename operation for all valid non-conflicting items
6. WHEN the rename operation completes THEN the trename system SHALL refresh the display to show the updated file tree status
7. WHEN a user selects a directory in the interface THEN the trename system SHALL scan the directory and display the generated Rename_JSON
8. WHEN a user pastes or imports JSON in the interface THEN the trename system SHALL parse and display the Rename_JSON structure
9. WHEN a user clicks the export button THEN the trename system SHALL copy the current Rename_JSON to the Clipboard
10. WHEN a user uploads a JSON file THEN the trename system SHALL load and display the Rename_JSON from the file

### Requirement 5

**User Story:** As a user, I want to see which items are pending translation, so that I can track progress.

#### Acceptance Criteria

1. WHEN displaying the Rename_JSON THEN the trename system SHALL count and display the total number of Pending_Items
2. WHEN filtering by status THEN the trename system SHALL allow users to view only Pending_Items, only completed items, or all items
3. WHEN a Pending_Item receives a tgt value THEN the trename system SHALL update the pending count immediately

### Requirement 6

**User Story:** As a user, I want to undo rename operations, so that I can recover from mistakes.

#### Acceptance Criteria

1. WHEN a rename operation completes THEN the trename system SHALL save a Undo_Record containing the original and new file paths
2. WHEN a user triggers the undo action THEN the trename system SHALL restore files to their original names using the Undo_Record
3. WHEN undoing a batch rename THEN the trename system SHALL process items in reverse order to handle directory renames correctly
4. WHEN an undo operation fails for a specific item THEN the trename system SHALL report the failure and continue with remaining items
5. WHEN the Streamlit interface displays rename history THEN the trename system SHALL show recent operations with undo buttons
6. WHEN a user clicks undo in the interface THEN the trename system SHALL execute the undo operation and refresh the display
