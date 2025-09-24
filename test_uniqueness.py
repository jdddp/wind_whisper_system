#!/usr/bin/env python3
"""
测试专家记录发布时间线事件的唯一性
验证：重复发布同一专家记录只保留最新一次时间线事件
"""

import requests
import json
import time

# 配置
BASE_URL = "http://192.168.3.99:8004/api"

def get_headers(token):
    """获取请求头"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def login():
    """登录获取token"""
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        result = response.json()
        print(f"登录成功: {result['access_token'][:20]}...")
        return result['access_token']
    else:
        print(f"登录失败: {response.text}")
        return None

def create_turbine(token):
    """创建测试风机"""
    headers = get_headers(token)
    
    # 使用时间戳确保唯一性
    timestamp = str(int(time.time()))
    turbine_data = {
        "farm_name": f"测试风场_{timestamp}",
        "unit_id": f"TEST_{timestamp}",
        "model": "测试型号",
        "owner_company": "测试公司",
        "install_date": "2023-01-01",
        "status": "Normal"
    }
    
    response = requests.post(f"{BASE_URL}/turbines/", headers=headers, json=turbine_data)
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"创建风机成功: {result['turbine_id']}")
        return result['turbine_id']
    else:
        print(f"创建风机失败: {response.text}")
        return None

def create_expert_log(token, turbine_id, description):
    """创建专家记录"""
    headers = get_headers(token)
    
    log_data = {
        "turbine_id": turbine_id,
        "status_tag": "Watch",
        "description_text": description
    }
    
    response = requests.post(f"{BASE_URL}/expert-logs/", headers=headers, json=log_data)
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"创建专家记录成功: {result['log_id']} - {description}")
        return result['log_id']
    else:
        print(f"创建专家记录失败: {response.text}")
        return None

def publish_to_timeline(token, log_id):
    """发布专家记录到时间线"""
    headers = get_headers(token)
    
    response = requests.post(f"{BASE_URL}/timeline/update-from-log/{log_id}", headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"发布到时间线成功: {result}")
        return result
    else:
        print(f"发布到时间线失败: {response.text}")
        return None

def get_timeline_events(token):
    """获取所有时间线事件"""
    headers = get_headers(token)
    
    response = requests.get(f"{BASE_URL}/timeline/", headers=headers)
    if response.status_code == 200:
        events = response.json()
        return events
    else:
        print(f"获取时间线事件失败: {response.text}")
        return []

def get_expert_logs(token):
    """获取所有专家记录"""
    headers = get_headers(token)
    
    response = requests.get(f"{BASE_URL}/expert-logs/", headers=headers)
    if response.status_code == 200:
        logs = response.json()
        return logs
    else:
        print(f"获取专家记录失败: {response.text}")
        return []

def main():
    print("开始测试专家记录发布时间线事件的唯一性...")
    
    # 1. 登录
    token = login()
    if not token:
        print("❌ 唯一性测试失败！")
        return
    
    # 2. 创建测试风机
    turbine_id = create_turbine(token)
    if not turbine_id:
        print("❌ 唯一性测试失败！")
        return
    
    # 3. 创建专家记录
    log_id = create_expert_log(token, turbine_id, "测试专家记录")
    if not log_id:
        print("❌ 唯一性测试失败！")
        return
    
    # 4. 获取初始时间线事件数量
    initial_events = get_timeline_events(token)
    print(f"初始时间线事件数量: {len(initial_events)}")
    
    # 5. 第一次发布到时间线
    print("\n=== 第一次发布到时间线 ===")
    result1 = publish_to_timeline(token, log_id)
    if not result1:
        print("❌ 唯一性测试失败！")
        return
    
    events_after_first = get_timeline_events(token)
    print(f"第一次发布后，时间线事件数量: {len(events_after_first)}")
    
    # 6. 第二次发布同一专家记录
    print("\n=== 第二次发布同一专家记录 ===")
    result2 = publish_to_timeline(token, log_id)
    if not result2:
        print("❌ 唯一性测试失败！")
        return
    
    events_after_second = get_timeline_events(token)
    print(f"第二次发布后，时间线事件数量: {len(events_after_second)}")
    
    # 验证唯一性
    uniqueness_passed = True
    if len(events_after_second) == len(events_after_first):
        print("✅ 第二次发布同一专家记录，时间线事件数量保持不变（符合唯一性要求）")
    else:
        print("❌ 第二次发布同一专家记录，时间线事件数量发生变化（违反唯一性要求）")
        uniqueness_passed = False
    
    # 7. 第三次发布同一专家记录
    print("\n=== 第三次发布同一专家记录 ===")
    result3 = publish_to_timeline(token, log_id)
    if result3:
        events_after_third = get_timeline_events(token)
        print(f"第三次发布后，时间线事件数量: {len(events_after_third)}")
        
        if len(events_after_third) == len(events_after_first):
            print("✅ 第三次发布同一专家记录，时间线事件数量保持不变（符合唯一性要求）")
        else:
            print("❌ 第三次发布同一专家记录，时间线事件数量发生变化（违反唯一性要求）")
            uniqueness_passed = False
    
    # 8. 创建另一个专家记录并发布
    print("\n=== 创建并发布另一个专家记录 ===")
    log_id2 = create_expert_log(token, turbine_id, "第二个测试专家记录")
    if log_id2:
        result4 = publish_to_timeline(token, log_id2)
        if result4:
            events_after_fourth = get_timeline_events(token)
            print(f"发布第二个专家记录后，时间线事件数量: {len(events_after_fourth)}")
            
            if len(events_after_fourth) == len(events_after_first) + 1:
                print("✅ 不同专家记录可以正常发布到时间线")
            else:
                print("❌ 不同专家记录发布到时间线异常")
    
    # 9. 显示最终状态
    print("\n=== 最终状态 ===")
    final_events = get_timeline_events(token)
    final_logs = get_expert_logs(token)
    
    print(f"最终时间线事件数量: {len(final_events)}")
    print(f"最终专家记录数量: {len(final_logs)}")
    
    # 显示详细信息
    print("\n=== 时间线事件详情 ===")
    for i, event in enumerate(final_events[-5:], 1):  # 显示最后5个事件
        print(f"{i}. 事件ID: {event['event_id']}")
        print(f"   风机ID: {event['turbine_id']}")
        print(f"   标题: {event['title']}")
        print(f"   摘要: {event['summary'][:50]}...")
        print(f"   创建时间: {event['created_at']}")
        print()
    
    # 最终结果
    if uniqueness_passed:
        print("✅ 专家记录发布时间线事件的唯一性测试通过！")
    else:
        print("❌ 专家记录发布时间线事件的唯一性测试失败！")

if __name__ == "__main__":
    main()