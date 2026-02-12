#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件加载模块
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
class Config:
    """配置管理器"""
    _instance = None
    _config: Dict[str, Any] = {}
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    def _load_config(self):
        """加载配置文件"""
        config_paths = [
            'config.json',
            'config/config.json',
            os.path.join(os.path.dirname(__file__), 'config.json')
        ]
        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                    return
                except Exception as e:
                    print(f"加载配置文件失败: {e}")
        self._config = self._get_default_config()
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'name': 'Telegram网盘机器人',
            'version': '1.0.0',
            'telegram': {
                'token': '',
                'admin_id': 0,
                'channel_id': 0
            },
            'database': {
                'type': 'sqlite',
                'path': 'data/bot.db'
            },
            'redis': {
                'host': 'localhost',
                'port': 6379,
                'db': 0
            },
            'upload': {
                'max_file_size': 2000,
                'allowed_types': ['document', 'photo', 'video', 'audio'],
                'max_downloads_per_file': 0
            },
            'rate_limit': {
                'upload_per_user': 100,
                'download_per_user': 1000,
                'search_per_user': 50
            },
            'web_server': {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 8080
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': 'logs/bot.log'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        
        return value if value is not None else default
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    def reload(self):
        """重新加载配置"""
        self._load_config()
    @property
    def telegram_token(self) -> str:
        """获取Telegram Bot Token"""
        return self.get('telegram.token', '')
    @property
    def admin_id(self) -> int:
        """获取管理员ID"""
        return int(self.get('telegram.admin_id', 0))
    @property
    def channel_id(self) -> int:
        """获取频道ID"""
        return int(self.get('telegram.channel_id', 0))
    @property
    def database_path(self) -> str:
        """获取数据库路径"""
        return self.get('database.path', 'data/bot.db')
    @property
    def max_file_size(self) -> int:
        """获取最大文件大小(MB)"""
        return int(self.get('upload.max_file_size', 2000))
# 单例模式
config = Config()
