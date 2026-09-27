import os
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class SemanticMemory:
    """语义记忆：向量检索，用于 RAG"""

    def __init__(
        self,
        persist_dir: str = "./data/chroma",
        collection_name: str = "semantic",
        embed_model_name: str = "BAAI/bge-small-zh-v1.5",
    ):
        """
        初始化

        Args:
            persist_dir: ChromaDB 持久化目录
            collection_name: collection 名
            embed_model_name: 嵌入模型名
        """
        import chromadb
        from sentence_transformers import SentenceTransformer

        os.makedirs(persist_dir, exist_ok=True)

        # ChromaDB 持久化客户端
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # 嵌入模型
        self.embed_model = SentenceTransformer(embed_model_name)

        logger.info(f"[semantic] 初始化完成：{persist_dir} / {collection_name}")

    def _split_text(self, text: str, max_len: int = 500) -> List[str]:
        """
        切分文本

        Args:
            text: 原始文本
            max_len: 每段最大长度

        Returns:
            段落列表
        """
        if not text:
            return []

        # 1. 按空行切
        raw_chunks = [c.strip() for c in text.split("\n\n") if c.strip()]

        # 2. 超长再切
        chunks = []
        for c in raw_chunks:
            if len(c) <= max_len:
                if len(c) >= 10:
                    chunks.append(c)
            else:
                for i in range(0, len(c), max_len):
                    sub = c[i:i + max_len].strip()
                    if len(sub) >= 10:
                        chunks.append(sub)

        return chunks

    def add_document(
        self,
        user_id: str,
        doc_id: str,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        添加文档（自动切段 + 嵌入 + 存储）

        Args:
            user_id: 用户 ID
            doc_id: 文档 ID（如文件名、研报 ID）
            text: 文档内容
            metadata: 额外 metadata（可选）
        """
        chunks = self._split_text(text)
        if not chunks:
            logger.warning(f"[semantic] 文档为空，跳过：{doc_id}")
            return

        # 编码
        embeddings = self.embed_model.encode(
            chunks, normalize_embeddings=True
        ).tolist()

        # 构造 IDs 和 metadata
        ids = [f"{user_id}::{doc_id}::{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "user_id": user_id,
                "doc_id": doc_id,
                "chunk_index": i,
                **(metadata or {}),
            }
            for i in range(len(chunks))
        ]

        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"[semantic] 添加文档 {doc_id}：{len(chunks)} 段")

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> List[Dict]:
        """
        检索

        Args:
            user_id: 用户 ID
            query: 查询文本
            top_k: 返回条数

        Returns:
            [{"text": "...", "doc_id": "...", "distance": 0.23}, ...]
        """
        if not query:
            return []

        query_vec = self.embed_model.encode(
            [query], normalize_embeddings=True
        ).tolist()

        results = self.collection.query(
            query_embeddings=query_vec,
            n_results=top_k,
            where={"user_id": user_id},
        )

        out = []
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0] if results.get("distances") else [None] * len(docs)
            for doc, meta, dist in zip(docs, metas, dists):
                out.append({
                    "text": doc,
                    "doc_id": meta.get("doc_id", ""),
                    "distance": round(dist, 4) if dist is not None else None,
                })

        logger.info(f"[semantic] 检索 '{query[:30]}'：返回 {len(out)} 段")
        return out

    def delete_document(self, user_id: str, doc_id: str) -> None:
        """
        删除某用户的某文档

        Args:
            user_id: 用户 ID
            doc_id: 文档 ID
        """
        self.collection.delete(
            where={"$and": [{"user_id": user_id}, {"doc_id": doc_id}]}
        )
        logger.info(f"[semantic] 删除文档 {doc_id}（user={user_id}）")

    def clear(self, user_id: Optional[str] = None) -> None:
        """
        清空

        Args:
            user_id: 为空清空整个 collection，否则只清该用户的
        """
        if user_id:
            self.collection.delete(where={"user_id": user_id})
            logger.info(f"[semantic] 清空用户 {user_id} 的记忆")
        else:
            # 删掉整个 collection 再重建
            self.client.delete_collection(self.collection.name)
            self.collection = self.client.get_or_create_collection(
                name="semantic",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("[semantic] 清空整个 collection")


# ========================================
# 测试用
# ========================================
if __name__ == "__main__":
    import tempfile, shutil

    tmp_dir = tempfile.mkdtemp()
    try:
        sm = SemanticMemory(persist_dir=tmp_dir)

        # 添加两个文档
        sm.add_document(
            "u1", "report_aapl",
            "苹果公司 2024 年营收 3832 亿美元，净利润 970 亿，毛利率 46%。\n\n"
            "苹果在 AI 领域持续投入，预计 2025 年推出更多 AI 功能。"
        )
        sm.add_document(
            "u1", "report_tsla",
            "特斯拉 2024 年营收 967 亿美元，净利润 150 亿，毛利率 18%。\n\n"
            "特斯拉上海工厂产能持续提升，但竞争加剧。"
        )
        sm.add_document(
            "u2", "report_aapl",
            "另一个用户的文档，不应该被 u1 检索到。"
        )

        # 检索
        print("=== 检索 '苹果的毛利率' ===")
        for r in sm.search("u1", "苹果的毛利率", top_k=2):
            print(f"  [{r['doc_id']}] {r['text'][:50]}... (dist={r['distance']})")

        print("\n=== 检索 '特斯拉产能' ===")
        for r in sm.search("u1", "特斯拉产能", top_k=2):
            print(f"  [{r['doc_id']}] {r['text'][:50]}... (dist={r['distance']})")

        # 验证隔离
        print("\n=== 验证隔离：u2 检索 ===")
        r2 = sm.search("u2", "苹果", top_k=5)
        print(f"  u2 检索到 {len(r2)} 段，文档：{[r['doc_id'] for r in r2]}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
