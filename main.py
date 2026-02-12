#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram网盘机器人核心功能模块
"""
import logging
from datetime import datetime
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters, MessageHandler
from telegram.error import TelegramError
from telegram.request import HTTPXRequest
import config_manager
from database import db
from user_manager import user_manager
from utils import format_size, get_file_icon, get_extension, get_file_type

# 配置
config = config_manager.config
MAX_FILE_SIZE = config.max_file_size * 1024 * 1024

# 日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """/start 命令 """
    user = u.effective_user
    user_manager.get_or_create_user(user.id, user.username, user.first_name)
    if c.args:
        await handle_share_link(u, c, c.args[0])
        return
    
    # 欢迎消息
    text = """🎉 欢迎使用网盘！

📤 直接发送文件保存
📂 /myfiles 查看我的文件

💡 发送 /help 获取帮助"""
    
    keyboard = [
        [InlineKeyboardButton("📂 我的文件", callback_data="myfiles")],
    ]
    
    await u.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def cmd_myfiles(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """/myfiles 命令 - 显示用户的文件列表"""
    user = u.effective_user
    files = db.get_files_by_owner(user.id, limit=30)
    
    if not files:
        text = "📂 我的文件\n\n您还没有上传文件"
    else:
        bot = c.bot
        
        # 获取最早文件时间
        latest_time = max(f['created_at'] for f in files)
        last_update = latest_time.strftime('%Y.%m.%d %H:%M')
        text = f"📂 我的文件\n\n最后更新: {last_update}\n\n"

        for i, f in enumerate(files, 1):
            file_link = f"https://t.me/{bot.username}?start={f['file_uuid']}"
            text += f"({i}) [{f['name']}]({file_link})\n"
    
    if u.message:
        await u.message.reply_text(text, parse_mode='Markdown')
    elif u.callback_query:
        await u.callback_query.edit_message_text(text, parse_mode='Markdown')


async def cmd_help(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """/help 命令 """
    user = u.effective_user
    user_manager.get_or_create_user(user.id, user.username, user.first_name)
    
    text = """📖 **使用帮助**
• 📤 直接发送文件 → 自动保存到TG网盘
• /start - 开始使用
• /myfiles - 查看我的文件
• /help - 显示此帮助

☁您的文件存储于Telegram服务器。您可以使用本机器人在线播放视频，上传下载文件，也可使用本机器分享文件。
本机器人为云服务，所有数据均保存于Telegram服务器。本网盘所有资料均来源于用户自行上传，与本机器人无关！
""".format(config.max_file_size)
    keyboard = [
        [InlineKeyboardButton("📂 我的文件", callback_data="myfiles")],
    ]
    await u.message.reply_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_message(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """处理上传的文件"""
    user = u.effective_user
    msg = u.message
    
    user_manager.get_or_create_user(user.id, user.username, user.first_name)
    
    # 提取文件
    file_info = extract_file(msg)
    if not file_info:
        return await msg.reply_text("💡 发送 /help 获取帮助")
    
    # 检查大小
    if file_info['size'] > MAX_FILE_SIZE:
        return await msg.reply_text(f"❌ 文件太大，最大 {config.max_file_size}MB")
    
    # 上传到频道
    try:
        from channel_manager import ChannelManager
        channel_mgr = ChannelManager(c.bot)
        # 传递用户信息
        file_info['owner_id'] = user.id
        file_info['owner_username'] = user.username or user.first_name
        result = await channel_mgr.upload_file(file_info)
        
        if not result:
            return await msg.reply_text("❌ 上传失败")
        
        file_info['channel_id'] = result['channel_id']
        file_info['channel_message_id'] = result['channel_message_id']
        
        file_uuid = db.add_file(file_info)
        
        if file_uuid:
            await send_file_result(c.bot, msg.chat.id, file_info, file_uuid)
        else:
            await msg.reply_text("❌ 保存失败")
            
    except TelegramError as e:
        logger.error(f"上传失败: {e}")
        await msg.reply_text("❌ 上传失败")


def extract_file(msg) -> Dict:
    """提取文件信息"""
    info = {
        'file_id': None, 'name': None, 'file_type': 'document',
        'mime_type': None, 'extension': None, 'size': 0,
        'duration': None, 'width': None, 'height': None
    }
    
    try:
        if msg.document:
            d = msg.document
            info['file_id'] = d.file_id
            info['name'] = d.file_name or '未命名'
            info['size'] = d.file_size or 0
            info['mime_type'] = d.mime_type
            info['extension'] = get_extension(info['name'], d.mime_type)
            info['file_type'] = get_file_type(info['name'])
            
        elif msg.photo:
            p = msg.photo[-1]
            info['file_id'] = p.file_id
            info['size'] = p.file_size or 0
            info['width'] = p.width
            info['height'] = p.height
            info['file_type'] = 'photo'
            info['name'] = f"photo.jpg"
            
        elif msg.video:
            v = msg.video
            info['file_id'] = v.file_id
            info['name'] = v.file_name or f"video.mp4"
            info['size'] = v.file_size or 0
            info['duration'] = v.duration
            info['width'] = v.width
            info['height'] = v.height
            info['mime_type'] = v.mime_type
            info['extension'] = get_extension(v.file_name, v.mime_type)
            info['file_type'] = 'video'
            
        elif msg.audio:
            a = msg.audio
            info['file_id'] = a.file_id
            info['name'] = a.file_name or f"audio.mp3"
            info['size'] = a.file_size or 0
            info['duration'] = a.duration
            info['mime_type'] = a.mime_type
            info['extension'] = get_extension(a.file_name, a.mime_type)
            info['file_type'] = 'audio'
            
        elif msg.voice:
            v = msg.voice
            info['file_id'] = v.file_id
            info['size'] = v.file_size or 0
            info['duration'] = v.duration
            info['file_type'] = 'voice'
            info['name'] = "voice.ogg"
            
    except Exception as e:
        logger.error(f"提取文件失败: {e}")
        
    return info if info['file_id'] else None


async def send_file_result(bot, chat_id: int, file_info: Dict, file_uuid: str):
    """发送文件结果（资源 + 分享链接 + 按钮）"""
    try:
        share_link = f"https://t.me/{bot.username}?start={file_uuid}"
        
        icon = get_file_icon(file_info['file_type'])
        
        text = f"{icon} {file_info['name']}\n"
        text += f"分享链接： {share_link}\n"
        text += f"📦 大小: {format_size(file_info['size'])}"
        
        # 按钮：删除 + 分享时长选项
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{file_uuid}")],
            [InlineKeyboardButton("📆 1天", callback_data=f"share_{file_uuid}_86400"),
             InlineKeyboardButton("📆 7天", callback_data=f"share_{file_uuid}_604800")],
            [InlineKeyboardButton("📆 30天", callback_data=f"share_{file_uuid}_2592000"),
             InlineKeyboardButton("♾️ 永久", callback_data=f"share_{file_uuid}_0")],
        ])
        
        ftype = file_info['file_type']
        if ftype == 'photo':
            await bot.send_photo(chat_id, file_info['file_id'], caption=text, reply_markup=keyboard)
        elif ftype == 'video':
            await bot.send_video(chat_id, file_info['file_id'], caption=text, reply_markup=keyboard)
        elif ftype == 'audio':
            await bot.send_audio(chat_id, file_info['file_id'], caption=text, reply_markup=keyboard)
        elif ftype == 'voice':
            await bot.send_voice(chat_id, file_info['file_id'], caption=text, reply_markup=keyboard)
        else:
            await bot.send_document(chat_id, file_info['file_id'], caption=text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"发送结果失败: {e}")


async def handle_share_link(u: Update, c: ContextTypes.DEFAULT_TYPE, code: str):
    """
    处理分享链接 - 返回资源 + 分享链接 + 按钮,如果不是文件所有者，自动转存到用户名下
    """
    user = u.effective_user
    user_manager.get_or_create_user(user.id, user.username, user.first_name)
    
    f = db.get_file(code)
    
    if not f:
        share_info = db.get_share_link(code)
        if share_info:
            f = db.get_file(share_info['file_uuid'])
            if f:
                db.increment_download(share_info['file_uuid'])
                code = share_info['file_uuid']
    
    if not f:
        await u.message.reply_text("❌ 链接无效或已过期")
        return
    
    db.increment_view(code)
    bot = await c.bot.get_me()
    # 检查是否是文件所有者，如果不是则转存
    is_owner = (f['owner_id'] == user.id)
    if not is_owner:
        # 转存文件到当前用户名下
        new_file_uuid = db.clone_file(code, user.id, user.username or user.first_name)
        if new_file_uuid:
            code = new_file_uuid
            # 使用新的file_uuid重新获取文件信息
            f = db.get_file(code)
            if not f:
                await u.message.reply_text("❌ 转存失败")
                return
            logger.info(f"用户 {user.id} 转存了文件 {code}")
    
    share_link = f"https://t.me/{bot.username}?start={code}"
    
    icon = get_file_icon(f['file_type'])
    
    # 提示信息
    #if not is_owner:
        #note = "✅ 已转存到你的文件\n\n"
    #else:
       # note = ""
    
    text = f"{icon} {f['name']}\n"
    #text += f"{note}分享链接 {share_link}\n"
    text += f"分享链接 {share_link}\n"
    text += f"📦 大小: {format_size(f['size'])}"
    
    # 按钮：删除 + 分享时长选项
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{code}")],
        [InlineKeyboardButton("分享1天", callback_data=f"share_{code}_86400"),
         InlineKeyboardButton("分享7天", callback_data=f"share_{code}_604800")],
        [InlineKeyboardButton("分享30天", callback_data=f"share_{code}_2592000"),
         InlineKeyboardButton("永久分享", callback_data=f"share_{code}_0")]
    ])
    
    ftype = f['file_type']
    if ftype == 'photo':
        await u.message.reply_photo(f['file_id'], caption=text, reply_markup=keyboard)
    elif ftype == 'video':
        await u.message.reply_video(f['file_id'], caption=text, reply_markup=keyboard)
    elif ftype == 'audio':
        await u.message.reply_audio(f['file_id'], caption=text, reply_markup=keyboard)
    elif ftype == 'voice':
        await u.message.reply_voice(f['file_id'], caption=text, reply_markup=keyboard)
    else:
        await u.message.reply_document(f['file_id'], caption=text, reply_markup=keyboard)


async def handle_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    q = u.callback_query
    data = q.data
    await q.answer()
    
    # 返回
    if data == "back":
        text = """🎉 欢迎使用小卡拉米TG网盘！

📤 直接发送文件保存 → 自动保存到TG网盘
📂 /myfiles 查看我的文件
💡 /help 获取帮助"""
        keyboard = [[InlineKeyboardButton("📂 我的文件", callback_data="myfiles")]]
        await c.bot.send_message(q.from_user.id, text, reply_markup=InlineKeyboardMarkup(keyboard))
        await q.answer()
        return
    
    # 我的文件
    if data == "myfiles":
        await cmd_myfiles(u, c)
        return
    
    # 查看文件详情
    if data.startswith("view_"):
        await show_file_detail(c.bot, q, data[5:])
        return
    
    # 下载
    if data.startswith("dl_"):
        await send_download(c.bot, q, data[3:])
        return
    
    # 删除
    if data.startswith("del_"):
        await delete_file_callback(c.bot, q, data[4:])
        return
    
    # 分享时长
    if data.startswith("share_"):
        parts = data[6:].split('_')
        file_uuid = parts[0]
        duration = int(parts[1]) if len(parts) > 1 else 0
        await set_share_expiry(c.bot, q, file_uuid, duration)
        return


async def set_share_expiry(bot, q, file_uuid: str, duration: int):
    """设置有效期"""
    f = db.get_file(file_uuid)
    if not f:
        await q.answer("❌ 文件不存在", show_alert=True)
        return
    
    # 检查权限
    if f['owner_id'] != q.from_user.id:
        await q.answer("无权操作", show_alert=True)
        return
    
    # 设置有效期
    if duration == 0:
        expiry_text = "永久有效"
    else:
        from datetime import timedelta
        expiry_time = datetime.now() + timedelta(seconds=duration)
        expiry_text = expiry_time.strftime('%Y.%m.%d %H:%M')
    
    db.set_share_expiry(file_uuid, duration)
    
    bot_info = await bot.get_me()
    share_link = f"https://t.me/{bot_info.username}?start={file_uuid}"
    
    icon = get_file_icon(f['file_type'])
    
    text = f"{icon} {f['name']}\n"
    text += f"分享链接： {share_link}\n"
    text += f"⏰ 有效期至: {expiry_text}\n\n"
    text += f"📦 大小: {format_size(f['size'])}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{file_uuid}")],
        [InlineKeyboardButton("📆 1天", callback_data=f"share_{file_uuid}_86400"),
         InlineKeyboardButton("📆 7天", callback_data=f"share_{file_uuid}_604800")],
        [InlineKeyboardButton("📆 30天", callback_data=f"share_{file_uuid}_2592000"),
         InlineKeyboardButton("♾️ 永久", callback_data=f"share_{file_uuid}_0")],
    ])
    
    # 尝试编辑消息文本，如果失败则发送新消息
    try:
        await q.edit_message_text(text, reply_markup=keyboard)
    except Exception:
        await q.edit_message_caption(caption=text, reply_markup=keyboard)

async def show_file_detail(bot, q, file_uuid: str):
    """显示文件详情"""
    f = db.get_file(file_uuid)
    if not f:
        await bot.send_message(q.from_user.id, "❌ 文件不存在")
        await q.answer()
        return
    
    bot_info = await bot.get_me()
    share_link = f"https://t.me/{bot_info.username}?start={file_uuid}"
    
    icon = get_file_icon(f['file_type'])
    upload_time = f['created_at'].strftime('%Y.%m.%d %H:%M')
    download_count = f.get('download_count', 0)
    
    text = f"{icon} {f['name']}\n"
    text += f"{format_size(f['size'])} | {upload_time} | {download_count} 次下载\n\n"
    text += f"分享链接： {share_link}"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ 下载", callback_data=f"dl_{file_uuid}")],
        [InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{file_uuid}")],
        [InlineKeyboardButton("🔙 返回", callback_data="myfiles")]
    ])
    
    await q.edit_message_text(text, reply_markup=keyboard)


async def send_download(bot, q, file_uuid: str):
    """发送下载"""
    f = db.get_file(file_uuid)
    if not f:
        await q.answer("❌ 文件不存在", show_alert=True)
        return
    
    db.increment_download(file_uuid)
    
    bot_info = await bot.get_me()
    share_link = f"https://t.me/{bot_info.username}?start={file_uuid}"
    
    icon = get_file_icon(f['file_type'])
    upload_time = f['created_at'].strftime('%Y.%m.%d %H:%M')
    download_count = f.get('download_count', 0)
    
    text = f"{icon} {f['name']}\n"
    text += f"{format_size(f['size'])} | {upload_time} | {download_count} 次下载\n\n"
    text += f"分享链接： {share_link}"
    
    # 判断是否为文件所有者
    is_owner = (f['owner_id'] == q.from_user.id)
    
    if is_owner:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ 删除", callback_data=f"del_{file_uuid}")],
            [InlineKeyboardButton("🔙 返回", callback_data="back")]
        ])
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 返回", callback_data="back")]
        ])
    
    try:
        ftype = f['file_type']
        if ftype == 'photo':
            await bot.send_photo(q.from_user.id, f['file_id'], caption=text, reply_markup=keyboard)
        elif ftype == 'video':
            await bot.send_video(q.from_user.id, f['file_id'], caption=text, reply_markup=keyboard)
        elif ftype == 'audio':
            await bot.send_audio(q.from_user.id, f['file_id'], caption=text, reply_markup=keyboard)
        elif ftype == 'voice':
            await bot.send_voice(q.from_user.id, f['file_id'], caption=text, reply_markup=keyboard)
        else:
            await bot.send_document(q.from_user.id, f['file_id'], caption=text, reply_markup=keyboard)
        
        await q.answer("✅ 已发送", show_alert=False)
    except TelegramError:
        await q.answer("❌ 发送失败", show_alert=True)


async def delete_file_callback(bot, q, file_uuid: str):
    """删除文件"""
    f = db.get_file(file_uuid)
    if not f:
        await bot.send_message(q.from_user.id, "❌ 文件不存在")
        return
    
    user = q.from_user
    
    # 检查权限
    if f['owner_id'] != user.id:
        await q.answer("无权删除", show_alert=True)
        return
    
    # 删除
    try:
        from channel_manager import ChannelManager
        channel_mgr = ChannelManager(bot)
        
        if f.get('channel_id') and f.get('channel_message_id'):
            try:
                await channel_mgr.delete_file(f['channel_id'], f['channel_message_id'])
            except:
                pass
        
        db.delete_file(file_uuid)
        user_manager.update_storage(f['owner_id'], -f['size'])
        
        text = f"🗑️ 已删除\n\n📁 {f['name']}"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 返回", callback_data="myfiles")]])
        await bot.send_message(q.from_user.id, text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"删除失败: {e}")
        await bot.send_message(q.from_user.id, "❌ 删除失败")


# ========== 主入口 ==========

def main():
    token = config.get('telegram.token')
    if not token or token == 'YOUR_BOT_TOKEN_HERE':
        print("❌ 请先在 config.json 中配置 telegram.token")
        return
    
    app = Application.builder().token(token).build()
    
    # 注册处理器
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("myfiles", cmd_myfiles))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    logger.info("机器人运行中... 按 Ctrl+C 停止")
    app.run_polling()


if __name__ == "__main__":
    main()
