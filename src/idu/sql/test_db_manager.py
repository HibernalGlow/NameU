from db_manager import DBManager
import orjson
import time

DB_PATH = "E:/1BACKUP/ehv/uuid/artworks.db"  # 可根据实际情况调整路径

def main():
    db = DBManager(DB_PATH)
    # 插入测试数据
    # for i in range(3):
    #     uuid = f"test-uuid-{i}"
    #     json_data = orjson.dumps({"uuid": uuid, "test": True, "index": i}).decode('utf-8')
    #     file_name = f"test_file_{i}.zip"
    #     artist = f"artist_{i}"
    #     relative_path = f"folder/sub_{i}"
    #     created_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    #     db.insert_or_replace(uuid, json_data, file_name, artist, relative_path, created_time)
    # 查询所有uuid
    uuids = db.get_all_uuids()
    print(f"所有uuid: {uuids}")
    # 展示前5条详细内容
    print("\n前5条详细内容:")
    for uuid in uuids[50:55]:
        data = db.get_by_uuid(uuid)
        print(data)
    db.close()

if __name__ == '__main__':
    main() 