# Wind Whisper RAG System 数据库说明文档

## 📋 目录
- [数据库概览](#数据库概览)
- [架构设计](#架构设计)
- [数据表详细说明](#数据表详细说明)
- [表关系图](#表关系图)
- [索引和性能优化](#索引和性能优化)
- [数据库初始化](#数据库初始化)
- [维护和监控](#维护和监控)

---

## 🗄️ 数据库概览

### 基本信息
- **数据库类型**: PostgreSQL 14+
- **扩展要求**: pgvector (向量数据库支持)
- **字符编码**: UTF-8
- **时区**: UTC
- **连接池**: SQLAlchemy 连接池管理

### 核心功能
Wind Whisper RAG System 是一个基于检索增强生成(RAG)的风机专家知识管理系统，数据库设计支持：

1. **用户管理**: 多角色用户系统，支持管理员、专家、观察者等角色
2. **风机管理**: 风机基础信息、状态监控、分组管理
3. **专家记录**: 专家日志记录、AI增强处理、版本控制
4. **智能检索**: 基于向量数据库的语义检索
5. **时间线分析**: 风机事件时间线自动生成
6. **附件管理**: 多媒体附件存储和文本提取
7. **智能分析**: AI驱动的数据分析和报告生成

### 数据表统计
- **核心表数量**: 8个主要数据表
- **关系表数量**: 1个关联表
- **总表数量**: 9个表
- **预估数据量**: 
  - 用户表(users): 10-1000条记录
  - 风机表(turbines): 50-10000条记录
  - 专家记录(expert_logs): 1000-100000条记录
  - 记录块(log_chunks): 10000-1000000条记录
  - 附件(attachments): 1000-50000条记录
  - 时间线事件(timeline_events): 1000-100000条记录
  - 智能分析(intelligent_analyses): 100-10000条记录

---

## 🏗️ 架构设计

### 数据库架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                │
├─────────────────────────────────────────────────────────────┤
│                    业务逻辑层 (Business Logic)               │
├─────────────────────────────────────────────────────────────┤
│                    数据访问层 (Data Access Layer)            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   用户管理   │ │   风机管理   │ │  知识管理   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                    数据存储层 (Data Storage Layer)           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ PostgreSQL  │ │  pgvector   │ │ 文件系统    │           │
│  │   关系数据   │ │   向量数据   │ │  附件存储   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

### 核心设计原则

1. **数据一致性**: 使用外键约束确保数据完整性
2. **性能优化**: 合理设计索引，支持高效查询
3. **扩展性**: 支持水平和垂直扩展
4. **安全性**: 密码加密、权限控制、数据隔离
5. **可维护性**: 清晰的表结构、标准化命名
6. **AI友好**: 向量存储、JSON字段支持AI功能

---

## 📊 数据表详细说明

### 1. 用户表 (users)

**用途**: 管理系统用户信息、角色权限和认证数据

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| user_id | UUID | PRIMARY KEY | 用户唯一标识符 |
| username | VARCHAR(50) | UNIQUE, NOT NULL, INDEX | 用户名，登录凭证 |
| password_hash | VARCHAR(255) | NOT NULL | 加密后的密码 |
| role | ENUM(UserRole) | NOT NULL, DEFAULT READER | 用户角色：ADMIN/EXPERT/READER |
| is_active | BOOLEAN | DEFAULT TRUE | 账户是否激活 |
| created_at | TIMESTAMP | DEFAULT NOW() | 账户创建时间 |
| updated_at | TIMESTAMP | ON UPDATE NOW() | 记录更新时间 |

**业务规则**:
- 用户名必须唯一，有索引优化
- 密码使用哈希加密存储
- 支持三种角色：管理员(ADMIN)、专家(EXPERT)、读者(READER)
- 软删除：通过is_active字段控制账户状态
- 默认角色为READER（只读权限）

**索引设计**:
```sql
-- 主键索引（自动创建）
CREATE INDEX idx_users_pkey ON users(user_id);

-- 唯一索引（自动创建）
CREATE UNIQUE INDEX idx_users_username ON users(username);

-- 查询优化索引
CREATE INDEX idx_users_role_active ON users(role, is_active);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_updated_at ON users(updated_at);
```

### 2. 风机表 (turbines)

**用途**: 存储风机基础信息和运行状态

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| turbine_id | UUID | PRIMARY KEY | 风机唯一标识符 |
| farm_name | VARCHAR(100) | NOT NULL | 所属风场名称 |
| unit_id | VARCHAR(50) | NOT NULL | 风机单元编号 |
| model | VARCHAR(100) | - | 风机型号 |
| owner_company | VARCHAR(100) | - | 业主公司 |
| install_date | DATE | - | 安装日期 |
| status | VARCHAR(20) | DEFAULT 'Normal' | 当前运行状态 |
| metadata_json | JSON | - | 扩展信息(经纬度、额定功率等) |
| created_at | TIMESTAMP | DEFAULT NOW() | 记录创建时间 |
| updated_at | TIMESTAMP | ON UPDATE NOW() | 记录更新时间 |

**业务规则**:
- farm_name + unit_id 组合唯一约束
- 支持运行状态：Normal、Watch、Alarm、Maintenance、Unknown
- metadata_json 字段存储扩展信息，如地理坐标、技术参数等
- 灵活的JSON结构支持不同型号风机的差异化信息

**索引设计**:
```sql
-- 主键索引（自动创建）
CREATE INDEX idx_turbines_pkey ON turbines(turbine_id);

-- 唯一约束索引
CREATE UNIQUE INDEX uq_farm_unit ON turbines(farm_name, unit_id);

-- 业务查询索引
CREATE INDEX idx_turbines_farm_name ON turbines(farm_name);
CREATE INDEX idx_turbines_status ON turbines(status);
CREATE INDEX idx_turbines_model ON turbines(model);
CREATE INDEX idx_turbines_owner_company ON turbines(owner_company);

-- 复合索引
CREATE INDEX idx_turbines_farm_status ON turbines(farm_name, status);
CREATE INDEX idx_turbines_install_date ON turbines(install_date);
```

### 3. 专家记录表 (expert_logs)

**用途**: 存储风机专家的运维记录、故障分析和维护建议，支持AI增强功能

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| log_id | UUID | PRIMARY KEY | 记录唯一标识符 |
| turbine_id | UUID | FOREIGN KEY | 关联风机ID |
| author_id | UUID | FOREIGN KEY | 作者用户ID |
| status_tag | ENUM(StatusTag) | NOT NULL, DEFAULT UNKNOWN | 状态标签：Normal/Watch/Alarm/Maintenance/Unknown |
| description_text | TEXT | NOT NULL | 详细内容描述 |
| log_status | ENUM(LogStatus) | NOT NULL, DEFAULT DRAFT | 记录状态：draft/published |
| ai_summary | TEXT | - | AI生成的约束式摘要 |
| ai_tags | JSON | - | AI生成的结构化标签 |
| ai_confidence | NUMERIC(3,2) | - | AI可信度评分(0-1) |
| ai_review_status | ENUM(AIReviewStatus) | DEFAULT UNREVIEWED | AI审核状态：unreviewed/approved/rejected |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | ON UPDATE NOW() | 更新时间 |
| published_at | TIMESTAMP | - | 发布时间 |

**业务规则**:
- 每条记录必须关联到具体风机和作者
- 支持草稿和发布状态管理
- 状态标签反映风机当前运行状态
- AI增强功能：自动摘要、标签提取、可信度评估
- AI审核流程：未审核 → 批准/拒绝

**关系说明**:
- `turbine_id` → `turbines.turbine_id` (多对一)
- `author_id` → `users.user_id` (多对一)

**索引设计**:
```sql
-- 主键和外键索引
CREATE INDEX idx_expert_logs_pkey ON expert_logs(log_id);
CREATE INDEX idx_expert_logs_turbine_id ON expert_logs(turbine_id);
CREATE INDEX idx_expert_logs_author_id ON expert_logs(author_id);

-- 业务查询索引
CREATE INDEX idx_expert_logs_status_tag ON expert_logs(status_tag);
CREATE INDEX idx_expert_logs_log_status ON expert_logs(log_status);
CREATE INDEX idx_expert_logs_published_at ON expert_logs(published_at);

-- 复合索引
CREATE INDEX idx_expert_logs_turbine_status ON expert_logs(turbine_id, log_status);
CREATE INDEX idx_expert_logs_turbine_published ON expert_logs(turbine_id, published_at);

-- AI相关索引
CREATE INDEX idx_expert_logs_ai_review ON expert_logs(ai_review_status);
```

### 4. 记录块表 (log_chunks)

**用途**: 存储专家记录的文本分块和向量嵌入，支持语义检索

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| chunk_id | UUID | PRIMARY KEY | 块唯一标识符 |
| log_id | UUID | FOREIGN KEY | 关联专家记录ID |
| turbine_id | UUID | FOREIGN KEY | 关联风机ID（冗余字段，便于查询） |
| chunk_text | TEXT | NOT NULL | 分块文本内容 |
| embedding | VECTOR(1024) | - | 文本向量嵌入（bge-m3模型） |
| status_tag | VARCHAR(20) | - | 状态标签（冗余字段，便于检索过滤） |
| published_at | TIMESTAMP | - | 发布时间（冗余字段，便于检索过滤） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**业务规则**:
- 每个专家记录按语义边界分割成多个块
- 向量维度固定为1024（bge-m3模型）
- 冗余字段（turbine_id、status_tag、published_at）优化跨表查询性能
- 支持基于向量相似度的语义检索
- 仅存储已发布记录的文本块

**关系说明**:
- `log_id` → `expert_logs.log_id` (多对一)
- `turbine_id` → `turbines.turbine_id` (多对一)

**索引设计**:
```sql
-- 主键和外键索引
CREATE INDEX idx_log_chunks_pkey ON log_chunks(chunk_id);
CREATE INDEX idx_log_chunks_log_id ON log_chunks(log_id);
CREATE INDEX idx_log_chunks_turbine_id ON log_chunks(turbine_id);

-- 向量检索索引
CREATE INDEX idx_log_chunks_embedding ON log_chunks USING ivfflat (embedding vector_cosine_ops);

-- 业务查询索引
CREATE INDEX idx_log_chunks_status_published ON log_chunks(status_tag, published_at);
```

### 5. 附件表 (attachments)

**用途**: 管理专家记录的附件文件，支持多媒体内容和文本提取

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| attachment_id | UUID | PRIMARY KEY | 附件唯一标识符 |
| log_id | UUID | FOREIGN KEY | 关联专家记录ID |
| file_name | VARCHAR(255) | NOT NULL | 原始文件名 |
| file_type | VARCHAR(100) | - | MIME类型 |
| file_size | BIGINT | - | 文件大小（字节） |
| storage_path | TEXT | NOT NULL | 本地存储路径 |
| extracted_text | TEXT | - | OCR/ASR/解析后的文本 |
| ai_excerpt | TEXT | - | 附件级要点摘录 |
| uploaded_at | TIMESTAMP | DEFAULT NOW() | 上传时间 |

**业务规则**:
- 支持图片、文档、音频、视频等多种格式
- 自动提取文本内容（OCR、ASR、文档解析）
- AI摘录提供附件关键信息概览
- 本地存储路径管理文件位置
- 与专家记录一对多关联

**关系说明**:
- `log_id` → `expert_logs.log_id` (多对一)

**索引设计**:
```sql
-- 主键和外键索引
CREATE INDEX idx_attachments_pkey ON attachments(attachment_id);
CREATE INDEX idx_attachments_log_id ON attachments(log_id);

-- 业务查询索引
CREATE INDEX idx_attachments_file_type ON attachments(file_type);
CREATE INDEX idx_attachments_uploaded_at ON attachments(uploaded_at);
```

### 6. 时间线事件表 (timeline_events)

**用途**: 构建风机的时间线视图，整合多源数据形成事件序列

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| event_id | UUID | PRIMARY KEY | 事件唯一标识符 |
| turbine_id | UUID | FOREIGN KEY | 关联风机ID |
| event_time | TIMESTAMP | NOT NULL | AI提取的事件发生时间 |
| event_type | ENUM(EventType) | NOT NULL | 事件类型：NORMAL/ALARM/WATCH/MAINTENANCE/FAULT等 |
| event_severity | ENUM(EventSeverity) | DEFAULT LOW | 事件严重程度：NORMAL/LOW/MEDIUM/HIGH/CRITICAL |
| title | VARCHAR(200) | NOT NULL | AI生成的事件标题 |
| summary | TEXT | NOT NULL | AI生成的事件摘要 |
| key_points | JSON | - | 关键要点列表 |
| confidence_score | NUMERIC(3,2) | - | AI分析的置信度(0-1) |
| is_verified | BOOLEAN | DEFAULT FALSE | 是否经过人工验证 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | ON UPDATE NOW() | 更新时间 |

**业务规则**:
- AI自动从专家记录中提取和生成事件
- 事件按时间排序形成风机运维时间线
- 支持11种事件类型和5种严重程度级别
- 置信度评估AI分析的可靠性
- 人工验证确保关键事件的准确性
- 关键要点以JSON格式存储结构化信息

**关系说明**:
- `turbine_id` → `turbines.turbine_id` (多对一)

**索引设计**:
```sql
-- 主键和外键索引
CREATE INDEX idx_timeline_events_pkey ON timeline_events(event_id);
CREATE INDEX idx_timeline_events_turbine_id ON timeline_events(turbine_id);

-- 时间线查询索引
CREATE INDEX idx_timeline_events_event_time ON timeline_events(event_time);
CREATE INDEX idx_timeline_events_turbine_time ON timeline_events(turbine_id, event_time);

-- 业务查询索引
CREATE INDEX idx_timeline_events_type ON timeline_events(event_type);
CREATE INDEX idx_timeline_events_severity ON timeline_events(event_severity);
CREATE INDEX idx_timeline_events_verified ON timeline_events(is_verified);
```

### 7. 时间线源记录关联表 (timeline_source_logs)

**用途**: 建立时间线事件与源专家记录之间的多对多关联关系

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| id | UUID | PRIMARY KEY | 关联记录唯一标识符 |
| event_id | UUID | FOREIGN KEY | 关联时间线事件ID |
| log_id | UUID | FOREIGN KEY | 关联专家记录ID |
| relevance_score | NUMERIC(3,2) | DEFAULT 1.0 | 关联权重(0-1) |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

**业务规则**:
- 一个时间线事件可能来源于多个专家记录
- 一个专家记录可能贡献给多个时间线事件
- 关联权重表示专家记录对事件的贡献度
- 支持溯源和可解释性分析

**关系说明**:
- `event_id` → `timeline_events.event_id` (多对一)
- `log_id` → `expert_logs.log_id` (多对一)

**索引设计**:
```sql
-- 主键和外键索引
CREATE INDEX idx_timeline_source_logs_pkey ON timeline_source_logs(id);
CREATE INDEX idx_timeline_source_logs_event_id ON timeline_source_logs(event_id);
CREATE INDEX idx_timeline_source_logs_log_id ON timeline_source_logs(log_id);

-- 复合索引
CREATE UNIQUE INDEX idx_timeline_source_logs_event_log ON timeline_source_logs(event_id, log_id);
```

### 8. 智能分析表 (intelligent_analyses)

**用途**: 存储AI对风机数据的智能分析结果和洞察

| 字段名 | 数据类型 | 约束 | 说明 |
|--------|----------|------|------|
| analysis_id | UUID | PRIMARY KEY | 分析记录ID |
| turbine_id | UUID | FOREIGN KEY | 关联风机ID |
| analysis_mode | VARCHAR(20) | NOT NULL | 分析模式：'llm'或'basic' |
| days_back | INTEGER | NOT NULL, DEFAULT 30 | 回溯天数 |
| summary | TEXT | NOT NULL | 分析总结 |
| analysis_data | JSON | - | 原始分析数据（包含统计信息等） |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| updated_at | TIMESTAMP | ON UPDATE NOW() | 更新时间 |

**业务规则**:
- 支持两种分析模式：LLM智能分析和基础统计分析
- 回溯天数定义分析的数据时间窗口
- 分析数据以JSON格式存储原始统计信息
- 分析总结提供人类可读的结果概述
- 支持分析结果的更新和版本管理

**关系说明**:
- `turbine_id` → `turbines.turbine_id` (多对一)

**索引设计**:
```sql
-- 主键和外键索引
CREATE INDEX idx_intelligent_analyses_pkey ON intelligent_analyses(analysis_id);
CREATE INDEX idx_intelligent_analyses_turbine_id ON intelligent_analyses(turbine_id);

-- 业务查询索引
CREATE INDEX idx_intelligent_analyses_mode ON intelligent_analyses(analysis_mode);
CREATE INDEX idx_intelligent_analyses_created_at ON intelligent_analyses(created_at);

-- 复合索引
CREATE INDEX idx_intelligent_analyses_turbine_created ON intelligent_analyses(turbine_id, created_at);
```

---

## 🔗 表关系图

### 核心关系图

```
                    ┌─────────────────┐
                    │     users       │
                    │   (用户表)       │
                    └─────────┬───────┘
                              │ 1:N (author_id)
                              │
    ┌─────────────────┐      │      ┌─────────────────┐
    │   turbines      │      │      │  expert_logs    │
    │   (风机表)       │◄─────┼─────►│  (专家记录表)    │
    └─────────┬───────┘      │      └─────────┬───────┘
              │ 1:N          │                │ 1:N
              │              │                │
              │              │                ▼
              │              │      ┌─────────────────┐
              │              │      │  attachments    │
              │              │      │   (附件表)       │
              │              │      └─────────────────┘
              │              │
              │              │      ┌─────────────────┐
              │              └─────►│   log_chunks    │
              │                     │  (记录块表)      │
              │                     └─────────────────┘
              │
              │ 1:N
              ▼
    ┌─────────────────┐
    │timeline_events  │
    │ (时间线事件表)   │
    └─────────┬───────┘
              │ N:M
              ▼
    ┌─────────────────┐      ┌─────────────────┐
    │timeline_source_ │ N:M  │  expert_logs    │
    │logs (关联表)     │◄────►│  (专家记录表)    │
    └─────────────────┘      └─────────────────┘
              │
              │ 1:N
              ▼
    ┌─────────────────┐
    │intelligent_     │
    │analyses         │
    │ (智能分析表)     │
    └─────────────────┘
```

### 详细关系说明

#### 1. 用户与专家记录 (1:N)
- **关系**: 一个用户可以创建多个专家记录
- **外键**: `expert_logs.author_id` → `users.user_id`
- **业务含义**: 追踪记录的创建者，支持权限控制

#### 2. 风机与专家记录 (1:N)
- **关系**: 一台风机可以有多个专家记录
- **外键**: `expert_logs.turbine_id` → `turbines.turbine_id`
- **业务含义**: 将专家观察与具体风机关联

#### 3. 专家记录与附件 (1:N)
- **关系**: 一个专家记录可以有多个附件
- **外键**: `attachments.log_id` → `expert_logs.log_id`
- **业务含义**: 支持多媒体内容的专家记录
- **级联删除**: 删除专家记录时自动删除相关附件

#### 4. 专家记录与记录块 (1:N)
- **关系**: 一个专家记录被分割成多个文本块
- **外键**: `log_chunks.log_id` → `expert_logs.log_id`
- **业务含义**: 支持细粒度的语义检索
- **级联删除**: 删除专家记录时自动删除相关文本块

#### 5. 风机与时间线事件 (1:N)
- **关系**: 一台风机可以有多个时间线事件
- **外键**: `timeline_events.turbine_id` → `turbines.turbine_id`
- **业务含义**: 构建风机的历史事件时间线

#### 6. 时间线事件与专家记录 (N:M)
- **关系**: 多对多关系，通过关联表实现
- **关联表**: `timeline_source_logs`
- **外键**: 
  - `timeline_source_logs.event_id` → `timeline_events.event_id`
  - `timeline_source_logs.log_id` → `expert_logs.log_id`
- **业务含义**: 追踪时间线事件的数据来源

#### 7. 风机与智能分析 (1:N)
- **关系**: 一台风机可以有多个智能分析结果
- **外键**: `intelligent_analyses.turbine_id` → `turbines.turbine_id`
- **业务含义**: 存储针对特定风机的分析报告

---

## ⚡ 索引和性能优化

### 主要索引策略

#### 1. 主键索引
所有表都使用UUID作为主键，自动创建聚集索引：
```sql
-- 自动创建的主键索引
CREATE UNIQUE INDEX pk_users ON users(user_id);
CREATE UNIQUE INDEX pk_turbines ON turbines(turbine_id);
-- ... 其他表类似
```

#### 2. 外键索引
为所有外键字段创建索引，提高关联查询性能：
```sql
-- 专家记录表的外键索引
CREATE INDEX idx_expert_logs_turbine_id ON expert_logs(turbine_id);
CREATE INDEX idx_expert_logs_author_id ON expert_logs(author_id);

-- 附件表的外键索引
CREATE INDEX idx_attachments_log_id ON attachments(log_id);

-- 记录块表的外键索引
CREATE INDEX idx_log_chunks_log_id ON log_chunks(log_id);
CREATE INDEX idx_log_chunks_turbine_id ON log_chunks(turbine_id);
```

#### 3. 业务查询索引
基于常见查询模式创建的复合索引：
```sql
-- 风机状态查询
CREATE INDEX idx_turbines_farm_status ON turbines(farm_name, current_status);

-- 专家记录时间范围查询
CREATE INDEX idx_expert_logs_turbine_published ON expert_logs(turbine_id, published_at);

-- 时间线事件查询
CREATE INDEX idx_timeline_events_turbine_time ON timeline_events(turbine_id, event_time);
```

#### 4. 向量索引
使用pgvector扩展的IVFFlat索引支持高效向量检索：
```sql
-- 向量相似度检索索引
CREATE INDEX idx_log_chunks_embedding ON log_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

### 性能优化建议

#### 1. 查询优化
- **分页查询**: 使用LIMIT和OFFSET进行分页
- **条件过滤**: 在WHERE子句中使用索引字段
- **排序优化**: 在ORDER BY字段上创建索引

#### 2. 连接池配置
```python
# SQLAlchemy连接池配置
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # 连接池大小
    max_overflow=30,       # 最大溢出连接
    pool_timeout=30,       # 连接超时时间
    pool_recycle=3600,     # 连接回收时间
    pool_pre_ping=True     # 连接健康检查
)
```

#### 3. 向量检索优化
- **索引参数调优**: 根据数据量调整lists参数
- **查询限制**: 使用适当的LIMIT限制返回结果
- **预过滤**: 在向量检索前进行业务条件过滤

#### 4. 数据分区策略
对于大数据量表，考虑按时间分区：
```sql
-- 专家记录表按月分区（示例）
CREATE TABLE expert_logs_y2024m01 PARTITION OF expert_logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## 🚀 数据库初始化

### 初始化脚本

系统提供完整的数据库初始化脚本：`scripts/init_db.py`

#### 初始化流程
1. **创建数据库表结构**
2. **启用pgvector扩展**
3. **创建默认管理员用户**
4. **初始化示例风机数据**
5. **设置索引和约束**

#### 执行方式
```bash
# 在项目根目录执行
python scripts/init_db.py
```

#### 初始化内容

##### 1. 默认管理员用户
```python
# 默认管理员账户
username: "admin"
email: "admin@windwhisper.com"
password: "admin123"  # 生产环境请修改
role: UserRole.ADMIN
```

##### 2. 示例风机数据
```python
# 示例风机配置
turbines = [
    {
        "turbine_name": "WT001",
        "farm_name": "北山风场",
        "model": "GE 2.5-120",
        "manufacturer": "GE",
        "capacity_kw": 2500.0,
        "hub_height": 80.0,
        "rotor_diameter": 120.0
    },
    # ... 更多示例数据
]
```

### 数据库迁移

使用Alembic进行数据库版本管理：

```bash
# 生成迁移脚本
alembic revision --autogenerate -m "描述变更内容"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

---

## 🔧 维护和监控

### 日常维护任务

#### 1. 数据备份
```bash
# 完整备份
pg_dump -h localhost -U postgres -d wind_whisper_rag > backup_$(date +%Y%m%d).sql

# 仅数据备份
pg_dump -h localhost -U postgres -d wind_whisper_rag --data-only > data_backup_$(date +%Y%m%d).sql
```

#### 2. 索引维护
```sql
-- 重建索引
REINDEX INDEX idx_log_chunks_embedding;

-- 分析表统计信息
ANALYZE expert_logs;
ANALYZE log_chunks;
```

#### 3. 清理任务
```sql
-- 清理过期的草稿记录（超过30天）
DELETE FROM expert_logs 
WHERE log_status = 'draft' 
AND created_at < NOW() - INTERVAL '30 days';

-- 清理孤立的文本块
DELETE FROM log_chunks 
WHERE log_id NOT IN (SELECT log_id FROM expert_logs);
```

### 性能监控

#### 1. 查询性能监控
```sql
-- 查看慢查询
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- 查看索引使用情况
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

#### 2. 连接监控
```sql
-- 查看当前连接数
SELECT count(*) as connection_count
FROM pg_stat_activity
WHERE state = 'active';

-- 查看长时间运行的查询
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';
```

#### 3. 存储监控
```sql
-- 查看表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 查看数据库总大小
SELECT pg_size_pretty(pg_database_size('wind_whisper_rag'));
```

### 故障排除

#### 1. 常见问题

**连接问题**:
```bash
# 检查PostgreSQL服务状态
systemctl status postgresql

# 检查端口监听
netstat -tlnp | grep 5432
```

**性能问题**:
```sql
-- 检查锁等待
SELECT * FROM pg_locks WHERE NOT granted;

-- 检查表膨胀
SELECT schemaname, tablename, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000;
```

**向量检索问题**:
```sql
-- 检查pgvector扩展
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 重建向量索引
DROP INDEX IF EXISTS idx_log_chunks_embedding;
CREATE INDEX idx_log_chunks_embedding ON log_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
```

#### 2. 应急处理

**数据恢复**:
```bash
# 从备份恢复
psql -h localhost -U postgres -d wind_whisper_rag < backup_20240120.sql
```

**性能调优**:
```sql
-- 临时增加工作内存
SET work_mem = '256MB';

-- 强制重新计划查询
SET enable_seqscan = off;
```

---

## 📝 总结

Wind Whisper RAG System的数据库设计充分考虑了以下关键因素：

### 设计优势
1. **模块化设计**: 清晰的表结构分离，便于维护和扩展
2. **AI友好**: 原生支持向量存储和JSON数据类型
3. **性能优化**: 合理的索引设计和查询优化
4. **数据完整性**: 完善的外键约束和业务规则
5. **可扩展性**: 支持水平和垂直扩展的架构设计

### 技术特色
- **向量数据库**: 使用pgvector扩展支持语义检索
- **时间线分析**: AI驱动的事件时间线自动生成
- **多媒体支持**: 完整的附件管理和文本提取
- **版本控制**: 支持草稿和发布状态的内容管理

### 应用场景
- 风机运维知识管理
- 专家经验数字化
- 智能故障诊断
- 历史数据分析
- 知识检索和问答

该数据库设计为Wind Whisper RAG System提供了坚实的数据基础，支持系统的核心功能需求，并为未来的功能扩展预留了充分的空间。

---

*文档版本: v1.0*  
*最后更新: 2024年1月*  
*维护团队: Wind Whisper Development Team*