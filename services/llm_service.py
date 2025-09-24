import os
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from typing import List, Dict, Any
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from config.settings import get_settings

logger = logging.getLogger(__name__)

class LLMService:
    """大语言模型服务 - 使用Hugging Face免费模型"""
    
    def __init__(self):
        """初始化LLM服务"""
        # 获取配置
        self.settings = get_settings()
        
        # 设置离线模式
        if self.settings.ai_model.transformers_offline:
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
        
        # 优先使用工程目录下的本地模型路径
        if os.path.exists(self.settings.ai_model.llm_local_path):
            self.model_name = self.settings.ai_model.llm_local_path
        else:
            self.model_name = self.settings.ai_model.llm_model_name  
        
        # 检测GPU可用性并设置设备
        if torch.cuda.is_available():
            self.device = "cuda"
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
        else:
            self.device = "cpu"
            logger.info("GPU not available, using CPU")
        self.model = None
        self.tokenizer = None
        self.generator = None
        self.executor = ThreadPoolExecutor(max_workers=2)  # 创建线程池
        
        try:
            logger.info(f"Loading model {self.model_name} on {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name, 
                trust_remote_code=True,
                local_files_only=True
            )
            # 根据设备选择合适的数据类型
            if self.device == "cuda":
                torch_dtype = torch.float16  # GPU使用float16节省显存
                device_map = "auto"
            else:
                torch_dtype = torch.float32  # CPU使用float32
                device_map = None
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch_dtype,
                trust_remote_code=True,
                local_files_only=True,
                device_map=device_map
            )
            
            # 如果是CPU模式，手动移动模型到设备
            if self.device == "cpu":
                self.model = self.model.to(self.device)
            
            # 创建文本生成pipeline
            # 当使用device_map="auto"时，不能指定device参数
            if device_map == "auto":
                self.generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    torch_dtype=torch_dtype
                )
            else:
                device_id = 0 if self.device == "cuda" else -1
                self.generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=device_id,
                    torch_dtype=torch_dtype
                )
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.info("Falling back to CPU-only smaller model")
            try:
                # 回退到更小的模型
                fallback_model = "microsoft/DialoGPT-medium"
                self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
                self.model = AutoModelForCausalLM.from_pretrained(fallback_model)
                self.generator = pipeline(
                    "text-generation",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    device=-1
                )
                logger.info(f"Fallback model {fallback_model} loaded")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
                self.generator = None
    
    @property
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self.generator is not None
    
    async def generate_summary(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        生成文本摘要
        
        Args:
            text: 需要摘要的文本
            context: 上下文信息，包含风机信息等
            
        Returns:
            生成的摘要
        """
        if not self.generator:
            return text[:200] + "..." if len(text) > 200 else text
        
        try:
            context_info = ""
            if context:
                turbine_info = context.get("turbine_info", "")
                if turbine_info:
                    context_info = f"风机信息：{turbine_info}\n\n"
            
            prompt = f"""请为以下风机监测记录生成简洁的摘要，要求：
1. 突出关键信息和异常情况
2. 保持专业术语的准确性
3. 控制在100字以内
4. 如果涉及具体部件或现象，请明确指出

{context_info}原始记录：
{text}

摘要："""

            # 在线程池中运行同步的生成函数
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.generator(
                    prompt,
                    max_length=len(prompt.split()) + 100,
                    num_return_sequences=1,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            generated_text = response[0]['generated_text']
            # 提取摘要部分（去掉原始prompt）
            summary = generated_text[len(prompt):].strip()
            
            # 如果生成的文本太长，截取前200字符
            if len(summary) > 200:
                summary = summary[:200] + "..."
                
            return summary if summary else text[:200] + "..." if len(text) > 200 else text
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # 回退到简单截取
            return text[:200] + "..." if len(text) > 200 else text
    
    async def generate_tags(self, text: str, summary: str = None) -> Dict[str, Any]:
        """
        生成标签和分类
        
        Args:
            text: 原始文本
            summary: 文本摘要（可选）
            
        Returns:
            包含标签和分类信息的字典
        """
        if not self.generator:
            return {
                "tags": ["监测记录"],
                "category": "其他",
                "severity": "正常",
                "components": []
            }
        
        try:
            content = summary if summary else text
            
            prompt = f"""请分析以下风机监测记录，提取关键信息并生成标签。

监测记录：
{content}

请按以下格式返回JSON：
{{
    "tags": ["标签1", "标签2", "标签3"],
    "category": "故障/维护/检查/其他",
    "severity": "正常/轻微/中等/严重/紧急",
    "components": ["涉及的部件1", "涉及的部件2"]
}}

要求：
1. tags包含3-5个关键标签
2. category从给定选项中选择
3. severity评估问题严重程度
4. components列出涉及的风机部件

JSON："""

            # 在线程池中运行同步的生成函数
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.generator(
                    prompt,
                    max_length=len(prompt.split()) + 150,
                    num_return_sequences=1,
                    temperature=0.2,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            generated_text = response[0]['generated_text']
            result_text = generated_text[len(prompt):].strip()
            
            # 尝试解析JSON
            import json
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回默认值
                logger.warning(f"Failed to parse JSON response: {result_text}")
                return {
                    "tags": ["监测记录"],
                    "category": "其他",
                    "severity": "正常",
                    "components": []
                }
                
        except Exception as e:
            logger.error(f"Error generating tags: {e}")
            return {
                "tags": ["监测记录"],
                "category": "其他", 
                "severity": "正常",
                "components": []
            }
    
    async def answer_question(self, question: str, context_chunks: List[Dict[str, Any]]) -> str:
        """
        基于上下文回答问题
        
        Args:
            question: 用户问题
            context_chunks: 相关的上下文片段
            
        Returns:
            生成的答案
        """
        if not self.generator:
            return "抱歉，LLM服务未配置，无法回答问题。"
        
        try:
            # 构建上下文
            context_text = ""
            for i, chunk in enumerate(context_chunks[:5]):  # 最多使用5个片段
                content = chunk.get('content', '')
                source = chunk.get('source', '未知来源')
                context_text += f"[片段{i+1}] 来源：{source}\n内容：{content}\n\n"
            
            if not context_text.strip():
                return "抱歉，没有找到相关的上下文信息来回答您的问题。"
            
            prompt = f"""你是一个专业的风机运维专家，请基于以下上下文信息回答用户问题。

上下文信息：
{context_text}

用户问题：{question}

回答要求：
1. 基于上下文信息提供准确、专业的回答
2. 如果涉及多台风机，请分别说明每台风机的情况
3. 突出关键的技术信息和运维建议
4. 如果上下文信息不足，请明确说明并建议获取更多信息
5. 使用专业术语但保持表达清晰易懂

专业回答："""

            # 在线程池中运行同步的生成函数
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.generator(
                    prompt,
                    max_length=len(prompt.split()) + 200,
                    num_return_sequences=1,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            generated_text = response[0]['generated_text']
            answer = generated_text[len(prompt):].strip()
            
            # 如果生成的答案太长，截取合理长度
            if len(answer) > 1000:
                answer = answer[:1000] + "..."
                
            return answer if answer else "抱歉，无法基于当前上下文生成合适的回答。"
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            return f"抱歉，生成答案时出现错误：{str(e)}"
    
    async def generate_response(self, prompt: str, max_tokens: int = 500) -> Dict[str, Any]:
        """
        生成响应内容
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数量
            
        Returns:
            Dict包含生成的内容、成功状态和错误信息
        """
        if not self.generator:
            return {
                "content": "LLM服务当前不可用",
                "success": False,
                "error": "LLM service not available"
            }
        
        try:
            # 在线程池中运行同步的生成函数
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.generator(
                    prompt,
                    max_length=len(prompt.split()) + max_tokens,
                    num_return_sequences=1,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            )
            
            generated_text = response[0]['generated_text']
            # 提取生成的部分（去掉原始prompt）
            content = generated_text[len(prompt):].strip()
            
            return {
                "content": content if content else "生成内容为空",
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "content": f"生成响应时出现错误: {str(e)}",
                "success": False,
                "error": str(e)
            }
    
    def _generate_sync_response(self, prompt: str, max_tokens: int = 500) -> str:
        """
        同步生成响应内容（用于线程池执行）
        
        Args:
            prompt: 输入提示词
            max_tokens: 最大生成token数量
            
        Returns:
            生成的文本内容
        """
        if not self.generator:
            return "LLM服务未初始化"
        
        try:
            response = self.generator(
                prompt,
                max_length=len(prompt.split()) + max_tokens,
                num_return_sequences=1,
                temperature=0.3,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id if self.tokenizer else None
            )
            
            generated_text = response[0]['generated_text']
            # 提取生成的部分（去掉原始prompt）
            content = generated_text[len(prompt):].strip()
            
            return content if content else "生成内容为空"
            
        except Exception as e:
            logger.error(f"Error in sync response generation: {e}")
            return f"同步生成响应时出现错误: {str(e)}"