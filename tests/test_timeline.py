#!/usr/bin/env python3
"""
时间线功能测试
测试环境：Docker容器
端口: 从配置文件获取
"""

import requests
import json
import time
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings

# 测试配置
settings = get_settings()
BASE_URL = settings.test.base_url
TEST_TURBINE_ID = "c8185942-88b8-4040-b72b-7f0998b43897"  # 使用实际的UUID
FALLBACK_TURBINE_ID = "WT001"  # 备用测试ID

class TimelineTest:
    """时间线功能测试类"""
    
    def __init__(self):
        self.token = None
        self.headers = {}
        self.turbine_id = TEST_TURBINE_ID
    
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
    
    def test_summary_status(self):
        """测试智能总结状态查询"""
        print(f"\n=== 测试智能总结状态查询 ===")
        print(f"风机ID: {self.turbine_id}")
        
        try:
            url = f"{BASE_URL}/api/timeline/turbine/{self.turbine_id}/summary-status"
            response = requests.get(url, headers=self.headers)
            print(f"状态查询响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 状态查询成功")
                print(f"状态信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return True
            elif response.status_code == 404:
                print("⚠ 风机不存在，尝试使用备用ID")
                self.turbine_id = FALLBACK_TURBINE_ID
                return self.test_summary_status()
            else:
                print(f"✗ 状态查询失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 状态查询异常: {e}")
            return False
    
    def test_generate_summary(self):
        """测试智能总结生成"""
        print(f"\n=== 测试智能总结生成 ===")
        print(f"风机ID: {self.turbine_id}")
        
        try:
            url = f"{BASE_URL}/api/timeline/turbine/{self.turbine_id}/intelligent-summary"
            params = {"days_back": 30}
            response = requests.post(url, headers=self.headers, params=params)
            print(f"总结生成响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 智能总结生成成功")
                print(f"总结结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
                return True
            elif response.status_code == 202:
                print("✓ 智能总结生成任务已提交，正在处理中")
                return True
            else:
                print(f"✗ 智能总结生成失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 智能总结生成异常: {e}")
            return False
    
    def test_timeline_data(self):
        """测试时间线数据获取"""
        print(f"\n=== 测试时间线数据获取 ===")
        print(f"风机ID: {self.turbine_id}")
        
        try:
            url = f"{BASE_URL}/api/timeline/turbine/{self.turbine_id}"
            params = {"days_back": 7}  # 获取最近7天数据
            response = requests.get(url, headers=self.headers, params=params)
            print(f"时间线数据响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 时间线数据获取成功")
                print(f"数据条数: {len(result) if isinstance(result, list) else '非列表格式'}")
                if isinstance(result, list) and len(result) > 0:
                    print(f"示例数据: {json.dumps(result[0], ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"✗ 时间线数据获取失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 时间线数据获取异常: {e}")
            return False
    
    def test_turbine_list(self):
        """测试风机列表获取"""
        print(f"\n=== 测试风机列表获取 ===")
        
        try:
            url = f"{BASE_URL}/api/turbines"
            response = requests.get(url, headers=self.headers)
            print(f"风机列表响应码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 风机列表获取成功")
                print(f"风机数量: {len(result) if isinstance(result, list) else '非列表格式'}")
                if isinstance(result, list) and len(result) > 0:
                    print(f"第一个风机: {json.dumps(result[0], ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"✗ 风机列表获取失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 风机列表获取异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有时间线测试"""
        print("开始时间线功能测试...")
        print(f"测试服务器: {BASE_URL}")
        print("-" * 50)
        
        # 先登录
        if not self.login():
            print("✗ 登录失败，无法继续测试")
            return False
        
        results = []
        results.append(self.test_turbine_list())
        results.append(self.test_summary_status())
        results.append(self.test_timeline_data())
        results.append(self.test_generate_summary())
        
        print("\n" + "=" * 50)
        print(f"时间线测试完成，成功: {sum(results)}/{len(results)}")
        
        return all(results)

def main():
    """主函数"""
    timeline_test = TimelineTest()
    success = timeline_test.run_all_tests()
    
    if success:
        print("✓ 所有时间线测试通过")
        exit(0)
    else:
        print("✗ 部分时间线测试失败")
        exit(1)

if __name__ == "__main__":
    main()