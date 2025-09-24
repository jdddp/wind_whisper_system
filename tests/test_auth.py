#!/usr/bin/env python3
"""
用户认证功能测试
测试环境：Docker容器
端口: 从配置文件获取
"""

import requests
import json
import time
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import get_settings

# 测试配置
settings = get_settings()
BASE_URL = settings.test.base_url
TEST_USER = {
    "username": "admin",
    "password": "admin123"
}

class AuthTest:
    """认证功能测试类"""
    
    def __init__(self):
        self.token = None
        self.headers = {}
    
    def test_login(self):
        """测试用户登录功能"""
        print("=== 测试用户登录 ===")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login", 
                json=TEST_USER
            )
            print(f"登录响应码: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get("access_token")
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print("✓ 登录成功")
                print(f"Token: {self.token[:20]}...")
                return True
            else:
                print(f"✗ 登录失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 登录测试异常: {e}")
            return False
    
    def test_token_validation(self):
        """测试token验证功能"""
        print("\n=== 测试Token验证 ===")
        
        if not self.token:
            print("✗ 无有效token，请先登录")
            return False
        
        try:
            # 测试需要认证的API
            response = requests.get(
                f"{BASE_URL}/api/auth/me", 
                headers=self.headers
            )
            print(f"Token验证响应码: {response.status_code}")
            
            if response.status_code == 200:
                user_info = response.json()
                print("✓ Token验证成功")
                print(f"用户信息: {json.dumps(user_info, ensure_ascii=False, indent=2)}")
                return True
            else:
                print(f"✗ Token验证失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Token验证异常: {e}")
            return False
    
    def test_invalid_credentials(self):
        """测试无效凭据"""
        print("\n=== 测试无效凭据 ===")
        
        invalid_user = {
            "username": "invalid_user",
            "password": "wrong_password"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login", 
                json=invalid_user
            )
            print(f"无效凭据响应码: {response.status_code}")
            
            if response.status_code == 401:
                print("✓ 正确拒绝无效凭据")
                return True
            else:
                print(f"✗ 未正确处理无效凭据: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ 无效凭据测试异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有认证测试"""
        print("开始认证功能测试...")
        print(f"测试服务器: {BASE_URL}")
        print("-" * 50)
        
        results = []
        results.append(self.test_login())
        results.append(self.test_token_validation())
        results.append(self.test_invalid_credentials())
        
        print("\n" + "=" * 50)
        print(f"认证测试完成，成功: {sum(results)}/{len(results)}")
        
        return all(results)

def main():
    """主函数"""
    auth_test = AuthTest()
    success = auth_test.run_all_tests()
    
    if success:
        print("✓ 所有认证测试通过")
        exit(0)
    else:
        print("✗ 部分认证测试失败")
        exit(1)

if __name__ == "__main__":
    main()