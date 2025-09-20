# 🍪 Cookies配置完整指南

## 📋 支持的平台

| 平台 | 文件名 | 是否必需 | 说明 |
|------|--------|----------|------|
| 抖音 | `douyin.txt` | ✅ **必需** | 抖音平台强制需要cookies |
| 哔哩哔哩 | `bilibili.txt` | ❌ 可选 | 用于访问会员内容 |
| 小红书 | `xiaohongshu.txt` | ❌ 可选 | 用于访问受限内容 |

## 🚀 快速配置方法

### 一分钟快速配置
1. **登录目标网站** (如 www.douyin.com)
2. **按F12** 打开开发者工具
3. **点击Application标签** → Storage → Cookies → 选择网站
4. **复制完整的Cookie字符串** (推荐)
5. **粘贴到对应文件** 并保存

## 📁 支持的文件格式

### 格式1: 完整Cookie字符串 ⭐ **推荐**
直接复制浏览器中的完整Cookie字符串：
```
sessionid=abc123; csrf_token=def456; uid=789; sid_guard=xyz; other_cookie=value
```

### 格式2: 一行一个
每行一个cookie：
```
sessionid=abc123
csrf_token=def456
uid=789
```

### 格式3: Netscape格式 (自动生成)
系统会自动将上述格式转换为Netscape格式供yt-dlp使用。

## 🎯 各平台重要Cookies

### 抖音 (douyin.txt)
**核心必需字段**：
- `sessionid` - 会话ID (最重要)
- `sid_guard` - 安全令牌
- `uid_tt` - 用户ID  
- `sid_tt` - 会话令牌
- `ttwid` - 设备ID
- `passport_csrf_token` - CSRF令牌

**建议**：直接复制完整的Cookie字符串，系统会自动解析所有字段。

### B站 (bilibili.txt) - 可选
```
SESSDATA=你的session值; bili_jct=你的csrf值; DedeUserID=你的用户ID
```

### 小红书 (xiaohongshu.txt) - 可选
```
web_session=你的session值; xsecappid=你的appid值
```

## 🛠️ 详细获取方法

### Chrome浏览器 (推荐)
1. 登录目标网站并确保正常使用
2. 按 `F12` → `Application` → `Storage` → `Cookies`
3. 选择对应网站域名
4. **方法A**: 复制完整Cookie字符串
   - 按 `F12` → `Network` → 刷新页面
   - 点击任意请求 → `Headers` → `Request Headers` → `Cookie`
   - 复制完整的Cookie值
5. **方法B**: 逐个复制重要字段
   - 在Cookies列表中找到重要字段并复制

### 浏览器插件方法
推荐使用 "Get cookies.txt" 扩展：
1. 安装浏览器扩展
2. 登录目标网站
3. 点击扩展图标导出cookies
4. 保存为对应的文件名

## 📊 自动检测和管理

系统提供完整的cookies管理功能：

- ✅ **启动检查**: 服务启动时自动检查所有cookies
- 🔄 **定期检查**: 定期验证cookies有效性
- ⚠️ **过期提醒**: cookies即将过期时发送通知
- 📝 **日志记录**: 详细的检查和错误日志
- 🔄 **自动转换**: 自动转换为yt-dlp兼容的Netscape格式

## 🚨 重要注意事项

### 安全性
- cookies文件包含敏感登录信息，请妥善保管
- 建议设置文件权限为600（仅所有者可读写）
- 不要在公共场所或不安全的网络环境下获取cookies

### 有效期
- cookies有过期时间，通常几小时到几天
- 过期后需要重新获取
- 系统会自动检测并提醒更新

### 使用建议
- 优先使用完整Cookie字符串格式
- 确保在正常登录状态下获取cookies
- 更新cookies后系统会自动重新加载

## 🔧 故障排除

### 常见问题

**Q: 抖音视频下载失败，提示需要cookies**
- A: 检查`douyin.txt`文件是否存在且内容正确
- 确保cookies是在正常登录状态下获取的

**Q: cookies过期了怎么办？**
- A: 重新登录对应平台，获取新的cookies并更新文件
- 系统会自动检测更新并重新加载

**Q: 如何知道cookies是否过期？**
- A: 查看API日志或访问 `/api/cookies/status` 接口

**Q: 提示"Fresh cookies needed"**
- A: 这通常意味着：
  1. cookies已过期，需要重新获取
  2. 缺少某些关键字段
  3. 平台检测到自动化访问

### 调试步骤
1. 检查cookies文件格式是否正确
2. 确认登录状态是否有效
3. 查看系统日志获取详细错误信息
4. 尝试重新获取完整的cookies

## 📞 API接口

系统提供以下cookies管理接口：

- `GET /api/cookies/status` - 查看cookies状态
- `POST /api/cookies/check` - 手动检查cookies
- `POST /api/cookies/webhook/test` - 测试通知功能

## 🔄 更新流程

1. 获取新的cookies
2. 更新对应的文件 (如 `douyin.txt`)
3. 系统自动检测文件变化
4. 自动转换格式并重新加载
5. 验证新cookies的有效性

---

💡 **小贴士**: 建议定期更新cookies以确保服务稳定运行。系统会在cookies即将过期时主动提醒。


