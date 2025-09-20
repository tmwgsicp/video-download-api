#!/usr/bin/env python3
"""
视频下载API启动脚本
"""

import os
import sys
import subprocess
import socket
import psutil
from pathlib import Path

def check_dependencies():
    """检查核心依赖是否安装"""
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn", 
        "yt-dlp": "yt_dlp",
        "pydantic": "pydantic",
        "requests": "requests",
        "pyyaml": "yaml",
        "psutil": "psutil"
    }
    
    missing_packages = []
    for display_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(display_name)
    
    if missing_packages:
        print("❌ 缺少以下依赖包:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖已安装")
    return True

def check_ffmpeg():
    """检查FFmpeg是否安装"""
    try:
        subprocess.run(["ffmpeg", "-version"], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        print("✅ FFmpeg已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 未找到FFmpeg")
        print("请安装FFmpeg:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: sudo apt install ffmpeg")
        print("  Windows: 从官网下载 https://ffmpeg.org/download.html")
        return False

def create_temp_dir():
    """创建临时目录"""
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    print("✅ 临时目录已创建")

def check_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except socket.error:
            return False

def find_process_using_port(port):
    """查找占用端口的进程"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            try:
                process = psutil.Process(conn.pid)
                return process.pid, process.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return conn.pid, "未知进程"
    return None, None

def handle_port_conflict(port):
    """处理端口冲突"""
    print(f"⚠️  端口 {port} 已被占用")
    
    pid, process_name = find_process_using_port(port)
    if pid:
        print(f"📋 占用进程: {process_name} (PID: {pid})")
        
        # 如果是Python进程，很可能是之前启动的API服务
        if 'python' in process_name.lower():
            print("🤔 检测到可能是之前启动的API服务")
            choice = input("是否终止该进程并重新启动? (y/N): ").lower()
            
            if choice == 'y':
                try:
                    process = psutil.Process(pid)
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✅ 已终止进程 {pid}")
                    return True
                except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied) as e:
                    print(f"❌ 无法终止进程: {e}")
                    return False
        else:
            print(f"💡 请手动终止进程 {pid} 或使用其他端口")
    else:
        print("💡 请检查并释放端口，或使用其他端口")
    
    return False

def main():
    """主函数"""
    print("🚀 视频下载API启动检查")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 检查FFmpeg
    if not check_ffmpeg():
        print("⚠️  FFmpeg未安装，可能影响某些视频格式的音频提取")
    
    # 创建必要目录
    create_temp_dir()
    
    print("\n🎉 启动检查完成!")
    print("=" * 50)
    
    # 启动服务器
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    # 检查端口是否可用
    if not check_port_available(port):
        if not handle_port_conflict(port):
            print("❌ 无法启动服务，端口被占用")
            sys.exit(1)
    
    print(f"\n🌐 启动API服务器...")
    print(f"   地址: http://localhost:{port}")
    print(f"   健康检查: http://localhost:{port}/api/health")
    print(f"   API文档: http://localhost:{port}/docs")
    print(f"   按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        cmd = [
            sys.executable, "-m", "uvicorn", "api.main:app",
            "--host", host,
            "--port", str(port)
        ]
        
        # 开发模式启用热重载
        if "--dev" in sys.argv:
            cmd.append("--reload")
            print("🔧 开发模式 - 热重载已启用")
        else:
            print("🔒 生产模式 - 热重载已禁用")
        
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 服务已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
