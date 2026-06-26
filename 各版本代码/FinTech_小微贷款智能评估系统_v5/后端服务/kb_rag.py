"""
v5 RAG 语义检索引擎 — ChromaDB + sentence-transformers
替代 kb_bridge 中的关键词匹配，实现向量语义搜索。
"""

import os
import json
from pathlib import Path
from typing import Optional

# 延迟加载（避免未安装时阻塞启动）
_chroma_client = None
_embedding_fn = None
_COLLECTION_NAME = "fintech_kb_v5"

KB_DATA = Path(__file__).resolve().parent.parent.parent / "kb" / "data"
CHROMA_PATH = Path(__file__).resolve().parent / "chroma_db"


def _ensure_chroma():
    global _chroma_client, _embedding_fn
    if _chroma_client is not None:
        return True
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        # 使用轻量中文友好的嵌入模型
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        return True
    except ImportError:
        print("[RAG] chromadb 未安装，语义搜索不可用。pip install chromadb sentence-transformers")
        return False
    except Exception as e:
        print(f"[RAG] 初始化失败: {e}")
        return False


def build_index(force_rebuild: bool = False) -> int:
    """
    构建/重建知识库向量索引。
    遍历 kb/data/ 下所有政策、案例、银行产品，生成 embedding 存入 ChromaDB。
    返回索引的文档数量。
    """
    if not _ensure_chroma():
        return 0

    collection = _chroma_client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=_embedding_fn,
    )

    # 如果已存在且不强制重建，跳过
    existing = collection.count()
    if existing > 0 and not force_rebuild:
        print(f"[RAG] 索引已存在 ({existing} 条文档)，跳过构建。force_rebuild=True 可强制重建。")
        return existing

    # 清空重建
    if force_rebuild:
        _chroma_client.delete_collection(_COLLECTION_NAME)
        collection = _chroma_client.create_collection(
            name=_COLLECTION_NAME,
            embedding_function=_embedding_fn,
        )

    ids, documents, metadatas = [], [], []

    def add_docs(doc_list: list[dict], doc_type: str, text_fields: list[str]):
        for i, item in enumerate(doc_list):
            text = " | ".join(str(item.get(f, "")) for f in text_fields if item.get(f))
            if not text.strip():
                continue
            doc_id = f"{doc_type}-{i}-{item.get('case_id', item.get('rule_id', item.get('id', i)))}"
            ids.append(doc_id)
            documents.append(text)
            metadatas.append({"type": doc_type, **{k: str(v)[:200] for k, v in item.items() if k not in text_fields}})

    # 1. 政策规则
    for csv_name in ["national_policies.csv", "provincial_policies.csv"]:
        rows = _read_csv_safe(f"policies/{csv_name}")
        add_docs(rows, "policy", ["document_title", "summary", "key_condition", "applicable_object", "agent_usage"])

    # 2. 银行产品
    bank_json = _read_json_safe("banks/bank_products.json")
    if bank_json:
        banks = bank_json.get("banks", [])
        add_docs(banks, "bank", ["name", "type", "product_name", "target_enterprise", "loan_type"])

    # 3. 教学案例
    for csv_name in ["teaching_cases_basic.csv", "teaching_cases_enhanced.csv"]:
        rows = _read_csv_safe(f"cases/{csv_name}")
        add_docs(rows, "case", ["industry", "scenario", "result", "reason", "diagnosis_chain", "improvement_advice"])

    # 4. 行业准入
    rows = _read_csv_safe("industries/industry_acceptance.csv")
    add_docs(rows, "industry", ["行业名称", "准入等级", "说明"])

    # 5. 补贴政策
    rows = _read_csv_safe("risk_control/subsidy_policies.csv")
    add_docs(rows, "subsidy", ["category", "subsidy_content", "amount_range", "application_condition"])

    # 6. 被拒因子
    rows = _read_csv_safe("risk_control/rejection_factors.csv")
    add_docs(rows, "rejection", ["factor", "estimated_percentage", "description"])

    # 批量写入 ChromaDB
    if ids:
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.add(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
            )
    print(f"[RAG] 索引构建完成，共 {len(ids)} 条文档。")
    return len(ids)


def semantic_search(query: str, top_n: int = 5, doc_type: str = "") -> list[dict]:
    """
    语义搜索知识库。
    - query: 自然语言查询
    - top_n: 返回条数
    - doc_type: 过滤文档类型 (policy/bank/case/industry/subsidy，留空=全部)
    """
    if not _ensure_chroma():
        return []

    try:
        collection = _chroma_client.get_collection(
            name=_COLLECTION_NAME,
            embedding_function=_embedding_fn,
        )
    except Exception:
        # 索引不存在，尝试构建
        count = build_index()
        if count == 0:
            return []
        collection = _chroma_client.get_collection(
            name=_COLLECTION_NAME,
            embedding_function=_embedding_fn,
        )

    where_filter = {"type": doc_type} if doc_type else None
    results = collection.query(
        query_texts=[query],
        n_results=top_n,
        where=where_filter,
    )

    output = []
    if results["ids"] and results["ids"][0]:
        for i, doc_id in enumerate(results["ids"][0]):
            output.append({
                "id": doc_id,
                "content": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
    return output


def is_available() -> bool:
    return _ensure_chroma()


# ============================================================
# 辅助读取（同 kb_bridge 逻辑，独立一份避免循环引用）
# ============================================================
def _read_csv_safe(relative_path: str) -> list[dict]:
    path = KB_DATA / relative_path
    if not path.exists():
        # 尝试递归查找
        for root, dirs, files in os.walk(str(KB_DATA)):
            if Path(relative_path).name in files:
                path = Path(root) / Path(relative_path).name
                break
    if not path.exists():
        return []
    import csv
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {}
                for k, v in row.items():
                    if k and k.strip():
                        cleaned[k.strip()] = (v.strip() if v else "")
                rows.append(cleaned)
    except Exception:
        pass
    return rows


def _read_json_safe(relative_path: str) -> Optional[dict]:
    path = KB_DATA / relative_path
    if not path.exists():
        for root, dirs, files in os.walk(str(KB_DATA)):
            if Path(relative_path).name in files:
                path = Path(root) / Path(relative_path).name
                break
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
