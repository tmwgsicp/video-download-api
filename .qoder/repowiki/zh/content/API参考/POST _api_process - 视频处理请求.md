# POST /api/process - 视频处理请求

<cite>
**本文档中引用的文件**   
- [main.py](file://api/main.py)
- [README.md](file://README.md)
</cite>

## 目录
1. [接口概述](#接口概述)
2. [请求参数](#请求参数)
3. [请求示例](#请求示例)
4. [响应说明](#响应说明)
5. [异步处理机制](#异步处理机制)
6. [错误码说明](#错误码说明)
7. [处理流程图](#处理流程图)

## 接口概述
`POST /api/process` 接口用于提交视频下载和音频提取任务。客户端通过该接口提交包含视频链接和处理选项的JSON请求体，服务端接收后立即返回任务ID和状态查询URL，实际的视频处理在后台异步执行。

该接口基于 `ProcessVideoRequest` 模型接收请求参数，支持从抖音、B站、YouTube等30多个平台下载视频和提取音频。服务端使用yt-dlp和FFmpeg进行视频处理，并通过任务队列管理并发任务。

**Section sources**
- [main.py](file://api/main.py#L138-L182)
- [README.md](file://README.md#L48-L142)

## 请求参数
请求体为JSON格式，基于 `ProcessVideoRequest` 模型，包含以下字段：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | string | 是 | 无 | 视频链接，支持抖音、B站、YouTube等30+平台 |
| extract_audio | boolean | 否 | true | 是否提取音频，true为提取，false为不提取 |
| keep_video | boolean | 否 | true | 是否保留原始视频，true为保留，false为不保留 |

- **url**: 必填字段，指定要处理的视频页面链接或直接视频链接。
- **extract_audio**: 控制是否从视频中提取音频文件。当设置为true时，系统会尝试提取MP3等格式的音频文件。
- **keep_video**: 决定是否保留下载的原始视频文件。当设置为false且extract_audio为true时，系统会在提取音频后自动清理临时视频文件。

**Section sources**
- [main.py](file://api/main.py#L81-L84)
- [README.md](file://README.md#L48-L142)

## 请求示例
以下是使用不同平台链接的请求示例：

### 抖音视频处理
```json
{
  "url": "https://www.douyin.com/video/1234567890",
  "extract_audio": true,
  "keep_video": true
}
```

### B站视频处理
```json
{
  "url": "https://www.bilibili.com/video/BV1Xx411c7mD",
  "extract_audio": true,
  "keep_video": false
}
```

### YouTube视频处理
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "extract_audio": false,
  "keep_video": true
}
```

使用curl命令提交请求：
```bash
curl -X POST "http://localhost:8000/api/process" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
       "extract_audio": true,
       "keep_video": true
     }'
```

**Section sources**
- [README.md](file://README.md#L48-L142)
- [main.py](file://api/main.py#L138-L182)

## 响应说明
成功响应的状态码为202（已接受），表示任务已成功创建并开始处理。

### 成功响应
响应体基于 `ProcessVideoResponse` 模型，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| task_id | string | 唯一的任务ID，用于后续查询状态 |
| message | string | 任务状态描述信息 |
| status_url | string | 状态查询URL，格式为 `/api/status/{task_id}` |

示例响应：
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8",
  "message": "任务已创建，正在处理中...",
  "status_url": "/api/status/a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
}
```

### 重复任务响应
如果提交的视频链接已经在处理中，接口会返回现有任务的信息：
```json
{
  "task_id": "existing-task-id",
  "message": "该视频正在处理中，请等待...",
  "status_url": "/api/status/existing-task-id"
}
```

**Section sources**
- [main.py](file://api/main.py#L97-L100)
- [main.py](file://api/main.py#L179-L218)

## 异步处理机制
该接口采用异步处理机制，客户端提交任务后，服务端立即返回响应，实际的视频下载和音频提取在后台线程中执行。

### 处理流程
1. 客户端提交 `POST /api/process` 请求
2. 服务端验证参数并创建任务记录
3. 返回任务ID和状态查询URL（状态码202）
4. 客户端通过 `GET /api/status/{task_id}` 轮询任务状态
5. 服务端后台完成视频下载和音频提取
6. 任务完成后，状态查询接口返回最终结果

### 状态轮询
客户端需要定期轮询 `GET /api/status/{task_id}` 接口获取任务进度，直到状态变为"completed"或"error"。建议轮询间隔为2-5秒。

**Section sources**
- [main.py](file://api/main.py#L320-L367)
- [main.py](file://api/main.py#L215-L253)

## 错误码说明
接口可能返回以下错误码：

| 状态码 | 错误类型 | 说明 | 响应结构 |
|--------|----------|------|----------|
| 400 | 参数错误 | 请求参数无效或缺失必填字段 | `{ "detail": "错误描述" }` |
| 404 | 任务不存在 | 查询的状态任务ID不存在 | `{ "detail": "任务不存在" }` |
| 500 | 处理失败 | 服务器内部错误，视频处理失败 | `{ "detail": "处理失败: 错误信息" }` |

### 错误响应结构
```json
{
  "detail": "具体的错误信息"
}
```

常见错误情况：
- 400错误：url字段为空或格式不正确
- 500错误：FFmpeg未安装、网络连接问题、视频链接失效等

**Section sources**
- [main.py](file://api/main.py#L179-L218)
- [main.py](file://api/main.py#L320-L367)

## 处理流程图
```mermaid
flowchart TD
A[客户端] --> |POST /api/process| B[服务端]
B --> C{验证参数}
C --> |无效| D[返回400错误]
C --> |有效| E[检查URL是否已在处理]
E --> |是| F[返回现有任务信息]
E --> |否| G[生成任务ID]
G --> H[初始化任务状态]
H --> I[创建异步处理任务]
I --> J[返回202响应]
J --> K[客户端轮询状态]
K --> |GET /api/status/{task_id}| L[返回当前状态]
L --> M{任务完成?}
M --> |否| K
M --> |是| N[返回最终结果]
```

**Diagram sources **
- [main.py](file://api/main.py#L138-L182)
- [main.py](file://api/main.py#L215-L253)

**Section sources**
- [main.py](file://api/main.py#L138-L182)
- [main.py](file://api/main.py#L215-L253)