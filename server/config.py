#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeeChat 服务器配置文件
包含所有服务器的数据库连接配置信息
"""

import os

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pwd@123',
    'port': 3306,
    'charset': 'utf8mb4',
    'database': 'test'
}

# 验证码数据库配置（用于邮件验证）
VERIFICATION_DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pwd@123',
    'port': 3306,
    'db_name': 'test'
}

# 服务器端口配置
SERVER_PORTS = {
    'login': 8888,
    'register': 8889,
    'friendlist': 8892,
    'chat': 8891,
    'file': 8893,
    'verification': 12123,
    'forgot': 8890
}

# 服务器主机配置
SERVER_HOST = 'localhost'

# 文件存储配置
STORAGE_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
