#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeeChat 服务器主入口文件
启动所有服务组件
"""

import threading
import sys
import os
from config import DB_CONFIG, SERVER_PORTS

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入各个服务模块
from loginserver import LoginServer
from registerserver import RegisterServer
from friendlistserver import FriendListServer
from chatserver import ChatServer
from mail_id import VerificationServer

class BeeChatServer:
    def __init__(self):
        # 初始化各个服务
        self.login_server = LoginServer()
        self.register_server = RegisterServer()
        self.friendlist_server = FriendListServer()
        self.chat_server = ChatServer()
        
        # 验证码服务配置
        self.db_config = {
            "host": DB_CONFIG['host'],
            "port": DB_CONFIG['port'],
            "user": DB_CONFIG['user'],
            "password": DB_CONFIG['password'],
            "db_name": DB_CONFIG['database']
        }
        self.verification_server = VerificationServer(db_config=self.db_config, cleanup_interval=120)
        
        # 服务线程列表
        self.server_threads = []
        
    def start_all_services(self):
        """启动所有服务"""
        print("正在启动BeeChat服务器...")
        
        # 启动登录服务
        login_thread = threading.Thread(target=self.login_server.start_server, daemon=True)
        login_thread.start()
        self.server_threads.append(login_thread)
        print("✓ 登录服务已启动")
        
        # 启动注册服务
        register_thread = threading.Thread(target=self.register_server.start_server, daemon=True)
        register_thread.start()
        self.server_threads.append(register_thread)
        print("✓ 注册服务已启动")
        
        # 启动好友列表服务
        friendlist_thread = threading.Thread(target=self.friendlist_server.start_server, daemon=True)
        friendlist_thread.start()
        self.server_threads.append(friendlist_thread)
        print("✓ 好友列表服务已启动")
        
        # 启动聊天服务
        chat_thread = threading.Thread(target=self.chat_server.start_server, daemon=True)
        chat_thread.start()
        self.server_threads.append(chat_thread)
        print("✓ 聊天服务已启动")
        
        # 启动验证码服务
        verification_thread = threading.Thread(target=self.verification_server.start, daemon=True)
        verification_thread.start()
        self.server_threads.append(verification_thread)
        print("✓ 验证码服务已启动")
        
        print("所有服务已启动完成！")
        
    def wait_for_services(self):
        """等待所有服务线程结束"""
        try:
            # 等待任意一个线程结束
            for thread in self.server_threads:
                thread.join()
        except KeyboardInterrupt:
            print("\n正在关闭所有服务...")
            self.stop_all_services()
            
    def stop_all_services(self):
        """停止所有服务"""
        # 停止各个服务
        self.login_server.stop_server()
        self.register_server.stop_server()
        self.friendlist_server.stop_server()
        self.chat_server.stop_server()
        self.verification_server.stop()
        print("所有服务已停止")

def main():
    """主函数"""
    server = BeeChatServer()
    try:
        server.start_all_services()
        print("服务器正在运行中... 按 Ctrl+C 停止服务")
        server.wait_for_services()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.stop_all_services()
    except Exception as e:
        print(f"服务器运行出错: {e}")
        server.stop_all_services()

if __name__ == '__main__':
    main()