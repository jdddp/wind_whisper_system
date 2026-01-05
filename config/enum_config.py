"""
枚举值配置文件
统一管理所有枚举类型的标准值
"""

# 事件严重程度枚举的标准值
EVENT_SEVERITY_VALUES = [
    'NORMAL',      # 正常
    'CRITICAL',    # 严重
    'ALARM',       # 告警
    'WATCH',       # 观察
    'MAINTENANCE', # 维护
    'UNKNOWN'      # 未知
]

# 事件类型枚举的标准值
EVENT_TYPE_VALUES = [
    'NORMAL',      # 正常事件
    'ALARM',       # 告警事件
    'WATCH',       # 观察事件
    'MAINTENANCE', # 维护事件
    'UNKNOWN'     # 未知事件
]

# 枚举值的中文标签映射
SEVERITY_LABELS = {
    'NORMAL': '正常',
    'CRITICAL': '严重',
    'ALARM': '告警',
    'WATCH': '观察',
    'MAINTENANCE': '维护',
    'UNKNOWN': '未知'
}

EVENT_TYPE_LABELS = {
    'NORMAL': '正常',
    'ALARM': '告警',
    'WATCH': '观察',
    'MAINTENANCE': '维护',
    'FAULT': '故障',
    'INSPECTION': '检查',
    'REPAIR': '修理',
    'UPGRADE': '升级',
    'MONITORING': '监控',
    'UNKNOWN': '未知',
    'OTHER': '其他'
}

# 严重程度的颜色映射（用于前端显示）
SEVERITY_COLORS = {
    'NORMAL': 'success',
    'ALARM': 'danger',
    'WATCH': 'warning',
    'MAINTENANCE': 'info',
    'UNKNOWN': 'secondary'
}

# 严重程度的优先级（数字越大优先级越高）
SEVERITY_PRIORITY = {
    'NORMAL': 1,
    'WATCH': 2,
    'MAINTENANCE': 3,
    'ALARM': 4,
    'UNKNOWN': 0
}