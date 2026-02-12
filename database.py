#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据库模块 - 极简版本"""
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, BigInteger, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from config_manager import config

logger = logging.getLogger(__name__)
# 数据库路径
db_path = config.get('database.path', 'data/bot.db')
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)
DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30
)
SessionFactory = sessionmaker(bind=engine)
Session = scoped_session(SessionFactory)
Base = declarative_base()
class File(Base):
    """文件模型"""
    __tablename__ = 'files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_uuid = Column(String(32), unique=True, nullable=False, index=True)
    file_id = Column(String(255), nullable=False)
    file_unique_id = Column(String(255), nullable=False)
    name = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100))
    extension = Column(String(20))
    size = Column(BigInteger, default=0)
    duration = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    channel_id = Column(BigInteger, nullable=False, index=True)
    channel_message_id = Column(BigInteger)
    
    owner_id = Column(BigInteger, nullable=False, index=True)
    owner_username = Column(String(255))
    
    download_count = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    share_expires_at = Column(DateTime)  # 分享链接过期时间
    created_at = Column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index('idx_files_active', 'is_active'),
    )
class User(Base):
    """用户模型"""
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    storage_used = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.now)

class ShareLink(Base):
    """分享链接模型（保留兼容）"""
    __tablename__ = 'share_links'
    id = Column(Integer, primary_key=True, autoincrement=True)
    link_code = Column(String(32), unique=True, nullable=False, index=True)
    file_uuid = Column(String(32), nullable=False, index=True)
    creator_id = Column(BigInteger, nullable=False)
    download_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
# 创建表
Base.metadata.create_all(engine)

@contextmanager
def session_scope():
    """数据库会话上下文"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
class Database:
    """数据库操作类"""
    @staticmethod
    def get_file(file_uuid: str) -> Optional[Dict]:
        """获取文件信息"""
        with session_scope() as s:
            f = s.query(File).filter(File.file_uuid == file_uuid, File.is_active == True).first()
            if f:
                if f.share_expires_at and f.share_expires_at < datetime.now():
                    return None
                return {
                    'file_uuid': f.file_uuid,
                    'file_id': f.file_id,
                    'name': f.name,
                    'file_type': f.file_type,
                    'size': f.size,
                    'duration': f.duration,
                    'width': f.width,
                    'height': f.height,
                    'channel_id': f.channel_id,
                    'channel_message_id': f.channel_message_id,
                    'owner_id': f.owner_id,
                    'download_count': f.download_count,
                    'view_count': f.view_count,
                    'share_expires_at': f.share_expires_at,
                    'created_at': f.created_at,
                }
            return None
    
    @staticmethod
    def add_file(info: Dict) -> str:
        """添加文件"""
        file_uuid = uuid.uuid4().hex[:16]
        with session_scope() as s:
            f = File(
                file_uuid=file_uuid,
                file_id=info['file_id'],
                file_unique_id=info.get('file_unique_id', ''),
                name=info['name'],
                file_type=info['file_type'],
                mime_type=info.get('mime_type'),
                extension=info.get('extension'),
                size=info['size'],
                duration=info.get('duration'),
                width=info.get('width'),
                height=info.get('height'),
                channel_id=info['channel_id'],
                channel_message_id=info.get('channel_message_id'),
                owner_id=info['owner_id'],
                owner_username=info.get('owner_username'),
            )
            s.add(f)
        return file_uuid
    
    @staticmethod
    def delete_file(file_uuid: str) -> bool:
        """删除文件"""
        with session_scope() as s:
            s.query(File).filter(File.file_uuid == file_uuid).update({'is_active': False})
        return True
    
    @staticmethod
    def clone_file(original_uuid: str, new_owner_id: int, new_owner_username: str) -> str:
        """克隆文件到新用户
        返回新的文件UUID
        """
        with session_scope() as s:
            original = s.query(File).filter(File.file_uuid == original_uuid, File.is_active == True).first()
            if not original:
                return None
            
            new_uuid = uuid.uuid4().hex[:16]
            
            cloned = File(
                file_uuid=new_uuid,
                file_id=original.file_id,
                file_unique_id=original.file_unique_id,
                name=original.name,
                file_type=original.file_type,
                mime_type=original.mime_type,
                extension=original.extension,
                size=original.size,
                duration=original.duration,
                width=original.width,
                height=original.height,
                channel_id=original.channel_id,
                channel_message_id=original.channel_message_id,
                owner_id=new_owner_id,
                owner_username=new_owner_username,
            )
            s.add(cloned)
        return new_uuid
    
    @staticmethod
    def get_files_by_owner(owner_id: int, limit: int = 30) -> List[Dict]:
        """获取用户文件"""
        with session_scope() as s:
            files = s.query(File).filter(
                File.owner_id == owner_id,
                File.is_active == True
            ).order_by(File.created_at.desc()).limit(limit).all()
            return [
                {
                    'file_uuid': f.file_uuid,
                    'name': f.name,
                    'file_type': f.file_type,
                    'size': f.size,
                    'download_count': f.download_count,
                    'created_at': f.created_at,
                }
                for f in files
            ]
    
    @staticmethod
    def increment_download(file_uuid: str):
        """增加下载次数"""
        with session_scope() as s:
            s.query(File).filter(File.file_uuid == file_uuid).update({
                File.download_count: File.download_count + 1
            })
    
    @staticmethod
    def increment_view(file_uuid: str):
        """增加查看次数"""
        with session_scope() as s:
            s.query(File).filter(File.file_uuid == file_uuid).update({
                File.view_count: File.view_count + 1
            })
    
    @staticmethod
    def get_share_link(code: str) -> Optional[Dict]:
        """获取分享链接信息（兼容旧版）"""
        with session_scope() as s:
            link = s.query(ShareLink).filter(
                ShareLink.link_code == code,
                ShareLink.is_active == True
            ).first()
            if link:
                if link.expires_at and link.expires_at < datetime.now():
                    return None
                return {
                    'link_code': link.link_code,
                    'file_uuid': link.file_uuid,
                    'expires_at': link.expires_at,
                }
            return None
    
    @staticmethod
    def create_share_link(file_uuid: str, creator_id: int, days: int = None) -> str:
        """创建分享链接"""
        import random
        import string
        code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        expires_at = None
        if days:
            expires_at = datetime.now() + timedelta(days=days)
        
        with session_scope() as s:
            s.add(ShareLink(
                link_code=code,
                file_uuid=file_uuid,
                creator_id=creator_id,
                expires_at=expires_at,
            ))
        return code
    
    @staticmethod
    def get_user(user_id: int) -> Optional[Dict]:
        """获取用户信息"""
        with session_scope() as s:
            user = s.query(User).filter(User.id == user_id).first()
            if user:
                return {
                    'id': user.id,
                    'username': user.username,
                    'is_admin': user.is_admin,
                    'is_banned': user.is_banned,
                    'storage_used': user.storage_used or 0,
                }
            return None
    
    @staticmethod
    def get_or_create_user(user_id: int, username: str = None, first_name: str = None) -> Dict:
        """获取或创建用户"""
        with session_scope() as s:
            user = s.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(
                    id=user_id,
                    username=username,
                    first_name=first_name,
                )
                s.add(user)
            return {
                'id': user.id,
                'username': user.username,
                'is_admin': user.is_admin,
                'is_banned': user.is_banned,
                'storage_used': user.storage_used or 0,
            }
    
    @staticmethod
    def set_user_banned(user_id: int, banned: bool = True):
        """封禁/解封用户"""
        with session_scope() as s:
            s.query(User).filter(User.id == user_id).update({'is_banned': banned})
    
    @staticmethod
    def update_user_storage(user_id: int, storage: int):
        """更新用户存储使用量"""
        with session_scope() as s:
            s.query(User).filter(User.id == user_id).update({'storage_used': max(0, storage)})
    
    @staticmethod
    def set_share_expiry(file_uuid: str, duration: int):
        """设置分享链接过期时间
        duration: 0 = 永久, 其他 = 秒数
        """
        with session_scope() as s:
            if duration == 0:
                expires_at = None  # 永久有效
            else:
                expires_at = datetime.now() + timedelta(seconds=duration)
            s.query(File).filter(File.file_uuid == file_uuid).update({
                File.share_expires_at: expires_at
            })


# 全局数据库实例
db = Database()
