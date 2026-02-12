#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具函数模块"""
from typing import Optional


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}PB"


def get_file_type(filename: str) -> str:
    """获取文件类型"""
    if not filename:
        return 'other'
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    video_exts = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v']
    audio_exts = ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a', 'wma']
    image_exts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
    doc_exts = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt']
    archive_exts = ['zip', 'rar', '7z', 'tar', 'gz']
    
    if ext in video_exts:
        return 'video'
    elif ext in audio_exts:
        return 'audio'
    elif ext in image_exts:
        return 'photo'
    elif ext in doc_exts:
        return 'document'
    elif ext in archive_exts:
        return 'archive'
    return 'other'


def get_file_icon(file_type: str) -> str:
    """获取文件图标"""
    icons = {
        'video': '🎬',
        'audio': '🎵',
        'photo': '🖼️',
        'document': '📄',
        'archive': '📦',
        'voice': '🎙️',
        'other': '📁'
    }
    return icons.get(file_type, '📁')


def get_extension(filename: str, mime_type: str = None) -> str:
    """获取文件扩展名"""
    if filename and '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    if mime_type:
        mime_map = {
            'application/pdf': 'pdf',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'video/mp4': 'mp4',
            'audio/mpeg': 'mp3',
        }
        return mime_map.get(mime_type, '')
    return ''
