"""
IDSet核心模块 - 使用SQLModel的极简实现
"""

from sqlmodel import SQLModel, Field, create_engine, Session, select
from nanoid import generate
from datetime import datetime
from typing import Set, Dict, Any, Optional


def new_id() -> str:
    """生成新ID，使用nanoid保持与原有规则一致"""
    return generate()


class Record(SQLModel, table=True):
    """记录模型"""
    __tablename__ = "records"

    uuid: str = Field(primary_key=True, default_factory=generate, max_length=21)
    file_name: Optional[str] = Field(default=None, max_length=512, index=True)
    artist: Optional[str] = Field(default=None, max_length=256, index=True)
    created_time: datetime = Field(default_factory=datetime.now, index=True)


class IDSet:
    """极简ID管理器 - 使用SQLModel"""

    def __init__(self, db_path: str = "ids.db"):
        """初始化"""
        db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(db_url)
        SQLModel.metadata.create_all(self.engine)
    
    def add(self, file_name: str = "", artist: str = "", **kwargs) -> str:
        """添加记录"""
        with Session(self.engine) as session:
            record = Record(
                file_name=file_name or None,
                artist=artist or None
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.uuid
    
    def get(self, uuid: str) -> Optional[Dict[str, Any]]:
        """获取记录"""
        with Session(self.engine) as session:
            record = session.get(Record, uuid)
            if record:
                return {
                    "uuid": record.uuid,
                    "file_name": record.file_name,
                    "artist": record.artist,
                    "created_time": record.created_time.isoformat()
                }
            return None
    
    def find(self, file_name: str = None, artist: str = None) -> list:
        """查找记录"""
        with Session(self.engine) as session:
            statement = select(Record)

            if file_name:
                statement = statement.where(Record.file_name.contains(file_name))

            if artist:
                statement = statement.where(Record.artist.contains(artist))

            records = session.exec(statement).all()

            return [
                {
                    "uuid": record.uuid,
                    "file_name": record.file_name,
                    "artist": record.artist,
                    "created_time": record.created_time.isoformat()
                }
                for record in records
            ]
    
    def update(self, uuid: str, **kwargs) -> bool:
        """更新记录"""
        with Session(self.engine) as session:
            record = session.get(Record, uuid)
            if not record:
                return False

            for key, value in kwargs.items():
                if key in ['file_name', 'artist'] and hasattr(record, key):
                    setattr(record, key, value)

            session.add(record)
            session.commit()
            return True
    
    def delete(self, uuid: str) -> bool:
        """删除记录"""
        with Session(self.engine) as session:
            record = session.get(Record, uuid)
            if record:
                session.delete(record)
                session.commit()
                return True
            return False

    def all_ids(self) -> Set[str]:
        """获取所有ID"""
        with Session(self.engine) as session:
            statement = select(Record.uuid)
            results = session.exec(statement).all()
            return set(results)

    def count(self) -> int:
        """记录总数"""
        with Session(self.engine) as session:
            statement = select(Record)
            results = session.exec(statement).all()
            return len(results)
