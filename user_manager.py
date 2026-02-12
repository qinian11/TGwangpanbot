#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用户管理模块"""
import logging
from typing import Dict
from database import db
logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器"""
    
    def get_or_create_user(self, user_id: int, username: str = None, first_name: str = None) -> Dict:
        """获取或创建用户"""
        return db.get_or_create_user(user_id, username, first_name)
    
    def update_storage(self, user_id: int, size_change: int):
        """更新存储使用量"""
        user = db.get_user(user_id)
        if user:
            new_storage = max(0, (user.get('storage_used', 0) or 0) + size_change)
            db.update_user_storage(user_id, new_storage)


# 全局实例
user_manager = UserManager()
