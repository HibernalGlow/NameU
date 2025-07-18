#!/usr/bin/env python3
"""
IDSet极简使用示例 - SQLModel版本
"""

from idset import IDSet, new_id


def main():
    """基本使用示例"""
    print("=== IDSet极简使用 (SQLModel版本) ===")

    # 创建管理器
    ids = IDSet("example.db")

    # 生成ID
    print(f"生成ID: {new_id()}")

    # 添加记录
    uuid1 = ids.add(file_name="test1.zip", artist="artist1")
    uuid2 = ids.add(file_name="test2.zip", artist="artist2")

    print(f"添加记录: {uuid1}, {uuid2}")

    # 获取记录
    record = ids.get(uuid1)
    print(f"获取记录: {record}")

    # 查找记录
    records = ids.find(artist="artist1")
    print(f"查找记录: {len(records)} 条")

    # 更新记录
    ids.update(uuid1, artist="updated_artist")
    print(f"更新记录: {uuid1}")

    # 统计
    print(f"总记录数: {ids.count()}")
    print(f"所有ID: {list(ids.all_ids())[:3]}...")  # 只显示前3个

    # 删除记录
    ids.delete(uuid2)
    print(f"删除记录: {uuid2}")
    print(f"删除后总数: {ids.count()}")


if __name__ == "__main__":
    main()
