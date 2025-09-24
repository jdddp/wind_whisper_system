from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class RAGQuery(BaseModel):
    question: str
    turbine_id: Optional[str] = None  # 可选：限制查询特定风机
    max_results: int = 5

class RAGSource(BaseModel):
    log_id: str
    chunk_text: str
    similarity_score: float
    turbine_info: str
    published_at: str

class RAGResponse(BaseModel):
    answer: str
    sources: List[RAGSource]
    query_time: float
    query_type: Optional[str] = "document_search"  # 查询类型：database_query, document_search等
    metadata: Optional[Dict[str, Any]] = {}  # 额外的元数据信息