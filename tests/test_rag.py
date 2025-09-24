#!/usr/bin/env python3
"""
RAG (检索增强生成) 功能测试模块
测试文档上传、向量检索、智能问答等功能
端口: 从配置文件获取
"""

import requests
import json
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings

# 测试配置
settings = get_settings()
BASE_URL = settings.test.base_url

class RAGTest:
    """RAG功能测试类"""
    
    def __init__(self):
        self.token = None
        self.headers = {}
        self.test_file_path = None
    
    def login(self):
        """登录获取token"""
        print("=== 登录系统 ===")
        
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/auth/login", json=login_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print("✓ 登录成功")
                return True
            else:
                print(f"✗ 登录失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 登录异常: {e}")
            return False
    
    def test_document_upload(self):
        """测试文档上传功能"""
        print("\n=== 测试文档上传功能 ===")
        
        # 创建测试文件
        test_content = """
        这是一个测试文档，用于验证RAG系统的文档上传功能。
        
        风机运行状态：
        - 风机编号：WT001
        - 运行状态：正常
        - 发电功率：2.5MW
        - 风速：12m/s
        - 温度：25°C
        
        故障记录：
        - 2024年1月15日：齿轮箱温度异常，已处理
        - 2024年1月20日：叶片结冰，已除冰
        """
        
        test_file_name = "test_document.txt"
        self.test_file_path = f"/tmp/{test_file_name}"
        
        try:
            # 创建测试文件
            with open(self.test_file_path, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            # 上传文件
            with open(self.test_file_path, 'rb') as f:
                files = {'file': (test_file_name, f, 'text/plain')}
                response = requests.post(
                    f"{BASE_URL}/api/rag/upload",
                    headers=self.headers,
                    files=files
                )
            
            print(f"文档上传响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 文档上传成功")
                print(f"上传结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"✗ 文档上传失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 文档上传异常: {e}")
            return False
        finally:
            # 清理测试文件
            if self.test_file_path and os.path.exists(self.test_file_path):
                os.remove(self.test_file_path)
    
    def test_document_list(self):
        """测试文档列表获取"""
        print("\n=== 测试文档列表获取 ===")
        
        try:
            response = requests.get(
                f"{BASE_URL}/api/rag/documents",
                headers=self.headers
            )
            print(f"文档列表响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 文档列表获取成功")
                print(f"文档数量: {len(result) if isinstance(result, list) else '非列表格式'}")
                if isinstance(result, list) and len(result) > 0:
                    print(f"示例文档: {json.dumps(result[0], ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"✗ 文档列表获取失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 文档列表获取异常: {e}")
            return False
    
    def test_rag_query(self):
        """测试RAG查询功能"""
        print("\n=== 测试RAG查询功能 ===")
        
        test_queries = [
            "风机WT001的运行状态如何？",
            "最近有哪些故障记录？",
            "齿轮箱温度异常如何处理？"
        ]
        
        success_count = 0
        
        for query in test_queries:
            try:
                print(f"\n查询: {query}")
                
                response = requests.post(
                    f"{BASE_URL}/api/rag/query",
                    headers=self.headers,
                    json={"query": query}
                )
                print(f"查询响应码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    print("✓ 查询成功")
                    print(f"回答: {result.get('answer', '无回答')}")
                    print(f"相关文档: {len(result.get('sources', []))} 个")
                    success_count += 1
                else:
                    print(f"✗ 查询失败: {response.text}")
                    
            except Exception as e:
                print(f"✗ 查询异常: {e}")
        
        print(f"\nRAG查询测试完成，成功: {success_count}/{len(test_queries)}")
        return success_count > 0  # 至少有一个查询成功
    
    def test_vector_search(self):
        """测试向量检索功能"""
        print("\n=== 测试向量检索功能 ===")
        
        try:
            search_query = "风机故障"
            
            response = requests.post(
                f"{BASE_URL}/api/rag/search",
                headers=self.headers,
                json={
                    "query": search_query,
                    "top_k": 5
                }
            )
            print(f"向量检索响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 向量检索成功")
                print(f"检索到 {len(result)} 个相关文档片段")
                if len(result) > 0:
                    print(f"最相关片段: {result[0].get('content', '无内容')[:100]}...")
                return True
            else:
                print(f"✗ 向量检索失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 向量检索异常: {e}")
            return False
    
    def test_embedding_service(self):
        """测试嵌入服务"""
        print("\n=== 测试嵌入服务 ===")
        
        try:
            test_text = "这是一个测试文本，用于验证嵌入服务"
            
            response = requests.post(
                f"{BASE_URL}/api/rag/embed",
                headers=self.headers,
                json={"text": test_text}
            )
            print(f"嵌入服务响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 嵌入服务正常")
                embedding = result.get('embedding', [])
                print(f"嵌入向量维度: {len(embedding)}")
                return True
            else:
                print(f"✗ 嵌入服务失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 嵌入服务异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有RAG测试"""
        print("开始RAG功能测试...")
        print(f"测试服务器: {BASE_URL}")
        print("-" * 50)
        
        # 先登录
        if not self.login():
            print("✗ 登录失败，无法继续测试")
            return False
        
        results = []
        results.append(self.test_document_list())
        results.append(self.test_document_upload())
        results.append(self.test_vector_search())
        results.append(self.test_rag_query())
        results.append(self.test_embedding_service())
        
        print("\n" + "=" * 50)
        print(f"RAG测试完成，成功: {sum(results)}/{len(results)}")
        
        return all(results)

def main():
    """主函数"""
    rag_test = RAGTest()
    success = rag_test.run_all_tests()
    
    if success:
        print("✓ 所有RAG测试通过")
        exit(0)
    else:
        print("✗ 部分RAG测试失败")
        exit(1)

if __name__ == "__main__":
    main()