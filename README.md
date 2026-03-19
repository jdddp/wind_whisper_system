# Wind Whisper RAG System

<!-- 项目标题和简介 -->
**风机专家知识检索增强生成系统**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue.svg)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


## 🚀 快速开始
### 📚 项目文档
- docs/*

### 📋 环境要求
- **Docker** : 容器化部署

### 🛠️ 安装步骤
#### Docker快速部署

```bash
# 克隆项目
git clone <repository-url>
cd wind_whisper_rag_system

# 复制环境配置
cp .env.example .env
# 编辑 .env 文件配置必要参数

# 使用Docker Compose启动
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### ✅ 验证部署

1. **访问Web界面**
   - 打开浏览器访问: http://localhost:8004
   - 系统将自动加载主界面
   - 默认管理员账户: `admin` / `admin123` 

### 🎒 备份机制

#### 备份方式
~~~bash
# 1、上传过的历史文档原件目录：./uploda
# 2、数据库文件本地化存储：./pg_data
# 综上，基于工程目录&docker环境，可直接备份，采用rsync的方式，备份脚本见./备份机制

# 循环模式：判断当前时刻据0点多久后，进入睡眠，直至时间到执行一次备份后；再次判断
sudo python3 ./备份机制/backup_rsync.py > ./logs/backup_rsync.log &
~~~
- 检查./logs/backup_rsync.log & ./logs/remote_sync_backup.log文件，确认备份是否成功

#### 备份后验证
~~~bash
'''
1 备份服务器版本docker compose版本不一致，注销docker-compose.yml内的指定gpu设置
deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              # count: all
              device_ids: ['0', '1']
              capabilities: [gpu]
'''

docker-compose up -d

'''
打开日志发现报错，因为备份用的账户，docker内部的数据库不存在这个权限，赋权即可：
Missing argument in printf at /usr/bin/pg_lsclusters line 131.
 * Starting PostgreSQL 14 database server
 * Error: The cluster is owned by user id 1002 which does not exist

 需要给./pd_data 赋权，先查看一下容器内部数据库的useid：
 '''
 (base) /path/to/wind_whisper_rag_system$ docker run --rm --entrypoint bash wind-whisper-rag:latest-with-postgres-external-access -c "id -u postgres"
'''
返回101
'''
sudo chown -R 101:101 ./pd_data
'''

docker-compose up -d
~~~

## 使用指南

### 1. 系统登录
- 默认管理员账户: `admin` / `admin123`
- 首次登录后请及时修改密码

### 2. 风机管理
- 在"风机管理"页面添加风机信息
- 支持风场名称、机组编号、型号等信息

### 3. 专家记录
- 创建监测记录，记录风机运行状态
- 系统自动生成AI摘要和标签
- 发布后的记录可用于RAG问答

<!-- ### 4. RAG问答
- 在"RAG问答"页面提出问题
- 系统基于历史记录提供智能答案
- 显示相关来源和相似度评分 -->

### 5. 时间线分析
- 默认显示所有风机的时间线概览
- 使用搜索框快速定位特定风机
- 通过状态筛选查看不同运行状态的风机
- 点击风机可查看详细的单机时间线
- 系统自动按状态优先级和最近更新时间排序

## 数据库设计

### 主要数据表
- `users`: 用户信息
- `turbines`: 风机信息
- `expert_logs`: 专家监测记录
- `log_chunks`: RAG文档分块
- `attachments`: 附件信息

## 📖 项目简介

**Wind Whisper RAG System** 是一个专为风力发电行业运维专家设计的智能知识管理和问答系统。系统集成了专家记录管理、智能问答、时间线分析和风机监控等核心功能，为风电运维提供全方位的智能化支持。

### 🎯 核心价值
- **知识沉淀**: 将专家的监测记录和运维经验进行结构化存储和管理
- **智能检索**: 基于RAG（Retrieval-Augmented Generation）技术，实现语义化知识检索
- **经验传承**: 通过AI问答系统，让新手快速获取专家经验
- **决策支持**: 为风机运维决策提供历史数据和智能分析支持
- **时间线分析**: 按状态优先级和时间顺序展示风机事件，便于趋势分析

### 🔧 技术特色
- **本地化部署**: 支持完全离线运行，保障数据安全
- **向量化检索**: 使用pgvector扩展实现高效的语义相似度搜索
- **多模态支持**: 支持文本、图片等多种类型的专家记录
- **实时分析**: 提供时间线视图和智能摘要功能
- **智能排序**: 按风机状态优先级和最近更新时间自动排序
- **响应式设计**: 支持桌面和移动端访问

## 🚀 主要功能

### 🎯 核心业务功能
- **专家记录管理**: 
  - 创建、编辑、发布风机监测记录和运维日志
  - 支持富文本编辑，可插入图片、音频等多媒体内容
  - 记录状态管理（提交→生成关联时间线事件->二次修改->发布），确保内容质量

- **RAG智能问答**: （做的不行）
  - 基于历史专家记录的智能问答系统
  - 支持自然语言查询，如"某型号风机常见故障有哪些？"
  - 提供答案来源追溯，显示相关记录和相似度评分
  - 上下文感知，支持多轮对话和追问
  
- **知识检索**: 
  - 高效的向量化语义检索，支持模糊匹配和同义词搜索
  - 多维度筛选：时间范围、风机型号、故障类型、专家等级
  - 全文搜索结合向量搜索，提供精准和相关的结果
  - 搜索结果排序和聚合，便于快速定位关键信息
  
- **时间线视图**: 
  - 按时间顺序展示风机监测记录和运维事件
  - 支持时间范围筛选和事件类型过滤
  - 可视化展示风机状态变化趋势
  - 关联事件分析，发现潜在的因果关系

### 📊 系统管理功能
- **风机资产管理**: 
  - 风机基础信息维护（风场、机组编号、型号、安装日期等）
  - 风机状态监控和运行参数记录
  - 维护计划管理和提醒功能
  - 风机性能分析和报表生成
  
- **用户权限管理**: 
  - 多角色权限控制（管理员、专家、普通用户）
    - 管理员
      - 新建、删除专家或普通用户
      - 信息新增权限
        - 风机、专家记录、时间线事件等
      - 信息删除权限
        - 风机（删除附属专家记录及时间线事件）
        - 专家记录（删除附属时间线事件）
        - 时间线事件
    - 专家
      - 新建、删除普通用户
      - 信息新增权限
        - 风机、专家记录、时间线事件等
    - 用户
      只读：驾驶舱、RAG问答、时间线

### 🤖 AI智能增强功能
- **自动内容分析**: 
  - AI自动生成记录摘要，提取关键信息
  - 智能标签提取，自动识别故障类型、严重程度、处理方案
  - 内容质量评估，提供改进建议
  

## 🏗️ 技术架构

### 🎨 架构设计理念
- **微服务架构**: 模块化设计，便于扩展和维护
- **前后端分离**: API优先设计，支持多端接入
- **数据驱动**: 基于向量数据库的智能检索
- **云原生**: 支持容器化部署和水平扩展

### 🔧 后端技术栈
- **FastAPI** (v0.104+): 
  
- **SQLAlchemy** (v2.0+): 
  
- **PostgreSQL** (v12+): 
  
- **pgvector** (v0.5+): 

### 🤖 AI/ML技术栈
- **Sentence Transformers** (v2.2+): 
  - 基于BERT的文本嵌入模型库
  - 支持中文语义理解和向量化
  
<!-- - **OpenAI API** (GPT-3.5/4): 
  - 业界领先的大语言模型服务
  - 支持文本生成、摘要、问答等任务
  - 可配置的API参数，控制输出质量
  - 支持流式输出，提升用户体验 -->

### 🔄 系统架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   API网关       │    │   业务服务层    │
│  (Bootstrap)    │◄──►│   (FastAPI)     │◄──►│   (Services)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI服务层      │    │   数据访问层    │    │   向量数据库    │
│  (Local LLM) │◄──►│   (SQLAlchemy)  │◄──►│   (pgvector)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 开发指南

### 项目结构
```
wind_whisper_rag_system/
├── api/                 # API路由
├── models/              # 数据模型
├── schemas/             # Pydantic模式
├── services/            # 业务服务
├── utils/               # 工具函数
├── static/              # 静态文件
├── scripts/             # 脚本文件
├── alembic/             # 数据库迁移
├── main.py              # 主应用
└── requirements.txt     # 依赖文件
```

### 添加新功能
1. 在 `models/` 中定义数据模型
2. 在 `schemas/` 中定义API模式
3. 在 `api/` 中实现路由
4. 在 `services/` 中实现业务逻辑


