import os
import sys
import orjson
from db_manager import DBManager

# 用法: python import_json_to_db.py <uuid目录> <db路径>
def main():
    if len(sys.argv) < 3:
        print("用法: python import_json_to_db.py <uuid目录> <db路径>")
        return
    uuid_dir = sys.argv[1]
    db_path = sys.argv[2]
    db = DBManager(db_path)
    count = 0
    for root, _, files in os.walk(uuid_dir):
        for file in files:
            if file.endswith('.json'):
                json_path = os.path.join(root, file)
                try:
                    with open(json_path, 'rb') as f:
                        data = orjson.loads(f.read())
                    uuid = data.get('uuid', os.path.splitext(file)[0])
                    file_name = data.get('archive_name', '')
                    artist = data.get('artist_name', '')
                    relative_path = data.get('relative_path', '')
                    # 尝试从timestamps中取最早的时间
                    created_time = ''
                    if 'timestamps' in data and isinstance(data['timestamps'], dict):
                        created_time = sorted(data['timestamps'].keys())[0]
                    db.insert_or_replace(uuid, orjson.dumps(data).decode('utf-8'), file_name, artist, relative_path, created_time)
                    count += 1
                    if count % 100 == 0:
                        print(f"已导入 {count} 条...")
                except Exception as e:
                    print(f"导入失败: {json_path} 错误: {e}")
    db.close()
    print(f"导入完成，共导入 {count} 条记录。")

if __name__ == '__main__':
    main() 