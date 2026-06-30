import json
from pathlib import Path
from typing import Any

from bson import ObjectId
import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from utils import settings

client: AsyncIOMotorClient | None = None
mongo_error: str | None = None
using_local_fallback = False
LOCAL_DB_PATH = Path('local_db.json')
COLLECTIONS = ['documents', 'chunks', 'chat_history', 'settings', 'feedback']

class InsertOneResult:
    def __init__(self, inserted_id: str):
        self.inserted_id = inserted_id

class UpdateResult:
    def __init__(self, modified_count: int):
        self.modified_count = modified_count

class LocalCursor:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.index = 0

    def sort(self, field: str, direction: int):
        reverse = direction < 0
        self.rows.sort(key=lambda row: str(row.get(field, '')), reverse=reverse)
        return self

    def limit(self, count: int):
        self.rows = self.rows[:count]
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.rows):
            raise StopAsyncIteration
        row = dict(self.rows[self.index])
        self.index += 1
        return row

class LocalCollection:
    def __init__(self, name: str):
        self.name = name

    async def create_index(self, _: str) -> None:
        return None

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        if not LOCAL_DB_PATH.exists():
            return {name: [] for name in COLLECTIONS}
        data = json.loads(LOCAL_DB_PATH.read_text(encoding='utf-8'))
        for name in COLLECTIONS:
            data.setdefault(name, [])
        return data

    def _save(self, data: dict[str, list[dict[str, Any]]]) -> None:
        LOCAL_DB_PATH.write_text(json.dumps(data, default=str, indent=2), encoding='utf-8')

    def _matches(self, row: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, expected in (query or {}).items():
            actual = row.get(key)
            if key == '_id':
                if str(actual) != str(expected):
                    return False
            elif isinstance(expected, dict) and '$in' in expected:
                if actual not in expected['$in']:
                    return False
            elif actual != expected:
                return False
        return True

    async def insert_one(self, record: dict[str, Any]) -> InsertOneResult:
        data = self._load()
        row = dict(record)
        row['_id'] = str(ObjectId())
        data.setdefault(self.name, []).append(row)
        self._save(data)
        return InsertOneResult(row['_id'])

    async def insert_many(self, records: list[dict[str, Any]]) -> None:
        data = self._load()
        data.setdefault(self.name, []).extend(dict(record) for record in records)
        self._save(data)

    def find(self, query: dict[str, Any] | None = None) -> LocalCursor:
        data = self._load()
        rows = [dict(row) for row in data.get(self.name, []) if self._matches(row, query or {})]
        return LocalCursor(rows)

    async def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        data = self._load()
        for row in data.get(self.name, []):
            if self._matches(row, query):
                return dict(row)
        return None

    async def update_one(self, query: dict[str, Any], update: dict[str, Any], upsert: bool = False) -> UpdateResult:
        data = self._load()
        rows = data.setdefault(self.name, [])
        for row in rows:
            if self._matches(row, query):
                if '$set' in update:
                    row.update(update['$set'])
                self._save(data)
                return UpdateResult(1)
        if upsert:
            new_row = dict(query)
            if '$set' in update:
                new_row.update(update['$set'])
            new_row['_id'] = str(ObjectId())
            rows.append(new_row)
            self._save(data)
            return UpdateResult(1)
        return UpdateResult(0)

    async def update_many(self, query: dict[str, Any], update: dict[str, Any]) -> UpdateResult:
        data = self._load()
        modified = 0
        for row in data.get(self.name, []):
            if self._matches(row, query):
                if '$set' in update:
                    row.update(update['$set'])
                modified += 1
        self._save(data)
        return UpdateResult(modified)

    async def delete_one(self, query: dict[str, Any]) -> None:
        data = self._load()
        rows = data.get(self.name, [])
        removed = False
        kept = []
        for row in rows:
            if not removed and self._matches(row, query):
                removed = True
                continue
            kept.append(row)
        data[self.name] = kept
        self._save(data)

    async def delete_many(self, query: dict[str, Any]) -> None:
        data = self._load()
        data[self.name] = [row for row in data.get(self.name, []) if not self._matches(row, query)]
        self._save(data)

    async def count_documents(self, query: dict[str, Any] | None = None) -> int:
        data = self._load()
        return len([row for row in data.get(self.name, []) if self._matches(row, query or {})])

class LocalDatabase:
    def __init__(self):
        self.documents = LocalCollection('documents')
        self.chunks = LocalCollection('chunks')
        self.chat_history = LocalCollection('chat_history')
        self.settings = LocalCollection('settings')
        self.feedback = LocalCollection('feedback')

local_database = LocalDatabase()

async def connect_to_mongo() -> None:
    global client, mongo_error, using_local_fallback
    if '<username>' in settings.mongodb_uri or '<cluster-url>' in settings.mongodb_uri:
        mongo_error = 'MongoDB Atlas URI is still using placeholder values in backend/.env'
        client = None
        using_local_fallback = True
        return
    try:
        client = AsyncIOMotorClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=20000,
            connectTimeoutMS=20000,
            socketTimeoutMS=20000,
            tls=True,
            tlsCAFile=certifi.where(),
            tlsAllowInvalidCertificates=True,
        )
        await client.admin.command('ping')
        db = client[settings.mongodb_db]
        for collection, index in [('documents', 'created_at'), ('chat_history', 'created_at'), ('chunks', 'document_id'), ('feedback', 'chat_id')]:
            await getattr(db, collection).create_index(index)
        mongo_error = None
        using_local_fallback = False
        print('MongoDB Atlas connected')
    except Exception as exc:
        client = None
        mongo_error = str(exc)
        using_local_fallback = True
        print(f'MongoDB Atlas unavailable, using local_db.json fallback: {mongo_error}')

async def close_mongo_connection() -> None:
    global client
    if client is not None:
        client.close()
        client = None

def get_database() -> AsyncIOMotorDatabase | LocalDatabase:
    if client is None:
        return local_database
    return client[settings.mongodb_db]
