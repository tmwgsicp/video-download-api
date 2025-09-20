# 视频下载API

一款简单高效的视频下载API服务，支持从YouTube、Bilibili、TikTok等25+平台下载视频文件和提取音频文件。

## ✨ 功能特性

- 🎥 **多平台支持**: 支持YouTube、Bilibili、TikTok等25+平台
- 📹 **视频下载**: 高质量视频文件下载，支持多种格式
- 🎵 **音频提取**: 从视频中提取高质量MP3音频文件，支持智能回退机制
- 🚀 **RESTful API**: 提供完整的API接口，支持异步处理和文件下载
- 📦 **简单部署**: 支持自动安装和手动安装，轻量级Python部署
- ☁️ **云服务器友好**: 轻量级设计，适合云服务器部署
- ⚡ **高性能**: 基于FastAPI和yt-dlp，处理速度快
- 🔒 **安全可靠**: 文件安全管理，防止路径遍历攻击

## 🚀 快速开始

### 环境要求

- **Python 3.8+** 
- **FFmpeg** （音频提取必需）

### 🎯 部署方式选择

#### 🖥️ 生产环境部署（推荐）

**Linux/Ubuntu 系统**：
```bash
git clone https://github.com/tmwgsicp/video-download-api.git
cd video-download-api
chmod +x deploy.sh
./deploy.sh
```

**Windows 系统**：
```cmd
# 1. 克隆项目
git clone https://github.com/tmwgsicp/video-download-api.git
cd video-download-api

# 2. 运行安装脚本
双击运行 install.bat
```

**FFmpeg安装**（音频提取功能）：
```cmd
# 下载FFmpeg
访问: https://ffmpeg.org/download.html#build-windows
下载: Windows版本的FFmpeg

# 安装步骤
1. 解压到 C:\ffmpeg\
2. 添加 C:\ffmpeg\bin 到系统PATH环境变量
3. 重启命令提示符验证: ffmpeg -version
```

**启动服务**：
```cmd
# 启动API服务
双击运行 run.bat

# 重要提示
- 保持CMD窗口打开，关闭窗口将停止服务
- 使用 Ctrl+C 可以优雅停止服务
- 服务日志会实时显示在窗口中
```

**生产环境建议**：
- **防火墙设置**: 允许Python访问网络
- **端口管理**: 确保8000端口未被占用
- **服务监控**: 可以使用任务计划程序设置开机自启
- **日志管理**: 考虑将日志重定向到文件

**常见问题**：
- **端口占用**: 使用 `netstat -ano | findstr :8000` 检查
- **Python环境**: 确保Python 3.8+已安装并添加到PATH
- **依赖安装失败**: 检查网络连接，脚本会自动尝试中国镜像

#### 🔧 开发环境安装

适合开发者和需要自定义配置的用户：

```bash
# 1. 克隆项目
git clone https://github.com/tmwgsicp/video-download-api.git
cd video-download-api

# 2. 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate.bat  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装FFmpeg
# Ubuntu/Debian: sudo apt install ffmpeg
# macOS: brew install ffmpeg
# Windows: 从 https://ffmpeg.org 下载并添加到PATH

# 5. 启动服务
python start.py
```

### 🌐 访问服务

服务启动后，访问：
- **主页**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health

## 📖 API使用指南

### 基本流程

1. **提交任务** → 2. **查询状态** → 3. **下载文件**

### API接口

#### 1. 健康检查
```http
GET /api/health
```

#### 2. 提交视频处理任务
```http
POST /api/process
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=example",
  "extract_audio": true,    // 是否提取音频
  "keep_video": true        // 是否保留视频
}
```

**响应：**
```json
{
  "task_id": "uuid-string",
  "message": "任务已创建，正在处理中..."
}
```

#### 3. 查询任务状态
```http
GET /api/status/{task_id}
```

**响应：**
```json
{
  "status": "completed",
  "progress": 100,
  "message": "处理完成！",
  "video_title": "视频标题",
  "video_file": "video_abc123.mp4",
  "audio_file": "audio_abc123.mp3"
}
```

#### 4. 下载文件
```http
GET /api/download/{filename}
```

### 使用场景

#### 🎬 同时下载视频和音频
```bash
curl -X POST "http://localhost:8000/api/process" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
       "extract_audio": true,
       "keep_video": true
     }'
```

#### 🎵 只提取音频
```bash
curl -X POST "http://localhost:8000/api/process" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
       "extract_audio": true,
       "keep_video": false
     }'
```

#### 📹 只下载视频
```bash
curl -X POST "http://localhost:8000/api/process" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
       "extract_audio": false,
       "keep_video": true
     }'
```

### Python测试脚本
```bash
# 测试所有场景
python3 test_all_scenarios.py --url "视频链接"

# 测试特定场景
python3 test_all_scenarios.py --url "视频链接" --scenario 1  # 视频+音频
python3 test_all_scenarios.py --url "视频链接" --scenario 2  # 仅视频
python3 test_all_scenarios.py --url "视频链接" --scenario 3  # 仅音频
```

## 🛠️ 技术架构

### 技术栈
- **FastAPI**: 现代化的Python Web框架
- **yt-dlp**: 视频下载和处理，支持25+平台
- **FFmpeg**: 音视频处理工具
- **Pydantic**: 数据验证和序列化

### 智能音频提取策略
- **优先策略**: 使用yt-dlp直接提取音频流（速度快）
- **回退机制**: 直接提取失败时，下载视频后用FFmpeg提取音频
- **自动清理**: 仅需音频时，自动删除临时视频文件

### 项目结构
```
video-download-api/
├── api/                        # API服务代码
│   ├── __init__.py
│   ├── main.py                 # FastAPI主应用
│   ├── video_processor.py      # 视频处理模块
│   └── file_cleaner.py         # 文件清理管理
├── temp/                       # 临时文件目录（运行时创建）
├── requirements.txt            # Python依赖
├── start.py                   # 启动脚本
├── deploy.sh                  # Linux一键部署脚本
├── install.bat                # Windows一键部署脚本
├── run.bat                    # Windows启动脚本
├── test_all_scenarios.py      # 全功能测试脚本
└── README.md                  # 项目文档
```


## 🌍 支持平台

### ✅ 支持的平台
- **YouTube** - 全球最大视频平台
- **Bilibili** - 中国知名视频网站
- **TikTok** - 短视频平台
- **Twitter/X** - 社交媒体视频
- **Instagram** - 图片和视频社交
- **小红书** - 生活方式分享平台
- **Facebook、Vimeo、Dailymotion** 等25+个平台

详见 [yt-dlp支持列表](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

### ❌ 暂不支持的平台
- **抖音(Douyin)** - 由于反爬限制严格，暂时无法支持
  - 尝试访问抖音链接时会提示："抖音平台由于反爬限制暂时不支持，建议使用其他平台的视频"
  - 建议使用TikTok或其他平台的类似内容

## 📈 性能说明

### 处理速度
- **短视频** (1-5分钟): 通常30秒-2分钟完成
- **中等视频** (5-30分钟): 通常2-10分钟完成
- **长视频** (30分钟+): 时间较长，建议在稳定网络环境下处理

### 资源占用
- **内存占用**: 约200MB-1GB（处理过程中）
- **磁盘空间**: 临时文件会自动清理
- **网络带宽**: 取决于视频大小和画质

### 并发处理
- 支持多个任务同时处理
- 每个任务独立处理，互不影响

## 🔧 常见问题

### Q: 视频下载速度慢怎么办？
A: 下载速度取决于视频长度、画质和网络状况。可以尝试：
- 检查网络连接
- 更换网络或VPN
- 选择较低画质的视频源

### Q: 音频提取失败怎么办？
A: 系统采用智能回退策略：
1. 优先使用yt-dlp直接提取音频流
2. 失败时自动下载视频，再用FFmpeg提取音频
3. 确保在各种情况下都能成功提取音频

### Q: 为什么不支持抖音？
A: 抖音平台的反爬机制非常严格，即使使用最新的cookies也会很快失效。经过测试，yt-dlp一直提示需要"Fresh cookies"，说明cookies很快就会过期。为了避免给用户带来困扰，我们暂时移除了抖音支持，建议使用TikTok等其他平台。


## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用 Apache 2.0 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

### 源项目
本项目基于 [AI-Video-Transcriber](https://github.com/wendy7756/AI-Video-Transcriber) 项目进行构建，感谢原作者 **Wendy** 的开源贡献。

### 技术依赖
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载工具
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [FFmpeg](https://ffmpeg.org/) - 多媒体处理工具包

## 📞 联系与交流

### 💬 技术交流与学习指导

如果你在部署过程中遇到问题，或者想要学习更多关于AI自动化、AI工作流的技术，欢迎添加我的联系方式进行交流：

<div align="center">
  <img src="contact.jpg" alt="联系方式" width="300">
  <p><em>扫码添加联系方式，获取技术支持和学习指导</em></p>
</div>

## ☕ 支持项目

如果这个项目对你有帮助，欢迎请我喝杯奶茶！你的支持是我持续更新和维护项目的动力。

<div align="center">
  <img src="donate.jpg" alt="赞赏码" width="300">
  <p><em>感谢你的支持与鼓励！</em></p>
</div>

### 🙏 其他支持方式

- ⭐ 给项目一个 Star
- 🐛 提交 Bug 报告和改进建议  
- 📢 向朋友推荐这个项目
- 🔧 贡献代码和文档

---

**⭐ 如果这个项目对你有帮助或启发，请给个Star支持一下！**