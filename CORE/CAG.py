from datetime import datetime
from datetime import timedelta
from sentence_transformers import SentenceTransformer
import numpy as np
import threading
import faiss

class sentenceSimilarityTest:
    def __init__(
        self, 
        model="BAAI/bge-small-zh-v1.5", #模型路径
        similarity_threshold=0.85,  #语义相似度阈值
        cache_size=3000,  #缓存大小，用于存储已计算的相似度矩阵
        ttl_hours : int = 24,  #缓存过期时间，单位：小时
        ):
        self.model = model
        self.similarity_threshold = similarity_threshold
        # === 1.初始化 ====

        self.encoder = SentenceTransformer(model)
        self.encoder.max_sequence_length = 128  #限制长度加速计算


        # === 2.faiss索引 ====
        self.dim = self.encoder.get_sentence_embedding_dimension()
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dim))  #内积即相似度
        
        # ===3.缓存 ====
        self.cache = {}   # {id: {"query": str, "response": str, "ts": datetime}}
        self.id_counter = 0
        self.similarity_threshold = similarity_threshold
        self.lock = threading.Lock()
        self.cache_size = cache_size
        self.ttl_hours = timedelta(hours=ttl_hours)

        # ===4.预启动 ===
        self._preload_common_qa()
    


    # 核心API：查询缓存
    def query_cache(self, query: str) -> str:
        """
        查询缓存中是否有与查询相关的缓存项
        """

        # Step1：将查询转换为向量
        query_embedding = self.encoder.encode(query,convert_to_numpy=True)
        query_embedding = query_embedding/np.linalg.norm(query_embedding)  #归一化

        # Step2: Faiss索引查询
        if self.index.total_elements == 0:
            return None
        scores, ids =self.index.search(query_embedding.astype(np.float32), k=1)
        sim_score = scores[0][0]

        # Step3: 检查相似度是否超过阈值

        if sim_score < self.similarity_threshold:
            return None
        else:
            cache_id = int(ids[0][0])
            with self.lock:
                if cache_id in self.cache:
                    entry = self.cache[cache_id]
                    if(datetime.now() - entry["ts"] < self.ttl_hours):
                        return True,entry["response"],sim_score

    # 核心API2：写入缓存中
    def add(self, user_input: str, response: str):
        """将新问答对加入缓存"""
        with self.lock:
            # 防止重复存储（相似度>0.95视为重复）
            if self.index.ntotal > 0:
                emb = self.encoder.encode([user_input], convert_to_numpy=True)
                emb = emb / np.linalg.norm(emb)
                scores, ids = self.index.search(emb.astype('float32'), k=1)
                if scores[0][0] >= 0.95:
                    cid = int(ids[0][0])
                    self.cache[cid]["response"] = response
                    self.cache[cid]["timestamp"] = datetime.now()
                    return
            
            # 新增缓存项
            emb = self.encoder.encode([user_input], convert_to_numpy=True)
            emb = emb / np.linalg.norm(emb)
            cache_id = self.id_counter
            
            self.cache[cache_id] = {
                "query": user_input,
                "response": response,
                "timestamp": datetime.now()
            }
            self.index.add_with_ids(emb.astype('float32'), np.array([cache_id]))
            self.id_counter += 1
            
            # 超量淘汰（LRU）
            if len(self.cache) > 3000:
                oldest = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
                del self.cache[oldest]
                self.index.remove_ids(np.array([oldest]))
            
    #────────────────────────────────────────────────
    # 辅助：预热直播常见问题（启动即命中）
    # ────────────────────────────────────────────────
    def _preload_common_qa(self):
        """预加载50条高频QA，直播开始即享受缓存加速"""
        common_qa = [
            ("你好", "呐~你好呀！我是乐正绫，今天也要元气满满♪"),
            ("你是谁", "我是乐正绫哦！16岁的女高中生，也是乐队主唱兼吉他手~"),
            ("唱首歌", "诶嘿~想听我唱歌吗？那我清唱一小段给你听♪"),
            ("喜欢什么", "最喜欢音乐和巨大的毛绒玩具啦！软乎乎的好想rua~"),
            ("天依在哪", "天依刚刚还在呢！我们经常一起唱歌玩耍的~"),
            # ... 共50条
        ]
        for q, a in common_qa:
            self.add(q, a)
        print(f"✓ 预热 {len(common_qa)} 条高频QA")
