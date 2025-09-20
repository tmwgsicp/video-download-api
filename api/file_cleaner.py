"""
文件清理管理器
负责定期清理临时文件，避免磁盘空间占用过多
"""

import os
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)

class FileCleanerManager:
    """文件清理管理器"""
    
    def __init__(self, temp_dir: Path, config: Dict = None):
        """
        初始化文件清理管理器
        
        Args:
            temp_dir: 临时文件目录
            config: 清理配置
        """
        self.temp_dir = temp_dir
        self.config = config or self._get_default_config()
        self.is_running = False
        
    def _get_default_config(self) -> Dict:
        """获取默认清理配置"""
        return {
            'enabled': True,
            'check_interval': 3600,  # 检查间隔(秒) - 1小时
            'file_retention_hours': 24,  # 文件保留时间(小时) - 24小时
            'max_storage_mb': 1000,  # 最大存储空间(MB) - 1GB
            'cleanup_on_startup': True,  # 启动时清理
            'preserve_recent_files': 10,  # 保留最近的文件数量
        }
    
    async def start_cleanup_service(self):
        """启动清理服务"""
        if not self.config.get('enabled', True):
            logger.info("文件清理服务已禁用")
            return
            
        self.is_running = True
        logger.info("🧹 启动文件清理服务")
        
        # 启动时清理
        if self.config.get('cleanup_on_startup', True):
            await self.cleanup_files()
        
        # 定期清理
        while self.is_running:
            try:
                await asyncio.sleep(self.config.get('check_interval', 3600))
                if self.is_running:
                    await self.cleanup_files()
            except Exception as e:
                logger.error(f"文件清理服务错误: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟再重试
    
    def stop_cleanup_service(self):
        """停止清理服务"""
        self.is_running = False
        logger.info("文件清理服务已停止")
    
    async def cleanup_files(self) -> Dict:
        """
        清理文件
        
        Returns:
            清理统计信息
        """
        try:
            logger.info("🔍 开始检查和清理文件...")
            
            if not self.temp_dir.exists():
                return {'status': 'no_temp_dir', 'message': '临时目录不存在'}
            
            # 获取所有文件信息
            files_info = self._get_files_info()
            if not files_info:
                return {'status': 'no_files', 'message': '没有文件需要清理'}
            
            # 执行清理策略
            cleanup_stats = await self._execute_cleanup_strategy(files_info)
            
            logger.info(f"✅ 文件清理完成: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            error_msg = f"文件清理失败: {str(e)}"
            logger.error(error_msg)
            return {'status': 'error', 'message': error_msg}
    
    def _get_files_info(self) -> List[Dict]:
        """获取所有文件信息"""
        files_info = []
        
        for file_path in self.temp_dir.glob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    stat = file_path.stat()
                    files_info.append({
                        'path': file_path,
                        'name': file_path.name,
                        'size': stat.st_size,
                        'modified_time': stat.st_mtime,
                        'age_hours': (time.time() - stat.st_mtime) / 3600
                    })
                except Exception as e:
                    logger.warning(f"获取文件信息失败 {file_path}: {e}")
        
        return files_info
    
    async def _execute_cleanup_strategy(self, files_info: List[Dict]) -> Dict:
        """执行清理策略"""
        stats = {
            'total_files': len(files_info),
            'deleted_files': 0,
            'freed_space_mb': 0,
            'preserved_files': 0,
            'strategy': []
        }
        
        # 按修改时间排序（最新的在前）
        files_info.sort(key=lambda x: x['modified_time'], reverse=True)
        
        # 策略1: 保留最近的文件
        preserve_count = self.config.get('preserve_recent_files', 10)
        preserved_files = files_info[:preserve_count]
        candidate_files = files_info[preserve_count:]
        
        stats['preserved_files'] = len(preserved_files)
        stats['strategy'].append(f"保留最近{preserve_count}个文件")
        
        # 策略2: 按时间清理
        retention_hours = self.config.get('file_retention_hours', 24)
        old_files = [f for f in candidate_files if f['age_hours'] > retention_hours]
        
        if old_files:
            stats['strategy'].append(f"清理{retention_hours}小时前的文件")
            for file_info in old_files:
                if await self._delete_file(file_info):
                    stats['deleted_files'] += 1
                    stats['freed_space_mb'] += file_info['size'] / (1024 * 1024)
        
        # 策略3: 按存储空间清理
        remaining_files = [f for f in candidate_files if f not in old_files]
        total_size_mb = sum(f['size'] for f in files_info) / (1024 * 1024)
        max_storage_mb = self.config.get('max_storage_mb', 1000)
        
        if total_size_mb > max_storage_mb and remaining_files:
            stats['strategy'].append(f"存储空间超过{max_storage_mb}MB，清理最老文件")
            # 按时间排序，删除最老的文件
            remaining_files.sort(key=lambda x: x['modified_time'])
            
            for file_info in remaining_files:
                if total_size_mb <= max_storage_mb:
                    break
                if await self._delete_file(file_info):
                    stats['deleted_files'] += 1
                    freed_mb = file_info['size'] / (1024 * 1024)
                    stats['freed_space_mb'] += freed_mb
                    total_size_mb -= freed_mb
        
        stats['freed_space_mb'] = round(stats['freed_space_mb'], 2)
        return stats
    
    async def _delete_file(self, file_info: Dict) -> bool:
        """删除文件"""
        try:
            file_path = file_info['path']
            file_path.unlink()
            logger.info(f"🗑️ 已删除文件: {file_info['name']} ({file_info['size']/1024/1024:.1f}MB)")
            return True
        except Exception as e:
            logger.warning(f"删除文件失败 {file_info['name']}: {e}")
            return False
    
    def get_storage_info(self) -> Dict:
        """获取存储信息"""
        if not self.temp_dir.exists():
            return {'status': 'no_temp_dir'}
        
        files_info = self._get_files_info()
        total_size = sum(f['size'] for f in files_info)
        
        return {
            'total_files': len(files_info),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_file_hours': max([f['age_hours'] for f in files_info], default=0),
            'newest_file_hours': min([f['age_hours'] for f in files_info], default=0),
            'temp_dir': str(self.temp_dir)
        }
