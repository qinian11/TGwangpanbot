#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""频道管理模块"""
import logging
from typing import Dict, Optional
from telegram import Bot
from telegram.error import TelegramError
from config_manager import config
logger = logging.getLogger(__name__)
class ChannelManager:
    """频道管理器"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel_id = config.get('telegram.channel_id')
    async def upload_file(self, file_info: Dict) -> Optional[Dict]:
        """上传文件到频道"""
        try:
            file_type = file_info.get('file_type', 'document')
            file_id = file_info.get('file_id')
            owner_id = file_info.get('owner_id', 'Unknown')
            owner_name = file_info.get('owner_username', f'User_{owner_id}')
            caption = f"{file_info['name']}\n\n"
            caption += f"📤 上传者: {owner_name} (ID: {owner_id})\n"
            caption += f"🆔 文件: {file_info.get('file_uuid', '')}"
            if file_type == 'photo':
                result = await self.bot.send_photo(
                    chat_id=self.channel_id,
                    photo=file_id,
                    caption=caption
                )
            elif file_type == 'video':
                result = await self.bot.send_video(
                    chat_id=self.channel_id,
                    video=file_id,
                    caption=caption
                )
            elif file_type == 'audio':
                result = await self.bot.send_audio(
                    chat_id=self.channel_id,
                    audio=file_id,
                    caption=caption
                )
            elif file_type == 'voice':
                result = await self.bot.send_voice(
                    chat_id=self.channel_id,
                    voice=file_id,
                    caption=caption
                )
            else:
                result = await self.bot.send_document(
                    chat_id=self.channel_id,
                    document=file_id,
                    caption=caption
                )
            file_id_out = None
            file_unique_id = None
            if hasattr(result, 'document') and result.document:
                file_id_out = result.document.file_id
                file_unique_id = result.document.file_unique_id
            elif hasattr(result, 'photo') and result.photo:
                file_id_out = result.photo[-1].file_id if result.photo else file_id
            elif hasattr(result, 'video') and result.video:
                file_id_out = result.video.file_id
            elif hasattr(result, 'audio') and result.audio:
                file_id_out = result.audio.file_id
            elif hasattr(result, 'voice') and result.voice:
                file_id_out = result.voice.file_id
            else:
                file_id_out = file_id
            
            return {
                'file_id': file_id_out,
                'file_unique_id': file_unique_id or '',
                'channel_id': self.channel_id,
                'channel_message_id': result.message_id
            }
            
        except TelegramError as e:
            logger.error(f"上传到频道失败: {e}")
            return None
    
    async def delete_file(self, channel_id: int, message_id: int) -> bool:
        """从频道删除文件"""
        try:
            await self.bot.delete_message(chat_id=channel_id, message_id=message_id)
            return True
        except TelegramError as e:
            logger.error(f"删除频道消息失败: {e}")
            return False
