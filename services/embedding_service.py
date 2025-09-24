import os
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Union
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """文本嵌入服务"""
    
    def __init__(self, model_name: str = None):
        """
        初始化嵌入服务
        Args:
            model_name: 嵌入模型名称，默认使用配置文件中的设置
        """
        # 获取配置
        self.settings = get_settings()
        
        # 设置离线模式
        if self.settings.ai_model.transformers_offline:
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
        if self.settings.ai_model.hf_hub_offline:
            os.environ['HF_HUB_OFFLINE'] = '1'
        
        # 优先使用工程目录下的本地模型路径
        if model_name is None and os.path.exists(self.settings.ai_model.embedding_local_path):
            self.model_name = self.settings.ai_model.embedding_local_path
        else:
            self.model_name = model_name or self.settings.ai_model.embedding_model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载嵌入模型"""
        try:
            import torch
            logger.info(f"Loading embedding model: {self.model_name}")
            
            # 检查GPU可用性
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            
            # 确保使用本地文件
            if os.path.exists(self.model_name):
                self.model = SentenceTransformer(self.model_name, local_files_only=True, device=device)
            else:
                self.model = SentenceTransformer(self.model_name, device=device)
            
            logger.info(f"Embedding model loaded successfully on {device}")
            if torch.cuda.is_available():
                logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            # 如果无法加载主模型，尝试使用简单的向量化方法
            logger.warning("Embedding model failed to load, will use fallback method")
            self.model = None
    
    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        将文本编码为向量
        Args:
            texts: 单个文本或文本列表
        Returns:
            嵌入向量数组
        """
        if isinstance(texts, str):
            texts = [texts]
        
        if self.model is None:
            # 使用简单的TF-IDF向量化作为fallback
            return self._fallback_encode(texts)
        
        try:
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            logger.warning("Using fallback encoding method")
            return self._fallback_encode(texts)
    
    def _fallback_encode(self, texts: List[str]) -> np.ndarray:
        """
        Fallback编码方法，使用简单的词频向量
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        import jieba
        
        # 中文分词
        processed_texts = []
        for text in texts:
            words = jieba.lcut(text)
            processed_texts.append(' '.join(words))
        
        # 使用TF-IDF向量化
        vectorizer = TfidfVectorizer(max_features=384, stop_words=None)
        try:
            embeddings = vectorizer.fit_transform(processed_texts).toarray()
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error(f"Fallback encoding failed: {e}")
            # 最后的fallback：返回随机向量
            return np.random.rand(len(texts), 384).astype(np.float32)
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        异步获取单个文本的嵌入向量
        Args:
            text: 输入文本
        Returns:
            嵌入向量列表
        """
        embedding = self.encode(text)
        if isinstance(embedding, np.ndarray):
            if embedding.ndim == 2:
                return embedding[0].tolist()
            else:
                return embedding.tolist()
        return embedding

    def get_embedding_dimension(self) -> int:
        """获取嵌入向量维度"""
        # 测试编码一个简单文本来获取维度
        test_embedding = self.encode("test")
        return test_embedding.shape[-1]