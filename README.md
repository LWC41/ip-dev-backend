# IP开发平台 - 后端

FastAPI + SQLAlchemy + Celery 构建的 IP 开发平台后端服务。

## 技术栈

- FastAPI
- SQLAlchemy (ORM)
- PostgreSQL
- Celery (异步任务)
- Redis (消息队列)
- Meshy AI API (3D 生成)

## 快速开始

### 本地开发

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DATABASE_URL=postgresql://postgres:postgres@localhost/ipdev_db
export REDIS_URL=redis://localhost:6379/0
export MESHY_API_KEY=your_api_key

# 启动服务
uvicorn app.main:app --reload
```

### Docker 部署

```bash
cd ../infra
docker-compose up -d
```

## API 文档

启动服务后访问: http://localhost:8000/docs

## 主要 API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | /api/v1/users/register | 用户注册 |
| GET | /api/v1/users/me | 获取当前用户 |
| POST | /api/v1/projects | 创建项目 |
| GET | /api/v1/projects | 列出项目 |
| POST | /api/v1/characters | 创建角色 |
| POST | /api/v1/tasks | 创建任务 |
| GET | /api/v1/tasks/{id} | 获取任务状态 |

## 目录结构

```
backend/
├── app/
│   └── main.py     # 应用入口 (单文件架构)
├── tests/          # 测试
├── Dockerfile
└── requirements.txt
```
