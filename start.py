#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram网盘机器人启动脚本
功能：支持Windows/Linux/Mac系统，支持后台运行

使用方法：
1. 直接运行：python start.py
2. 后台运行(Linux/Mac)：python start.py --daemon
3. 指定配置文件：python start.py --config config/custom.json
4. 查看帮助：python start.py --help

作者：AI助手
版本：2.0.0
"""

import os
import sys
import time
import signal
import argparse
import logging
import subprocess
from datetime import datetime
from pathlib import Path
import requests
import json
# 配置路径
BASE_DIR = Path(__file__).parent.absolute()
LOG_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# 日志配置
LOG_FILE = LOG_DIR / "bot.log"
ERROR_FILE = LOG_DIR / "error.log"


def setup_logging():
    """配置日志"""
    LOG_DIR.mkdir(exist_ok=True)
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 使用RotatingFileHandler限制日志文件大小
    # 每个日志文件最大1MB，保留3个备份
    from logging.handlers import RotatingFileHandler
    
    max_bytes = 1024 * 1024  # 1MB
    backup_count = 3
    
    # 主日志文件处理器
    file_handler = RotatingFileHandler(LOG_FILE, encoding='utf-8', maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 错误日志文件处理器
    error_handler = RotatingFileHandler(ERROR_FILE, encoding='utf-8', maxBytes=max_bytes, backupCount=backup_count)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 配置根日志
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    
    # 清理旧日志文件
    _cleanup_old_logs(LOG_DIR, max_bytes)
    
    return logging.getLogger(__name__)


def _cleanup_old_logs(log_dir: Path, max_bytes: int):
    """清理过大的日志文件"""
    try:
        for log_file in log_dir.glob('*.log*'):
            try:
                if log_file.stat().st_size > max_bytes * 10:  # 超过10MB的旧日志
                    log_file.unlink()
                    print(f"已清理大日志文件: {log_file.name}")
            except Exception:
                pass
    except Exception:
        pass


def check_requirements():
    """检查依赖"""
    logger.info("检查系统依赖...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        logger.error("需要Python 3.8或更高版本")
        return False
    
    logger.info(f"Python版本: {sys.version}")
    
    # 检查必要文件
    required_files = [
        'main.py',
        'config.json',
        'requirements.txt',
        'database.py',
        'channel_manager.py',
        'user_manager.py',
        'utils.py'
    ]
    
    for file in required_files:
        if not (BASE_DIR / file).exists():
            logger.error(f"缺少必要文件: {file}")
            return False
    
    logger.info("必要文件检查通过")
    return True


def install_requirements():
    """安装依赖"""
    logger.info("检查并安装依赖...")
    
    requirements_file = BASE_DIR / "requirements.txt"
    
    if not requirements_file.exists():
        logger.error("找不到 requirements.txt 文件")
        return False
    
    try:
        # 使用pip安装依赖
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info("依赖安装成功")
            return True
        else:
            logger.error(f"依赖安装失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("依赖安装超时")
        return False
    except Exception as e:
        logger.error(f"安装依赖时出错: {e}")
        return False


def check_config():
    """检查配置文件"""
    logger.info("检查配置文件...")
    
    config_file = BASE_DIR / "config.json"
    
    if not config_file.exists():
        logger.error("找不到 config.json 文件")
        return False
    
    try:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查必要配置
        token = config.get('telegram', {}).get('token', '')
        if not token or token == 'YOUR_BOT_TOKEN_HERE':
            logger.warning("未配置Telegram Bot Token")
            logger.warning("请在 config.json 中设置 telegram.token")
        
        channel_id = config.get('telegram', {}).get('channel_id', 0)
        if not channel_id:
            logger.warning("未配置存储频道")
            logger.warning("请在 config.json 中设置 telegram.channel_id")
        
        logger.info("配置文件检查完成")
        return True
        
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        return False
    except Exception as e:
        logger.error(f"检查配置文件时出错: {e}")
        return False


def run_bot():
    """运行机器人"""
    logger.info("启动Telegram网盘机器人...")
    
    try:
        # 切换到脚本目录
        os.chdir(BASE_DIR)
        
        # 导入并运行主程序
        from main import main
        main()
        
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"运行机器人时出错: {e}")
        return False
    
    return True


def check_database():
    """检查并初始化数据库"""
    logger.info("检查数据库...")
    
    DATA_DIR.mkdir(exist_ok=True)
    
    try:
        # 尝试导入数据库模块
        from database import db
        logger.info("数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        return False


def test_bot_connection(bot_token: str) -> bool:
    """测试机器人连接"""
    logger.info("测试Telegram Bot连接...")
    
    try:
        # 获取Bot信息
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('ok'):
            bot_info = data.get('result', {})
            logger.info(f"Bot连接成功: @{bot_info.get('username')} ({bot_info.get('first_name')})")
            return True
        else:
            logger.error(f"Bot连接失败: {data.get('description')}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("连接超时，请检查网络")
        return False
    except Exception as e:
        logger.error(f"测试连接时出错: {e}")
        return False


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔════════════════════════════════════════════════════════════╗
║              Telegram网盘机器人 v1.0.0                       ║
║    功能：上传、分享、转存、我的文件                              ║
║    作者TG：小卡拉米 @hy499                                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """主函数"""
    global logger
    logger = setup_logging()
    
    # 打印横幅
    print_banner()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Telegram网盘机器人启动脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='后台运行模式（仅Linux/Mac）'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='指定配置文件路径'
    )
    parser.add_argument(
        '--check', '-k',
        action='store_true',
        help='仅检查环境，不运行'
    )
    parser.add_argument(
        '--install', '-i',
        action='store_true',
        help='安装依赖'
    )
    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='测试Bot连接'
    )
    
    args = parser.parse_args()
    
    # 记录启动信息
    logger.info("=" * 60)
    logger.info("Telegram网盘机器人启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"工作目录: {BASE_DIR}")
    logger.info(f"Python版本: {sys.version}")
    logger.info("=" * 60)
    
    # 检查依赖
    if not check_requirements():
        sys.exit(1)
    
    # 安装依赖
    if args.install:
        if not install_requirements():
            sys.exit(1)
    
    # 检查配置
    if not check_config():
        sys.exit(1)
    
    # 测试连接
    if args.test:
        import json
        with open(BASE_DIR / "config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        token = config.get('telegram', {}).get('token', '')
        if test_bot_connection(token):
            print("\n✅ Bot连接测试成功！")
        else:
            print("\n❌ Bot连接测试失败，请检查token是否正确")
        sys.exit(0)
    
    # 仅检查模式
    if args.check:
        print("\n✅ 环境检查完成，没有发现问题")
        sys.exit(0)
    
    # 检查数据库
    if not check_database():
        sys.exit(1)
    
    # 后台运行（仅Linux/Mac）
    if args.daemon and sys.platform != 'win32':
        logger.info("进入后台运行模式...")
        
        # 创建pid文件
        pid_file = BASE_DIR / "bot.pid"
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        try:
            # 创建守护进程
            pid = os.fork()
            if pid > 0:
                logger.info(f"后台进程已启动 (PID: {pid})")
                sys.exit(0)
        except Exception as e:
            logger.error(f"无法进入后台模式: {e}")
    
    # 运行机器人
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    except Exception as e:
        logger.error(f"运行时错误: {e}")
        sys.exit(1)
    
    logger.info("机器人已停止")


if __name__ == "__main__":
    main()
