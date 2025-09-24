import json
import logging
from typing import Dict, Any, List, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
import torch

logger = logging.getLogger(__name__)

class QueryIntentService:
    """智能查询意图识别服务 - 基于LLM语义理解"""
    
    def __init__(self, model_path: str = "ai_models/Qwen2-1.5B-Instruct"):
        self.model_path = model_path
        self.tokenizer = None
        self.model = None
        self.generator = None
        self._load_model()
        
        # 定义查询意图类型和示例
        self.intent_definitions = {
            "count_query": {
                "description": "询问数量、统计信息",
                "examples": [
                    "有几台风机？", "风机数量是多少？", "总共有多少台风机？",
                    "有几个风场？", "风场数量", "多少条记录？"
                ],
                "keywords": ["几", "多少", "数量", "总数", "统计", "总共"]
            },
            "status_query": {
                "description": "询问状态、运行情况",
                "examples": [
                    "风机状态如何？", "有哪些风机在运行？", "故障的风机有哪些？",
                    "处于Watch状态的风机", "正常运行的风机"
                ],
                "keywords": ["状态", "运行", "故障", "正常", "异常", "维护", "Watch", "Normal"]
            },
            "list_query": {
                "description": "询问列表、清单信息",
                "examples": [
                    "有哪些风场？", "风机列表", "所有风机", "风场名称",
                    "风机型号有哪些？", "给我看看所有的风机"
                ],
                "keywords": ["哪些", "列表", "所有", "清单", "名称", "型号"]
            },
            "specific_info_query": {
                "description": "询问具体信息、详细内容",
                "examples": [
                    "处于Watch状态的风机叫什么？", "这台风机的详细信息",
                    "XX风机的型号是什么？", "风机的具体参数"
                ],
                "keywords": ["叫什么", "是什么", "详细", "具体", "信息", "参数", "名字"]
            },
            "time_related_query": {
                "description": "与时间相关的查询",
                "examples": [
                    "最近的记录", "今天的日志", "昨天有什么记录？",
                    "最新的维护记录", "近期的故障"
                ],
                "keywords": ["最近", "今天", "昨天", "最新", "近期", "历史"]
            },
            "technical_query": {
                "description": "技术问题、故障诊断、专业知识",
                "examples": [
                    "风机振动异常怎么处理？", "叶片结冰如何解决？",
                    "这个故障代码是什么意思？", "维护建议"
                ],
                "keywords": ["怎么", "如何", "为什么", "原因", "解决", "处理", "建议", "故障代码"]
            }
        }
    
    def _load_model(self):
        """加载模型"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
            
            self.generator = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                torch_dtype=torch.float16,
                device_map="auto"
            )
            
            logger.info("Query intent model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading query intent model: {e}")
            self.generator = None
    
    def analyze_query_intent(self, question: str) -> Dict[str, Any]:
        """分析查询意图"""
        try:
            # 构建分析提示
            prompt = self._build_intent_analysis_prompt(question)
            
            # 使用LLM分析
            if self.generator:
                response = self.generator(
                    prompt,
                    max_new_tokens=200,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                
                # 解析响应
                generated_text = response[0]['generated_text']
                analysis_result = self._parse_intent_response(generated_text, prompt)
                
            else:
                # 回退到关键词匹配
                analysis_result = self._fallback_keyword_analysis(question)
            
            # 提取实体信息
            entities = self._extract_entities(question)
            
            return {
                "intent": analysis_result.get("intent", "unknown"),
                "confidence": analysis_result.get("confidence", 0.5),
                "entities": entities,
                "reasoning": analysis_result.get("reasoning", ""),
                "original_question": question
            }
            
        except Exception as e:
            logger.error(f"Error analyzing query intent: {e}")
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "reasoning": f"分析出错: {str(e)}",
                "original_question": question
            }
    
    def _build_intent_analysis_prompt(self, question: str) -> str:
        """构建意图分析提示"""
        intent_descriptions = []
        for intent, info in self.intent_definitions.items():
            examples = "、".join(info["examples"][:3])
            intent_descriptions.append(f"- {intent}: {info['description']} (例如: {examples})")
        
        prompt = f"""你是一个智能查询意图分析助手。请分析用户问题的意图类型。

可用的意图类型：
{chr(10).join(intent_descriptions)}

用户问题: "{question}"

请分析这个问题属于哪种意图类型，并给出置信度(0-1)和理由。

回答格式（JSON）：
{{
    "intent": "意图类型",
    "confidence": 置信度,
    "reasoning": "分析理由"
}}

回答："""
        
        return prompt
    
    def _parse_intent_response(self, generated_text: str, prompt: str) -> Dict[str, Any]:
        """解析LLM的意图分析响应"""
        try:
            # 提取生成的部分
            response_part = generated_text[len(prompt):].strip()
            
            # 尝试解析JSON
            if "{" in response_part and "}" in response_part:
                json_start = response_part.find("{")
                json_end = response_part.rfind("}") + 1
                json_str = response_part[json_start:json_end]
                
                result = json.loads(json_str)
                
                # 验证意图类型
                if result.get("intent") not in self.intent_definitions:
                    result["intent"] = "unknown"
                
                return result
            
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
        
        # 回退到关键词分析
        return self._fallback_keyword_analysis(generated_text)
    
    def _fallback_keyword_analysis(self, question: str) -> Dict[str, Any]:
        """关键词回退分析"""
        question_lower = question.lower()
        
        # 计算每种意图的匹配分数
        intent_scores = {}
        
        for intent, info in self.intent_definitions.items():
            score = 0
            keyword_matches = 0
            
            # 关键词匹配
            for keyword in info["keywords"]:
                if keyword.lower() in question_lower:
                    keyword_matches += 1
                    score += 1
            
            # 示例相似度（简单的词汇重叠）
            for example in info["examples"]:
                example_words = set(example.lower().split())
                question_words = set(question_lower.split())
                overlap = len(example_words & question_words)
                if overlap > 0:
                    score += overlap * 0.5
            
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            max_score = intent_scores[best_intent]
            confidence = min(max_score / 5.0, 1.0)  # 归一化到0-1
            
            return {
                "intent": best_intent,
                "confidence": confidence,
                "reasoning": f"基于关键词匹配，得分: {max_score}"
            }
        
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "reasoning": "无法识别查询意图"
        }
    
    def _extract_entities(self, question: str) -> Dict[str, Any]:
        """提取实体信息"""
        entities = {}
        
        # 提取状态信息
        status_keywords = {
            "watch": ["watch", "监控", "观察"],
            "normal": ["normal", "正常", "运行"],
            "fault": ["fault", "故障", "异常", "错误"],
            "maintenance": ["maintenance", "维护", "检修", "保养"]
        }
        
        question_lower = question.lower()
        for status, keywords in status_keywords.items():
            for keyword in keywords:
                if keyword in question_lower:
                    entities["status"] = status
                    break
        
        # 提取风场信息
        import re
        farm_match = re.search(r'(\w+)风场', question)
        if farm_match:
            entities["farm_name"] = farm_match.group(1)
        
        # 提取风机编号
        turbine_match = re.search(r'(\w+)\s*(\w+)\s*[风机|机组]', question)
        if turbine_match:
            entities["turbine_farm"] = turbine_match.group(1)
            entities["turbine_unit"] = turbine_match.group(2)
        
        # 提取时间信息
        time_keywords = {
            "today": ["今天", "今日"],
            "yesterday": ["昨天", "昨日"],
            "recent": ["最近", "近期", "最新"],
            "this_week": ["本周", "这周"],
            "this_month": ["本月", "这个月"]
        }
        
        for period, keywords in time_keywords.items():
            for keyword in keywords:
                if keyword in question:
                    entities["time_period"] = period
                    break
        
        return entities
    
    def get_query_suggestions(self, intent: str) -> List[str]:
        """根据意图获取查询建议"""
        if intent in self.intent_definitions:
            return self.intent_definitions[intent]["examples"]
        return []