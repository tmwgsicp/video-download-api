"""
Cookies管理器
负责cookies文件的管理、有效性检测和过期提醒
"""

import os
import re
import yaml
import time
import logging
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import yt_dlp

logger = logging.getLogger(__name__)

class CookiesManager:
    """Cookies管理器"""
    
    def __init__(self, config_path: str = "cookies/config.yaml"):
        """
        初始化cookies管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.cookies_dir = self.config_path.parent
        self.config = self._load_config()
        self.last_check_time = {}
        self._setup_notification()
        
    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"配置文件不存在: {self.config_path}")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'platforms': {
                'douyin': {
                    'name': '抖音',
                    'cookies_file': 'douyin.txt',
                    'required': True,
                    'check_interval': 3600,
                    'expiry_warning_days': 3
                }
            },
            'notifications': {
                'enabled': True,
                'methods': ['log', 'file'],
                'log_level': 'WARNING',
                'notification_file': 'cookies_notifications.log'
            },
            'health_check': {
                'enabled': True,
                'startup_check': True,
                'periodic_check': True,
                'check_on_error': True
            }
        }
    
    def _setup_notification(self):
        """设置通知系统"""
        self.notification_config = self.config.get('notifications', {})
        self.notification_file = self.cookies_dir / self.notification_config.get(
            'notification_file', 'cookies_notifications.log'
        )
        self.webhook_url = self.notification_config.get('webhook_url')
        
    def get_platform_from_url(self, url: str) -> str:
        """从URL识别平台"""
        if 'bilibili.com' in url:
            return 'bilibili'
        elif 'douyin.com' in url or 'v.douyin.com' in url:
            return 'douyin'
        elif 'xiaohongshu.com' in url:
            return 'xiaohongshu'
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 'youtube'
        elif 'tiktok.com' in url:
            return 'tiktok'
        else:
            return 'generic'
    
    def get_cookies_file_for_url(self, url: str) -> Optional[str]:
        """
        根据URL获取对应的cookies文件路径
        
        Args:
            url: 视频URL
            
        Returns:
            cookies文件路径，如果不需要或不存在则返回None
        """
        platform = self.get_platform_from_url(url)
        platform_config = self.config['platforms'].get(platform)
        
        if not platform_config:
            return None
            
        cookies_filename = platform_config.get('cookies_file')
        if not cookies_filename:
            return None
            
        cookies_file = self.cookies_dir / cookies_filename
        
        if not cookies_file.exists():
            if platform_config.get('required', False):
                logger.error(f"{platform_config.get('name', platform)}平台需要cookies文件: {cookies_file}")
                self._notify_missing_cookies(platform, str(cookies_file))
            return None
        
        # 处理cookies文件格式并返回处理后的路径
        processed_file = self._process_cookies_file(str(cookies_file))
        return processed_file
    
    def check_cookies_validity(self, platform: str) -> Tuple[bool, str]:
        """
        检查指定平台cookies的有效性
        
        Args:
            platform: 平台名称
            
        Returns:
            (是否有效, 状态消息)
        """
        platform_config = self.config['platforms'].get(platform)
        if not platform_config:
            return True, "平台不需要cookies"
            
        cookies_filename = platform_config.get('cookies_file')
        if not cookies_filename:
            return True, "平台不需要cookies"
            
        cookies_file = self.cookies_dir / cookies_filename
        
        if not cookies_file.exists():
            if platform_config.get('required', False):
                return False, f"缺少必需的cookies文件: {cookies_file}"
            return True, "可选cookies文件不存在"
        
        # 检查文件修改时间
        try:
            file_stat = cookies_file.stat()
            file_age_hours = (time.time() - file_stat.st_mtime) / 3600
            
            # 如果文件超过7天，可能需要更新
            if file_age_hours > 168:  # 7天
                return False, f"cookies文件可能过期 (已存在{file_age_hours:.1f}小时)"
            
            # 尝试使用yt-dlp验证cookies
            return self._test_cookies_with_ytdlp(platform, str(cookies_file))
            
        except Exception as e:
            return False, f"检查cookies文件时出错: {e}"
    
    def _process_cookies_file(self, cookies_file_path: str) -> str:
        """
        处理cookies文件，支持多种格式，包括完整的浏览器cookies字符串
        
        Args:
            cookies_file_path: cookies文件路径
            
        Returns:
            处理后的cookies文件路径
        """
        try:
            with open(cookies_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 如果已经是Netscape格式，直接返回
            if content.startswith('# Netscape HTTP Cookie File'):
                return cookies_file_path
            
            # 如果是cookies字符串，转换为Netscape格式
            if content and not content.startswith('#'):
                # 创建临时的Netscape格式文件
                temp_file = Path(cookies_file_path).with_suffix('.netscape.txt')
                
                # 检测平台以确定域名
                platform = self._detect_platform_from_path(cookies_file_path)
                domain_map = {
                    'douyin': '.douyin.com',
                    'bilibili': '.bilibili.com', 
                    'xiaohongshu': '.xiaohongshu.com'
                }
                domain = domain_map.get(platform, '.douyin.com')
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write('# Netscape HTTP Cookie File\n')
                    f.write('# This is a generated file! Do not edit.\n\n')
                    
                    # 解析完整的cookies字符串
                    cookies_parsed = self._parse_cookies_string(content)
                    
                    for name, value in cookies_parsed.items():
                        # 写入Netscape格式
                        # domain, flag, path, secure, expiration, name, value
                        f.write(f"{domain}\tTRUE\t/\tFALSE\t2147483647\t{name}\t{value}\n")
                
                logger.info(f"成功处理cookies文件，解析了 {len(cookies_parsed)} 个cookies")
                return str(temp_file)
            
            return cookies_file_path
            
        except Exception as e:
            logger.error(f"处理cookies文件失败: {e}")
            return cookies_file_path
    
    def _detect_platform_from_path(self, file_path: str) -> str:
        """从文件路径检测平台"""
        file_path = file_path.lower()
        if 'douyin' in file_path:
            return 'douyin'
        elif 'bilibili' in file_path:
            return 'bilibili'
        elif 'xiaohongshu' in file_path:
            return 'xiaohongshu'
        else:
            return 'douyin'  # 默认
    
    def _parse_cookies_string(self, cookies_string: str) -> dict:
        """
        解析完整的cookies字符串，支持浏览器直接复制的格式
        
        Args:
            cookies_string: 完整的cookies字符串
            
        Returns:
            解析后的cookies字典
        """
        cookies = {}
        
        try:
            # 处理完整的cookies字符串（浏览器复制格式）
            # 支持格式: name1=value1; name2=value2; name3=value3
            
            # 分割cookies
            cookie_parts = cookies_string.split(';')
            
            for part in cookie_parts:
                part = part.strip()
                if '=' in part:
                    try:
                        name, value = part.split('=', 1)
                        name = name.strip()
                        value = value.strip()
                        
                        # 过滤掉空值和无效cookies
                        if name and value and not name.startswith('__'):
                            cookies[name] = value
                            
                    except Exception as e:
                        logger.warning(f"跳过无效cookie部分: {part[:50]}...")
                        continue
            
            logger.info(f"成功解析cookies: {list(cookies.keys())[:10]}...")  # 只显示前10个
            
        except Exception as e:
            logger.error(f"解析cookies字符串失败: {e}")
            
        return cookies
    
    def _test_cookies_with_ytdlp(self, platform: str, cookies_file: str) -> Tuple[bool, str]:
        """
        使用yt-dlp测试cookies有效性
        
        Args:
            platform: 平台名称
            cookies_file: cookies文件路径
            
        Returns:
            (是否有效, 状态消息)
        """
        # 对于抖音平台，由于反爬虫机制严格，跳过实际测试
        if platform == 'douyin':
            # 只检查文件是否存在和基本格式
            try:
                processed_cookies_file = self._process_cookies_file(cookies_file)
                if os.path.exists(processed_cookies_file):
                    return True, "cookies文件存在（跳过在线验证）"
                else:
                    return False, "cookies文件处理失败"
            except Exception as e:
                return False, f"cookies文件处理错误: {e}"
        
        # 处理cookies文件格式
        processed_cookies_file = self._process_cookies_file(cookies_file)
        
        # 测试URL映射（移除抖音，避免测试失败影响其他平台）
        test_urls = {
            'bilibili': 'https://www.bilibili.com/',
            'xiaohongshu': 'https://www.xiaohongshu.com/'
        }
        
        test_url = test_urls.get(platform)
        if not test_url:
            return True, "无需测试"
            
        try:
            opts = {
                'quiet': True,
                'no_warnings': True,
                'cookiefile': processed_cookies_file,
                'extract_flat': True,
                'skip_download': True,
                'timeout': 10  # 添加超时限制，避免长时间等待
            }
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                # 尝试提取基本信息，不下载
                ydl.extract_info(test_url, download=False)
                
            return True, "cookies有效"
            
        except Exception as e:
            error_msg = str(e)
            if 'cookies' in error_msg.lower() or 'login' in error_msg.lower():
                return False, f"cookies无效或过期: {error_msg}"
            else:
                # 其他错误可能不是cookies问题，不影响服务运行
                return True, f"无法确定cookies状态（不影响使用）: {error_msg}"
    
    async def check_all_cookies(self) -> Dict[str, Tuple[bool, str]]:
        """
        检查所有平台的cookies状态
        
        Returns:
            各平台的检查结果
        """
        results = {}
        
        for platform in self.config['platforms']:
            try:
                is_valid, message = self.check_cookies_validity(platform)
                results[platform] = (is_valid, message)
                
                if not is_valid:
                    self._notify_cookies_issue(platform, message)
                    
            except Exception as e:
                error_msg = f"检查{platform}时出错: {e}"
                results[platform] = (False, error_msg)
                logger.error(error_msg)
        
        return results
    
    def _notify_missing_cookies(self, platform: str, cookies_file: str):
        """通知缺少cookies文件"""
        platform_config = self.config['platforms'].get(platform, {})
        platform_name = platform_config.get('name', platform)
        
        message = f"⚠️  缺少{platform_name}平台的cookies文件: {cookies_file}"
        self._send_notification(message, level='ERROR')
    
    def _notify_cookies_issue(self, platform: str, issue: str):
        """通知cookies问题"""
        platform_config = self.config['platforms'].get(platform, {})
        platform_name = platform_config.get('name', platform)
        
        message = f"🚨 {platform_name}平台cookies问题: {issue}"
        self._send_notification(message, level='WARNING')
    
    def _send_notification(self, message: str, level: str = 'INFO'):
        """发送通知"""
        if not self.notification_config.get('enabled', True):
            return
            
        methods = self.notification_config.get('methods', ['log'])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_message = f"[{timestamp}] {level}: {message}"
        
        # 日志通知
        if 'log' in methods:
            if level == 'ERROR':
                logger.error(message)
            elif level == 'WARNING':
                logger.warning(message)
            else:
                logger.info(message)
        
        # 文件通知
        if 'file' in methods:
            try:
                with open(self.notification_file, 'a', encoding='utf-8') as f:
                    f.write(formatted_message + '\n')
            except Exception as e:
                logger.error(f"写入通知文件失败: {e}")
        
        # Webhook通知
        if 'webhook' in methods and self.webhook_url:
            asyncio.create_task(self._send_webhook_notification(message, level))
    
    async def _send_webhook_notification(self, message: str, level: str = 'INFO'):
        """发送Webhook通知到企微机器人"""
        if not self.webhook_url:
            return
            
        try:
            # 根据级别选择颜色和图标
            color_map = {
                'ERROR': '🔴',
                'WARNING': '🟡', 
                'INFO': '🔵'
            }
            
            icon = color_map.get(level, '🔵')
            
            # 构造企微机器人消息格式
            webhook_data = {
                "msgtype": "text",
                "text": {
                    "content": f"{icon} 视频下载API - Cookies通知\n\n{message}\n\n时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
            
            # 发送webhook请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=webhook_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.info("Webhook通知发送成功")
                    else:
                        logger.error(f"Webhook通知发送失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"发送Webhook通知失败: {e}")
    
    async def start_periodic_check(self):
        """启动定期检查"""
        if not self.config.get('health_check', {}).get('periodic_check', True):
            return
            
        logger.info("启动cookies定期检查...")
        
        while True:
            try:
                current_time = time.time()
                
                for platform, config in self.config['platforms'].items():
                    check_interval = config.get('check_interval', 3600)
                    last_check = self.last_check_time.get(platform, 0)
                    
                    if current_time - last_check >= check_interval:
                        logger.info(f"检查{config.get('name', platform)}平台cookies...")
                        is_valid, message = self.check_cookies_validity(platform)
                        
                        if not is_valid:
                            self._notify_cookies_issue(platform, message)
                        
                        self.last_check_time[platform] = current_time
                
                # 每小时检查一次
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"定期检查时出错: {e}")
                await asyncio.sleep(300)  # 出错后5分钟重试
    
    def get_status_report(self) -> str:
        """获取cookies状态报告"""
        report_lines = ["📊 Cookies状态报告", "=" * 40]
        
        for platform, config in self.config['platforms'].items():
            platform_name = config.get('name', platform)
            is_valid, message = self.check_cookies_validity(platform)
            
            status_icon = "✅" if is_valid else "❌"
            required_text = " (必需)" if config.get('required', False) else " (可选)"
            
            report_lines.append(f"{status_icon} {platform_name}{required_text}: {message}")
        
        return '\n'.join(report_lines)
