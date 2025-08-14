import os
import tempfile
import orjson
from db_manager import DBManager

def make_test_db():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db = DBManager(tmp.name)
    return db, tmp.name

def test_insert_and_get():
    db, db_path = make_test_db()
    uuid = 'pytest-uuid-1'
    json_data = orjson.dumps({'uuid': uuid, 'pytest': True}).decode('utf-8')
    db.insert_or_replace(uuid, json_data, 'file1.zip', 'artist1', 'rel/path', '2024-01-01 00:00:00')
    result = db.get_by_uuid(uuid)
    assert result is not None
    assert result['uuid'] == uuid
    assert result['file_name'] == 'file1.zip'
    db.close()
    os.remove(db_path)

def test_get_all_uuids():
    db, db_path = make_test_db()
    uuids = []
    for i in range(5):
        uuid = f'pytest-uuid-{i}'
        uuids.append(uuid)
        json_data = orjson.dumps({'uuid': uuid, 'pytest': True}).decode('utf-8')
        db.insert_or_replace(uuid, json_data, f'file{i}.zip', f'artist{i}', f'rel/path{i}', f'2024-01-01 00:00:0{i}')
    all_uuids = db.get_all_uuids()
    assert set(uuids) == set(all_uuids)
    db.close()
    os.remove(db_path)

def test_delete():
    db, db_path = make_test_db()
    uuid = 'pytest-uuid-del'
    json_data = orjson.dumps({'uuid': uuid, 'pytest': True}).decode('utf-8')
    db.insert_or_replace(uuid, json_data, 'file.zip', 'artist', 'rel', '2024-01-01 00:00:00')
    assert db.get_by_uuid(uuid) is not None
    db.delete_by_uuid(uuid)
    assert db.get_by_uuid(uuid) is None
    db.close()
    os.remove(db_path) 