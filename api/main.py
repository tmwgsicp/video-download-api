from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict
import uuid
import json
import re
import yaml
from datetime import datetime
from pydantic import BaseModel

from .video_processor import VideoProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="视频下载API",
    description="简单的视频下载和音频提取API服务",
    version="3.0.0"
)

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    await startup_cookies_check()

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 创建临时目录
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# 初始化cookies管理器
try:
    from .cookies_manager import CookiesManager
    cookies_manager = CookiesManager()
except ImportError as e:
    logger.warning(f"Cookies管理器导入失败: {e}，使用简化版本")
    cookies_manager = None

# 初始化文件清理管理器
try:
    from .file_cleaner import FileCleanerManager
    file_cleaner = FileCleanerManager(TEMP_DIR)
except ImportError as e:
    logger.warning(f"文件清理管理器导入失败: {e}，禁用文件清理功能")
    file_cleaner = None

# 启动时检查cookies状态
async def startup_cookies_check():
    """启动时检查cookies状态"""
    try:
        if cookies_manager is None:
            logger.info("📝 Cookies管理器未初始化，跳过cookies检查")
            return
            
        logger.info("🔍 启动时检查cookies状态...")
        check_results = await cookies_manager.check_all_cookies()
        
        # 打印状态报告
        status_report = cookies_manager.get_status_report()
        for line in status_report.split('\n'):
            logger.info(line)
        
        # 启动定期检查
        asyncio.create_task(cookies_manager.start_periodic_check())
        
        # 启动文件清理服务
        if file_cleaner is not None:
            asyncio.create_task(file_cleaner.start_cleanup_service())
        
    except Exception as e:
        logger.error(f"启动时cookies检查失败: {e}")

# 不再使用全局处理器，改为动态创建
# video_processor = VideoProcessor()

# API请求和响应模型
class ProcessVideoRequest(BaseModel):
    url: str
    extract_audio: bool = True
    keep_video: bool = True

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # processing, completed, error
    progress: int
    message: str
    created_at: str
    completed_at: Optional[str] = None
    files: Optional[Dict[str, str]] = None  # 文件类型到下载链接的映射
    video_info: Optional[Dict] = None
    error: Optional[str] = None

class ProcessVideoResponse(BaseModel):
    task_id: str
    message: str
    status_url: str

# 存储任务状态
import threading

TASKS_FILE = TEMP_DIR / "tasks.json"
tasks_lock = threading.Lock()

def load_tasks():
    """加载任务状态"""
    try:
        if TASKS_FILE.exists():
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_tasks(tasks_data):
    """保存任务状态"""
    try:
        with tasks_lock:
            with open(TASKS_FILE, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存任务状态失败: {e}")

# 启动时加载任务状态
tasks = load_tasks()
processing_urls = set()
active_tasks = {}

def _sanitize_filename(title: str) -> str:
    """将视频标题清洗为安全的文件名"""
    if not title:
        return "untitled"
    # 仅保留字母数字、下划线、连字符与空格
    safe = re.sub(r"[^\w\-\s]", "", title)
    # 压缩空白并转为下划线
    safe = re.sub(r"\s+", "_", safe).strip("._-")
    # 最长限制
    return safe[:80] or "untitled"

@app.get("/")
async def read_root():
    """API服务根路径"""
    return {
        "service": "视频下载API",
        "version": "3.0.0",
        "description": "简单的视频下载和音频提取API服务",
        "endpoints": {
            "process": "POST /api/process - 处理视频链接",
            "status": "GET /api/status/{task_id} - 查询任务状态",
            "download": "GET /api/download/{file_id} - 下载文件",
            "health": "GET /api/health - 健康检查"
        },
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "video_processor": "available"
        }
    }

@app.post("/api/process", response_model=ProcessVideoResponse)
async def process_video(request: ProcessVideoRequest):
    """
    处理视频链接，下载视频和提取音频
    
    Args:
        request: 包含视频URL和处理选项的请求对象
        
    Returns:
        ProcessVideoResponse: 包含任务ID和状态查询URL
    """
    try:
        # 检查是否已经在处理相同的URL
        if request.url in processing_urls:
            # 查找现有任务
            for tid, task in tasks.items():
                if task.get("url") == request.url:
                    return ProcessVideoResponse(
                        task_id=tid,
                        message="该视频正在处理中，请等待...",
                        status_url=f"/api/status/{tid}"
                    )
            
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        
        # 标记URL为正在处理
        processing_urls.add(request.url)
        
        # 初始化任务状态
        tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "开始处理视频...",
            "created_at": datetime.now().isoformat(),
            "url": request.url,
            "extract_audio": request.extract_audio,
            "keep_video": request.keep_video,
            "files": {},
            "video_info": {},
            "error": None
        }
        save_tasks(tasks)
        
        # 创建并跟踪异步任务
        task = asyncio.create_task(process_video_task(
            task_id, 
            request.url, 
            request.extract_audio,
            request.keep_video
        ))
        active_tasks[task_id] = task
        
        return ProcessVideoResponse(
            task_id=task_id,
            message="任务已创建，正在处理中...",
            status_url=f"/api/status/{task_id}"
        )
        
    except Exception as e:
        logger.error(f"处理视频时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

async def process_video_task(task_id: str, url: str, extract_audio: bool = True, keep_video: bool = True):
    """
    异步处理视频任务
    """
    try:
        # 智能选择cookies文件
        cookies_file = cookies_manager.get_cookies_file_for_url(url)
        
        # 为此任务创建专用的VideoProcessor
        video_processor = VideoProcessor(cookies_file=cookies_file)
        logger.info(f"任务 {task_id}: 使用cookies文件 {cookies_file or '无'}")
        
        # 更新状态：获取视频信息
        tasks[task_id].update({
            "status": "processing",
            "progress": 10,
            "message": "正在获取视频信息..."
        })
        save_tasks(tasks)
        
        # 获取视频信息
        video_info = video_processor.get_video_info(url)
        tasks[task_id]["video_info"] = video_info
        
        # 更新状态：开始下载
        tasks[task_id].update({
            "progress": 20,
            "message": "正在下载视频..."
        })
        save_tasks(tasks)
        
        # 下载视频和提取音频
        result_files = await video_processor.download_video_and_audio(
            url, 
            TEMP_DIR, 
            extract_audio=extract_audio,
            keep_video=keep_video
        )
        
        # 生成下载链接
        file_links = {}
        short_id = task_id.replace("-", "")[:6]
        safe_title = _sanitize_filename(video_info.get('title', 'video'))
        
        for file_type, file_path in result_files.items():
            if file_path and Path(file_path).exists():
                filename = Path(file_path).name
                # 重命名文件以包含标题和短ID
                ext = Path(filename).suffix
                new_filename = f"{file_type}_{safe_title}_{short_id}{ext}"
                new_path = TEMP_DIR / new_filename
                
                try:
                    Path(file_path).rename(new_path)
                    file_links[file_type] = f"/api/download/{new_filename}"
                except Exception as e:
                    logger.warning(f"重命名文件失败: {e}")
                    file_links[file_type] = f"/api/download/{filename}"
        
        # 更新状态：完成
        tasks[task_id].update({
            "status": "completed",
            "progress": 100,
            "message": "处理完成！",
            "completed_at": datetime.now().isoformat(),
            "files": file_links
        })
        save_tasks(tasks)
        logger.info(f"任务完成: {task_id}")
        
        # 从处理列表中移除URL
        processing_urls.discard(url)
        
        # 从活跃任务列表中移除
        if task_id in active_tasks:
            del active_tasks[task_id]
            
    except Exception as e:
        logger.error(f"任务 {task_id} 处理失败: {str(e)}")
        # 从处理列表中移除URL
        processing_urls.discard(url)
        
        # 从活跃任务列表中移除
        if task_id in active_tasks:
            del active_tasks[task_id]
            
        tasks[task_id].update({
            "status": "error",
            "error": str(e),
            "message": f"处理失败: {str(e)}",
            "completed_at": datetime.now().isoformat()
        })
        save_tasks(tasks)

@app.get("/api/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务处理状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        TaskStatusResponse: 任务状态信息
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        message=task["message"],
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        files=task.get("files", {}),
        video_info=task.get("video_info", {}),
        error=task.get("error")
    )

@app.get("/api/download/{file_id}")
async def download_file(file_id: str):
    """
    下载文件
    
    Args:
        file_id: 文件ID（文件名）
        
    Returns:
        FileResponse: 文件下载响应
    """
    try:
        # 检查文件名格式（防止路径遍历攻击）
        if '..' in file_id or '/' in file_id or '\\' in file_id:
            raise HTTPException(status_code=400, detail="文件名格式无效")
            
        file_path = TEMP_DIR / file_id
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 根据文件扩展名设置媒体类型
        ext = file_path.suffix.lower()
        if ext in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
            media_type = "video/mp4"
        elif ext in ['.mp3', '.wav', '.m4a', '.aac', '.flac']:
            media_type = "audio/mpeg"
        else:
            media_type = "application/octet-stream"
            
        # 处理中文文件名编码问题
        import urllib.parse
        encoded_filename = urllib.parse.quote(file_id.encode('utf-8'))
        
        return FileResponse(
            file_path,
            filename=file_id,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@app.get("/api/cookies/status")
async def get_cookies_status():
    """
    获取所有平台cookies的状态
    
    Returns:
        cookies状态报告
    """
    try:
        # 获取状态报告
        status_report = cookies_manager.get_status_report()
        
        # 检查所有cookies
        check_results = await cookies_manager.check_all_cookies()
        
        return {
            "status": "success",
            "report": status_report,
            "details": {
                platform: {
                    "valid": is_valid,
                    "message": message
                }
                for platform, (is_valid, message) in check_results.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取cookies状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")

@app.post("/api/cookies/check")
async def check_cookies():
    """
    手动触发cookies检查
    
    Returns:
        检查结果
    """
    try:
        check_results = await cookies_manager.check_all_cookies()
        
        all_valid = all(is_valid for is_valid, _ in check_results.values())
        
        return {
            "status": "success" if all_valid else "warning",
            "message": "所有cookies正常" if all_valid else "部分cookies存在问题",
            "results": {
                platform: {
                    "valid": is_valid,
                    "message": message
                }
                for platform, (is_valid, message) in check_results.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"检查cookies失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")

@app.post("/api/cookies/webhook/test")
async def test_webhook_notification():
    """
    测试Webhook通知功能
    
    Returns:
        测试结果
    """
    try:
        # 发送测试消息
        test_message = "🧪 这是一条测试消息，用于验证Webhook通知功能是否正常工作"
        cookies_manager._send_notification(test_message, level='INFO')
        
        return {
            "status": "success",
            "message": "测试通知已发送",
            "webhook_configured": bool(cookies_manager.webhook_url),
            "webhook_url": cookies_manager.webhook_url[:50] + "..." if cookies_manager.webhook_url else None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"测试Webhook通知失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")

@app.post("/api/cookies/webhook/config")
async def update_webhook_config(webhook_url: str):
    """
    更新Webhook配置
    
    Args:
        webhook_url: 企微机器人Webhook URL
        
    Returns:
        配置结果
    """
    try:
        # 更新配置
        cookies_manager.webhook_url = webhook_url
        cookies_manager.notification_config['webhook_url'] = webhook_url
        
        # 保存到配置文件
        config_path = cookies_manager.config_path
        config = cookies_manager.config
        config['notifications']['webhook_url'] = webhook_url
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, ensure_ascii=False, indent=2)
        
        # 发送测试消息
        test_message = f"✅ Webhook配置已更新并测试成功！\n配置时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cookies_manager._send_notification(test_message, level='INFO')
        
        return {
            "status": "success",
            "message": "Webhook配置已更新",
            "webhook_url": webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新Webhook配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置失败: {str(e)}")

@app.delete("/api/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消并删除任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        删除确认消息
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 如果任务还在运行，先取消它
    if task_id in active_tasks:
        task = active_tasks[task_id]
        if not task.done():
            task.cancel()
            logger.info(f"任务 {task_id} 已被取消")
        del active_tasks[task_id]
    
    # 从处理URL列表中移除
    task_url = tasks[task_id].get("url")
    if task_url:
        processing_urls.discard(task_url)
    
    # 删除任务记录
    del tasks[task_id]
    save_tasks(tasks)
    return {"message": "任务已取消并删除"}

@app.get("/api/storage/info")
async def get_storage_info():
    """
    获取存储空间信息
    
    Returns:
        存储空间统计信息
    """
    try:
        storage_info = file_cleaner.get_storage_info()
        return {
            "status": "success",
            "storage": storage_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"获取存储信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取存储信息失败: {str(e)}")

@app.post("/api/storage/cleanup")
async def manual_cleanup():
    """
    手动触发文件清理
    
    Returns:
        清理结果统计
    """
    try:
        cleanup_result = await file_cleaner.cleanup_files()
        return {
            "status": "success",
            "cleanup_result": cleanup_result,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"手动清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

@app.get("/api/tasks")
async def list_tasks():
    """
    获取所有任务列表
    
    Returns:
        任务列表和统计信息
    """
    active_count = len(active_tasks)
    processing_count = len(processing_urls)
    
    # 返回任务概览
    task_summary = {}
    for task_id, task in tasks.items():
        task_summary[task_id] = {
            "status": task["status"],
            "progress": task["progress"],
            "message": task["message"],
            "created_at": task.get("created_at"),
            "completed_at": task.get("completed_at"),
            "video_info": task.get("video_info", {}),
            "files": task.get("files", {})
        }
    
    return {
        "active_tasks": active_count,
        "processing_urls": processing_count,
        "total_tasks": len(tasks),
        "tasks": task_summary
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)