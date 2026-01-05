import enum

class TurbineStatus(str, enum.Enum):
    """统一的风机状态枚举 - 用于所有状态相关字段"""
    NORMAL = "NORMAL"              # 正常
    ALARM = "ALARM"                # 告警
    WATCH = "WATCH"                # 观察
    MAINTENANCE = "MAINTENANCE"     # 维护
    UNKNOWN = "UNKNOWN"            # 未知

class EventType(str, enum.Enum):
    """事件类型枚举"""
    NORMAL = "NORMAL"              # 正常事件
    ALARM = "ALARM"                # 告警事件
    WATCH = "WATCH"                # 观察事件
    MAINTENANCE = "MAINTENANCE"     # 维护事件
    FAULT = "FAULT"                # 故障事件
    INSPECTION = "INSPECTION"       # 检查事件
    REPAIR = "REPAIR"              # 修理事件
    UPGRADE = "UPGRADE"            # 升级事件
    MONITORING = "MONITORING"       # 监控事件
    UNKNOWN = "UNKNOWN"            # 未知事件
    OTHER = "OTHER"                # 其他事件

class LogStatus(str, enum.Enum):
    """记录状态枚举"""
    DRAFT = "draft"
    PUBLISHED = "published"

class AIReviewStatus(str, enum.Enum):
    """AI审核状态枚举"""
    UNREVIEWED = "unreviewed"
    APPROVED = "approved"
    REJECTED = "rejected"