"""TripleVectorStore — 基于 FAISS 的三元组长期记忆向量库。

存储结构化三元组 {主语, 关系, 宾语} 及其重要性分数，
支持语义去重、容量管理和重要性淘汰。
"""

import os
import json
import pickle
import numpy as np
from typing import Dict, List, Tuple, Optional
from ..embedding.encoder import EmbeddingEncoder


class TripleVectorStore:
    """三元组向量库：FAISS IndexFlatIP + 重要性感知的容量管理。

    每个记忆条目为：
    {
        "id": int,
        "triple_text": str,         # "{主语} | {关系} | {宾语}"
        "subject": str,
        "relation": str,
        "object": str,
        "importance": int,          # 1-5
        "source_turn": int,         # 来源对话轮次
        "embedding": np.ndarray,    # 向量表示
    }
    """

    def __init__(
        self,
        encoder: EmbeddingEncoder,
        top_k: int = 5,
        capacity: int = 150,
        dedup_threshold: float = 0.90,
    ):
        self.encoder = encoder
        self.dim = encoder.dim
        self.top_k = top_k
        self.capacity = capacity
        self.dedup_threshold = dedup_threshold

        import faiss
        self._index = faiss.IndexFlatIP(self.dim)
        self._id_counter = 0
        self._entries: Dict[int, Dict] = {}  # doc_id -> entry dict

    # ── 公共接口 ──────────────────────────────────────────────────────

    def add_triple(
        self,
        subject: str,
        relation: str,
        obj: str,
        importance: int,
        source_turn: int,
    ) -> Optional[int]:
        """添加一条三元组记忆（含去重检查）。

        Args:
            subject: 主语
            relation: 关系
            obj: 宾语
            importance: 重要性分数 1-5
            source_turn: 来源对话轮次

        Returns:
            分配的 doc_id，若被去重则返回 None
        """
        triple_text = f"{subject} | {relation} | {obj}"

        # 精确去重：完全相同的三元组文本
        for entry in self._entries.values():
            if entry["triple_text"] == triple_text:
                return None

        # 语义去重：检查是否与已有记忆高度相似
        if self._index.ntotal > 0:
            query_vec = self.encoder.encode([triple_text])
            scores, indices = self._index.search(query_vec, 1)
            top_score = scores[0][0]
            if top_score >= self.dedup_threshold:
                return None

        # 写入向量库
        embedding = self.encoder.encode([triple_text])
        self._index.add(embedding)

        doc_id = self._id_counter
        self._entries[doc_id] = {
            "triple_text": triple_text,
            "subject": subject,
            "relation": relation,
            "object": obj,
            "importance": importance,
            "source_turn": source_turn,
        }
        self._id_counter += 1

        return doc_id

    def search(self, query: str) -> List[Dict]:
        """检索与查询相关的 top-k 三元组。

        Args:
            query: 查询文本（通常是当前用户输入）

        Returns:
            按相似度降序排列的三元组条目列表，
            每项含 subject, relation, object, importance
        """
        if self._index.ntotal == 0:
            return []

        query_vec = self.encoder.encode([query])
        scores, indices = self._index.search(query_vec, self.top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= self._id_counter:
                continue
            if idx in self._entries:
                entry = self._entries[idx]
                results.append({
                    "subject": entry["subject"],
                    "relation": entry["relation"],
                    "object": entry["object"],
                    "importance": entry["importance"],
                    "source_turn": entry["source_turn"],
                    "similarity": float(score),
                })

        return results

    def evict_lowest_importance(self) -> Optional[int]:
        """淘汰一条最低重要性的三元组。

        若存在多条同等最低分，淘汰最早写入的（source_turn 最小）。

        Returns:
            被淘汰的 doc_id，若库为空则返回 None
        """
        if not self._entries:
            return None

        # 找到最低重要性（同分取最早写入）
        worst_id = None
        worst_importance = 999
        worst_turn = 999999

        for doc_id, entry in self._entries.items():
            imp = entry["importance"]
            turn = entry["source_turn"]
            if imp < worst_importance or (imp == worst_importance and turn < worst_turn):
                worst_importance = imp
                worst_turn = turn
                worst_id = doc_id

        if worst_id is not None:
            self._remove_entry(worst_id)

        return worst_id

    def ensure_capacity(self) -> int:
        """检查容量，超出上限则逐条淘汰最低分直到回到容量内。

        Returns:
            本次淘汰的条目数
        """
        evicted = 0
        while len(self._entries) > self.capacity:
            self.evict_lowest_importance()
            evicted += 1
        return evicted

    def get_all_triples(self) -> List[Dict]:
        """获取所有存储的三元组（用于快照/导出）。"""
        return [
            {
                "id": doc_id,
                "subject": entry["subject"],
                "relation": entry["relation"],
                "object": entry["object"],
                "importance": entry["importance"],
                "source_turn": entry["source_turn"],
            }
            for doc_id, entry in sorted(self._entries.items())
        ]

    def reset(self) -> None:
        """清空所有数据。"""
        import faiss
        self._index = faiss.IndexFlatIP(self.dim)
        self._id_counter = 0
        self._entries.clear()

    def snapshot(self) -> Dict:
        """导出当前状态（用于日志）。"""
        return {
            "total_triples": len(self._entries),
            "capacity": self.capacity,
            "entries": self.get_all_triples(),
        }

    def save(self, directory: str) -> None:
        """持久化到磁盘。"""
        import faiss
        os.makedirs(directory, exist_ok=True)
        index_path = os.path.join(directory, "faiss.index.pkl")
        with open(index_path, "wb") as f:
            pickle.dump(faiss.serialize_index(self._index), f)
        meta_path = os.path.join(directory, "metadata.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "id_counter": self._id_counter,
                "entries": self._entries,
            }, f, ensure_ascii=False, indent=2)

    def load(self, directory: str) -> bool:
        """从磁盘加载。"""
        import faiss
        index_path = os.path.join(directory, "faiss.index.pkl")
        meta_path = os.path.join(directory, "metadata.json")
        if not os.path.exists(index_path) or not os.path.exists(meta_path):
            return False
        with open(index_path, "rb") as f:
            self._index = faiss.deserialize_index(pickle.load(f))
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self._id_counter = data["id_counter"]
            self._entries = {}
            for k, v in data["entries"].items():
                self._entries[int(k)] = v
        return True

    # ── 内部方法 ──────────────────────────────────────────────────────

    def _remove_entry(self, doc_id: int) -> None:
        """从向量库和条目表中移除一条记忆。

        注意：FAISS IndexFlatIP 不支持单条删除，因此采用就地重建策略。
        """
        if doc_id not in self._entries:
            return

        del self._entries[doc_id]

        # 重建索引（排除被删除的条目）
        import faiss
        new_index = faiss.IndexFlatIP(self.dim)

        remaining = sorted(self._entries.items())
        if remaining:
            texts = [e["triple_text"] for _, e in remaining]
            embeddings = self.encoder.encode(texts)
            new_index.add(embeddings)

        self._index = new_index
