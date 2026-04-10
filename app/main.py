"""
IP开发Agent - 后端API服务
FastAPI + SQLAlchemy + Celery + Meshy API集成
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uuid
import os
import httpx
import json
from celery import Celery
from enum import Enum

# ============== 配置 ==============
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/ipdev_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
MESHY_API_KEY = os.getenv("MESHY_API_KEY", "")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# ============== 数据库配置 ==============
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============== Celery配置 ==============
celery_app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# ============== FastAPI应用 ==============
app = FastAPI(
    title="IP开发Agent API",
    description="全栈IP开发系统后端服务",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== 数据模型 ==============

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True)
    password_hash = Column(String(255))
    role = Column(String(20), default="user")
    api_key = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class IPProject(Base):
    __tablename__ = "ip_projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="draft")
    settings = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Character(Base):
    __tablename__ = "characters"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False)
    name = Column(String(50), nullable=False)
    personality = Column(Text)
    backstory = Column(Text)
    visual_config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    project_id = Column(String)
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

# 创建表
Base.metadata.create_all(bind=engine)

# ============== Pydantic模型 ==============

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    role: str
    api_key: Optional[str]
    created_at: datetime

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    fruit_type: str = Field(..., description="水果类型，如：龙眼、芒果等")
    target_audience: str = Field(..., description="目标受众")
    style: str = Field(..., description="风格：cute, cool, professional等")

class ProjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    status: str
    settings: Dict[str, Any]
    created_at: datetime

class CharacterCreate(BaseModel):
    project_id: str
    name: str
    personality: str
    backstory: str
    appearance: Dict[str, Any]

class CharacterResponse(BaseModel):
    id: str
    project_id: str
    name: str
    personality: str
    backstory: str
    visual_config: Dict[str, Any]
    created_at: datetime

class TaskCreate(BaseModel):
    project_id: Optional[str] = None
    task_type: str = Field(..., description="任务类型：generate_3d, generate_stickers, generate_video等")
    params: Dict[str, Any]

class TaskResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str]
    task_type: str
    status: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

# ============== 依赖注入 ==============

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    user = db.query(User).filter(User.api_key == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user

# ============== Meshy API集成 ==============

class MeshyClient:
    """Meshy API客户端"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.meshy.ai/v1"
    
    async def text_to_3d(
        self,
        prompt: str,
        style: str = "realistic"
    ) -> Dict[str, Any]:
        """文本转3D模型"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/text-to-3d",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "prompt": prompt,
                    "style": style
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def image_to_3d(
        self,
        image_url: str,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """图片转3D模型"""
        async with httpx.AsyncClient() as client:
            payload = {"image_url": image_url}
            if prompt:
                payload["prompt"] = prompt
            
            response = await client.post(
                f"{self.base_url}/image-to-3d",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tasks/{task_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.json()
    
    async def download_model(self, task_id: str) -> bytes:
        """下载3D模型"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/tasks/{task_id}/download",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.content

# ============== Celery异步任务 ==============

@celery_app.task
def generate_3d_model_task(task_id: str, params: Dict[str, Any]):
    """异步生成3D模型任务"""
    import asyncio

    async def _run():
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()
        db.close()

        if not task:
            return {"error": "Task not found"}

        try:
            meshy_client = MeshyClient(MESHY_API_KEY)

            # 根据参数选择生成方式
            if "prompt" in params:
                result = await meshy_client.text_to_3d(
                    prompt=params["prompt"],
                    style=params.get("style", "realistic")
                )
            elif "image_url" in params:
                result = await meshy_client.image_to_3d(
                    image_url=params["image_url"],
                    prompt=params.get("prompt")
                )
            else:
                raise ValueError("Invalid params: must provide prompt or image_url")

            # 轮询任务状态
            meshy_task_id = result["task_id"]
            while True:
                task_status = await meshy_client.get_task_status(meshy_task_id)
                if task_status["status"] in ["succeeded", "failed"]:
                    break
                await asyncio.sleep(5)

            if task_status["status"] == "succeeded":
                # 下载模型
                model_data = await meshy_client.download_model(meshy_task_id)

                # 保存模型到OSS
                model_url = save_model_to_oss(task_id, model_data)

                # 更新任务状态
                update_task_status(
                    task_id=task_id,
                    status="completed",
                    output_data={
                        "meshy_task_id": meshy_task_id,
                        "model_url": model_url,
                        "result": task_status
                    }
                )
            else:
                update_task_status(
                    task_id=task_id,
                    status="failed",
                    error_message=task_status.get("error", "Unknown error")
                )
        except Exception as e:
            update_task_status(
                task_id=task_id,
                status="failed",
                error_message=str(e)
            )

    asyncio.run(_run())

@celery_app.task
def generate_stickers_task(task_id: str, params: Dict[str, Any]):
    """异步生成表情包任务"""
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    db.close()

    try:
        # 调用图片生成API生成表情包
        expressions = params.get("expressions", [])
        base_prompt = params.get("base_prompt", "")
        
        sticker_urls = []
        for expr in expressions:
            prompt = f"{base_prompt}, {expr['prompt']}, emoji style, white background"
            # 这里可以集成stable diffusion或其他图片生成API
            image_url = generate_image(prompt)
            sticker_urls.append({
                "expression": expr["name"],
                "url": image_url
            })
        
        update_task_status(
            task_id=task_id,
            status="completed",
            output_data={"stickers": sticker_urls}
        )
    except Exception as e:
        update_task_status(
            task_id=task_id,
            status="failed",
            error_message=str(e)
        )

# ============== 辅助函数 ==============

def save_model_to_oss(task_id: str, model_data: bytes) -> str:
    """保存模型到对象存储"""
    # 实际实现根据你的OSS选择
    # 这里简化返回示例URL
    return f"https://your-bucket.oss.com/models/{task_id}.glb"

def generate_image(prompt: str) -> str:
    """生成图片"""
    # 集成图片生成API
    return f"https://your-bucket.oss.com/images/{uuid.uuid4()}.png"

def update_task_status(task_id: str, status: str, 
                      output_data: Optional[Dict] = None,
                      error_message: Optional[str] = None):
    """更新任务状态"""
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.status = status
        if output_data:
            task.output_data = output_data
        if error_message:
            task.error_message = error_message
        if status == "completed":
            task.completed_at = datetime.utcnow()
        db.commit()
    db.close()

# ============== API路由 ==============

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "IP开发Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

# ============== 用户管理 ==============

@app.post("/api/v1/users/register", response_model=UserResponse)
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查用户名是否存在
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # 创建用户
    api_key = f"sk_{uuid.uuid4().hex}"
    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=user.password,  # 实际应该hash
        api_key=api_key
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.get("/api/v1/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

# ============== IP项目管理 ==============

@app.post("/api/v1/projects", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建IP项目"""
    new_project = IPProject(
        user_id=current_user.id,
        name=project.name,
        description=project.description,
        settings={
            "fruit_type": project.fruit_type,
            "target_audience": project.target_audience,
            "style": project.style
        }
    )
    
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    return new_project

@app.get("/api/v1/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出用户的所有项目"""
    projects = db.query(IPProject).filter(
        IPProject.user_id == current_user.id
    ).all()
    return projects

@app.get("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    project = db.query(IPProject).filter(
        IPProject.id == project_id,
        IPProject.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project

@app.put("/api/v1/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新项目"""
    project = db.query(IPProject).filter(
        IPProject.id == project_id,
        IPProject.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for key, value in project_update.items():
        if hasattr(project, key):
            setattr(project, key, value)
    
    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    
    return project

# ============== 角色管理 ==============

@app.post("/api/v1/characters", response_model=CharacterResponse)
async def create_character(
    character: CharacterCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建角色"""
    # 验证项目所有权
    project = db.query(IPProject).filter(
        IPProject.id == character.project_id,
        IPProject.user_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    new_character = Character(
        project_id=character.project_id,
        name=character.name,
        personality=character.personality,
        backstory=character.backstory,
        visual_config=character.appearance
    )
    
    db.add(new_character)
    db.commit()
    db.refresh(new_character)
    
    return new_character

@app.get("/api/v1/projects/{project_id}/characters", response_model=List[CharacterResponse])
async def list_characters(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出项目的所有角色"""
    characters = db.query(Character).filter(
        Character.project_id == project_id
    ).all()
    return characters

# ============== 任务管理 ==============

@app.post("/api/v1/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建任务"""
    new_task = Task(
        user_id=current_user.id,
        project_id=task.project_id,
        task_type=task.task_type,
        input_data=task.params,
        status="pending"
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # 根据任务类型分发到不同的Celery任务
    if task.task_type == "generate_3d":
        generate_3d_model_task.delay(str(new_task.id), task.params)
    elif task.task_type == "generate_stickers":
        generate_stickers_task.delay(str(new_task.id), task.params)
    elif task.task_type == "generate_video":
        generate_video_task.delay(str(new_task.id), task.params)
    
    return new_task

@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务状态"""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@app.get("/api/v1/tasks", response_model=List[TaskResponse])
async def list_tasks(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出任务"""
    query = db.query(Task).filter(Task.user_id == current_user.id)
    
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    tasks = query.order_by(Task.created_at.desc()).limit(50).all()
    return tasks

# ============== 启动 ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
