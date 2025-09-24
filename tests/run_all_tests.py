#!/usr/bin/env python3
"""
测试运行器
统一运行所有测试模块或指定测试模块
端口: 8003 (容器内测试)
"""

import sys
import os
import importlib
import argparse
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 测试模块映射
TEST_MODULES = {
    'auth': 'test_auth',
    'timeline': 'test_timeline', 
    'system': 'test_system',
    'rag': 'test_rag'
}

class TestRunner:
    """测试运行器类"""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_single_test(self, module_name):
        """运行单个测试模块"""
        print(f"\n{'='*60}")
        print(f"运行测试模块: {module_name}")
        print(f"{'='*60}")
        
        try:
            # 动态导入测试模块
            module = importlib.import_module(f"tests.{module_name}")
            
            # 运行测试
            if hasattr(module, 'main'):
                # 捕获退出码
                try:
                    module.main()
                    self.results[module_name] = True
                    print(f"✓ {module_name} 测试通过")
                except SystemExit as e:
                    success = e.code == 0
                    self.results[module_name] = success
                    if success:
                        print(f"✓ {module_name} 测试通过")
                    else:
                        print(f"✗ {module_name} 测试失败")
            else:
                print(f"✗ {module_name} 模块没有main函数")
                self.results[module_name] = False
                
        except ImportError as e:
            print(f"✗ 无法导入测试模块 {module_name}: {e}")
            self.results[module_name] = False
        except Exception as e:
            print(f"✗ 运行测试模块 {module_name} 时发生异常: {e}")
            self.results[module_name] = False
    
    def run_all_tests(self):
        """运行所有测试模块"""
        print("开始运行所有测试...")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目根目录: {project_root}")
        
        self.start_time = datetime.now()
        
        for test_key, module_name in TEST_MODULES.items():
            self.run_single_test(module_name)
        
        self.end_time = datetime.now()
        self.print_summary()
    
    def run_specific_tests(self, test_names):
        """运行指定的测试模块"""
        print(f"开始运行指定测试: {', '.join(test_names)}")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.start_time = datetime.now()
        
        for test_name in test_names:
            if test_name in TEST_MODULES:
                module_name = TEST_MODULES[test_name]
                self.run_single_test(module_name)
            else:
                print(f"✗ 未知的测试模块: {test_name}")
                print(f"可用的测试模块: {', '.join(TEST_MODULES.keys())}")
                self.results[test_name] = False
        
        self.end_time = datetime.now()
        self.print_summary()
    
    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'='*60}")
        print("测试总结")
        print(f"{'='*60}")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result)
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            print(f"耗时: {duration.total_seconds():.2f} 秒")
        
        print("\n详细结果:")
        for test_name, result in self.results.items():
            status = "✓ 通过" if result else "✗ 失败"
            print(f"  {test_name}: {status}")
        
        # 总体结果
        if failed_tests == 0:
            print(f"\n🎉 所有测试通过！")
            return True
        else:
            print(f"\n❌ 有 {failed_tests} 个测试失败")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Wind Whisper RAG 系统测试运行器')
    parser.add_argument(
        'tests', 
        nargs='*', 
        choices=list(TEST_MODULES.keys()) + ['all'],
        help=f'要运行的测试模块 ({", ".join(TEST_MODULES.keys())}) 或 "all" 运行所有测试'
    )
    parser.add_argument(
        '--list', 
        action='store_true',
        help='列出所有可用的测试模块'
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("可用的测试模块:")
        for key, module in TEST_MODULES.items():
            print(f"  {key}: {module}")
        return
    
    runner = TestRunner()
    
    if not args.tests or 'all' in args.tests:
        # 运行所有测试
        success = runner.run_all_tests()
    else:
        # 运行指定测试
        success = runner.run_specific_tests(args.tests)
    
    # 根据测试结果设置退出码
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()