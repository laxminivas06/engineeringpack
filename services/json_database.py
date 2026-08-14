import os
import json
import uuid
import threading
from typing import List, Dict, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

_file_lock = threading.RLock()


class JSONDatabase:

    def __init__(self, filename: str):
        if not filename.endswith('.json'):
            filename += '.json'
        self.filepath = os.path.join(DATA_DIR, filename)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        with _file_lock:
            if not os.path.exists(self.filepath):
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2)

    def read_all(self) -> List[Dict[str, Any]]:
        with _file_lock:
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []

    def write_all(self, data: List[Dict[str, Any]]) -> bool:
        with _file_lock:
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                return True
            except Exception as e:
                print(f"Error writing to {self.filepath}: {e}")
                return False

    def find_all(self, filter_func=None) -> List[Dict[str, Any]]:
        records = self.read_all()
        if filter_func is None:
            return records
        return [r for r in records if filter_func(r)]

    def find_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        records = self.read_all()
        for r in records:
            if str(r.get('id')) == str(record_id):
                return r
        return None

    def find_one(self, **kwargs) -> Optional[Dict[str, Any]]:
        records = self.read_all()
        for r in records:
            match = True
            for k, v in kwargs.items():
                if r.get(k) != v:
                    match = False
                    break
            if match:
                return r
        return None

    def create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with _file_lock:
            records = self.read_all()
            if 'id' not in record or not record['id']:
                record['id'] = uuid.uuid4().hex[:12]
            records.append(record)
            self.write_all(records)
            return record

    def update(self, record_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with _file_lock:
            records = self.read_all()
            for i, r in enumerate(records):
                if str(r.get('id')) == str(record_id):
                    records[i].update(updates)
                    self.write_all(records)
                    return records[i]
            return None

    def delete(self, record_id: str) -> bool:
        with _file_lock:
            records = self.read_all()
            new_records = [r for r in records if str(r.get('id')) != str(record_id)]
            if len(new_records) < len(records):
                self.write_all(new_records)
                return True
            return False

    def count(self, filter_func=None) -> int:
        return len(self.find_all(filter_func))
