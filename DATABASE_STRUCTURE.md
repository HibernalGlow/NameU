# NameSet 数据库结构文档

NameSet 系统使用 SQLite 数据库来存储压缩包的ID、历史记录和名称变更信息。数据库文件默认位于项目根目录：`archives.db`

## 📊 数据库表结构

### 1. `archive_info` 表 - 压缩包基本信息

这是主表，存储每个压缩包的基本信息和当前状态。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | TEXT | PRIMARY KEY | 压缩包唯一ID（12字符nanoid） |
| `file_path` | TEXT | NOT NULL | 当前文件路径 |
| `file_hash` | TEXT | NULL | 文件MD5哈希值（用于移动后匹配） |
| `current_name` | TEXT | NOT NULL | 当前文件名 |
| `artist_name` | TEXT | NULL | 画师名称 |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 记录创建时间 |
| `updated_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 记录更新时间 |

**索引：**
- `idx_archive_path`: 文件路径索引
- `idx_archive_hash`: 文件哈希索引

### 2. `archive_history` 表 - 压缩包历史记录

存储压缩包的所有重命名历史和变更记录。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | 历史记录ID |
| `archive_id` | TEXT | NOT NULL, FOREIGN KEY | 关联的压缩包ID |
| `old_name` | TEXT | NULL | 旧文件名 |
| `new_name` | TEXT | NOT NULL | 新文件名 |
| `reason` | TEXT | NULL | 修改原因（如"nameu重命名"） |
| `metadata` | TEXT | NULL | 额外元数据（JSON格式） |
| `timestamp` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 变更时间 |

**索引：**
- `idx_history_archive_id`: 压缩包ID索引

**外键关系：**
- `archive_id` → `archive_info.id`

## 🔄 数据流程

### 1. 新文件处理流程
```
1. 生成唯一ID (nanoid 12字符)
2. 创建 archive_info 记录
3. 计算文件哈希值
4. 设置ZIP注释（JSON格式包含ID）
```

### 2. 重命名流程
```
1. 检查注释中的ID
2. 查找或创建 archive_info 记录
3. 执行文件重命名
4. 更新 archive_info.current_name
5. 添加 archive_history 记录
```

### 3. 历史匹配流程
```
1. 通过文件哈希匹配 (最准确)
2. 通过文件名模糊匹配
3. 通过画师名称过滤
```

## 📋 数据示例

### archive_info 表示例
```sql
INSERT INTO archive_info VALUES (
    'uqYLHx2Gj1LI',                              -- id
    'D:\Gallery\Artist\作品集.zip',               -- file_path
    '5d41402abc4b2a76b9719d911017c592',          -- file_hash
    '作品集 Artist.zip',                          -- current_name
    'Artist',                                    -- artist_name
    '2025-07-20 00:30:00',                      -- created_at
    '2025-07-20 00:45:00'                       -- updated_at
);
```

### archive_history 表示例
```sql
INSERT INTO archive_history VALUES (
    1,                                           -- id
    'uqYLHx2Gj1LI',                             -- archive_id
    '[Artist]作品集.zip',                        -- old_name
    '作品集 Artist.zip',                         -- new_name
    'nameu重命名',                               -- reason
    '{"artist_name":"Artist","rename_method":"nameu"}', -- metadata
    '2025-07-20 00:45:00'                       -- timestamp
);
```

## 🔍 主要查询操作

### 1. 根据ID获取压缩包信息
```sql
SELECT * FROM archive_info WHERE id = ?;
```

### 2. 根据文件哈希查找ID
```sql
SELECT id FROM archive_info WHERE file_hash = ?;
```

### 3. 模糊搜索文件名
```sql
SELECT DISTINCT ai.id, ai.current_name, ai.artist_name 
FROM archive_info ai
LEFT JOIN archive_history ah ON ai.id = ah.archive_id
WHERE (ai.current_name LIKE ? OR ah.old_name LIKE ? OR ah.new_name LIKE ?)
ORDER BY ai.updated_at DESC;
```

### 4. 获取历史记录
```sql
SELECT old_name, new_name, reason, metadata, timestamp
FROM archive_history
WHERE archive_id = ?
ORDER BY timestamp DESC;
```

### 5. 统计信息
```sql
-- 总压缩包数量
SELECT COUNT(*) FROM archive_info;

-- 总历史记录数量
SELECT COUNT(*) FROM archive_history;

-- 按画师分组统计
SELECT artist_name, COUNT(*) 
FROM archive_info 
WHERE artist_name IS NOT NULL 
GROUP BY artist_name 
ORDER BY COUNT(*) DESC;
```

## 💾 存储位置

- **默认位置**: `项目根目录/archives.db`
- **可配置**: 通过 `ArchiveIDManager(db_path="自定义路径")` 指定
- **自动创建**: 数据库和表结构在首次使用时自动创建

## 🔧 维护操作

### 备份数据库
```bash
cp archives.db archives_backup_$(date +%Y%m%d).db
```

### 查看数据库信息
```bash
sqlite3 archives.db ".schema"  # 查看表结构
sqlite3 archives.db ".tables"  # 查看所有表
```

### 数据库迁移
如需迁移到新位置，只需复制 `archives.db` 文件即可。

## 🎯 设计特点

1. **简单高效**: 使用SQLite，无需额外服务
2. **完整历史**: 记录所有重命名操作
3. **智能匹配**: 支持哈希和名称双重匹配
4. **扩展性**: 元数据字段支持JSON格式存储
5. **跨平台**: SQLite确保跨平台兼容性

## 🔄 恢复功能

### 支持的恢复操作

现有数据结构完全支持恢复功能，无需新增表或字段：

#### 1. 单文件恢复
```python
# 根据当前名称找到ID
archive_id = db.get_archive_id_by_path(file_path)

# 获取历史记录
history = db.get_archive_history(archive_id)

# 选择要恢复的名称并执行恢复
manager.process_archive_rename(file_path, target_name, "恢复操作")
```

#### 2. 按日期批量恢复
```sql
-- 查找指定日期前最后一次重命名记录
SELECT new_name FROM archive_history 
WHERE archive_id = ? AND date(timestamp) <= ?
ORDER BY timestamp DESC LIMIT 1;
```

#### 3. 文件夹扫描恢复
- 扫描指定文件夹下所有压缩包
- 根据文件名/哈希匹配历史记录
- 提供恢复预览和批量操作

### 恢复工具使用

```bash
# 交互式模式
python restore_tool.py

# 命令行模式 - 扫描指定文件夹
python restore_tool.py "D:\Gallery\Artist"
```

### 恢复流程

1. **扫描阶段**: 遍历文件夹，匹配文件与数据库记录
2. **选择阶段**: 展示历史记录，用户选择目标名称
3. **确认阶段**: 预览更改，确认执行
4. **执行阶段**: 重命名文件，更新数据库
5. **记录阶段**: 在 `archive_history` 中记录恢复操作
