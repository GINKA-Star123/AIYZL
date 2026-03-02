# AI记忆存储功能
import json
from datetime import datetime
import os

class MemoryManager:
    def __init__(self, memory_file=r'knowledge\Personal\memory.json',max_memory=200):
        self.memory_limit = max_memory
        self.memory_file = memory_file
        self.memory = self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_memory(self):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def add_memory(self,content:str, users:str = "银花", importance:float = 0.5):
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.memory.append({
            "user": users,
            "content": content,
            "time": time,
            "importance": importance
        })

        # 清理记忆，保持在限制范围内
        self.memory = sorted(self.memory, key=lambda x: x['importance'], reverse=True)[:self.memory_limit]
        self._save_memory()

    def recall_memory(self, user : str, limit = 5):
        return [m for m in self.memory if m['user'] == user][:limit]
    