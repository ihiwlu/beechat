#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BeeChat 客户端主入口文件
启动客户端UI
"""

import wx
import sys
import os

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入各个UI模块
from login_ui import LoginFrame, LoginApp

def main():
    """主函数"""
    app = LoginApp()
    app.MainLoop()

if __name__ == '__main__':
    main()