import wx
import os
import time
import socket
import json
import threading

class ChatFrame(wx.Frame):
    def __init__(self, friend_name="好友", messages_data=None, username=None, user_id=None, friend_id=None):
        super().__init__(None, title=f"与 {friend_name} 聊天", size=(500, 600))
        try:
            icon = wx.Icon(os.path.join(os.path.dirname(__file__), 'app.ico'))
            self.SetIcon(icon)
        except Exception:
            pass
        
        # 居中显示
        self.Center()
        
        # 好友名称
        self.friend_name = friend_name
        
        # 当前用户名
        self.username = username
        
        # 用户ID和好友ID
        self.user_id = user_id
        self.friend_id = friend_id
        
        # 服务器配置
        # 实时聊天服务器（chatserver.py）
        self.CHAT_HOST = 'localhost'
        self.CHAT_PORT = 8891
        # 好友/消息持久化服务器（friendlistserver.py）
        self.FRIEND_HOST = 'localhost'
        self.FRIEND_PORT = 8892
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加聊天记录区域
        self.create_chat_history_section(main_sizer)
        
        # 添加输入区域
        self.create_input_section(main_sizer)
        
        # 设置主面板的布局
        self.panel.SetSizer(main_sizer)
        
        # 初始化消息数据
        self.messages_data = []
        
        # 实时聊天 socket
        self.client_socket = None
        self.receive_thread = None
        self._receiving = False

        # 加载聊天记录
        self.load_chat_history()
        
        # 显示消息
        self.display_messages()

        # 连接实时聊天服务器
        if self.username:
            self.connect_to_realtime_server()

        # 绑定关闭事件，确保清理连接
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # 激活时自动刷新历史，确保离线消息在打开/切回窗口时展示
        self.Bind(wx.EVT_ACTIVATE, self.on_activate)
        
    def create_chat_history_section(self, sizer):
        """创建聊天记录区域"""
        # 聊天记录面板
        history_panel = wx.Panel(self.panel)
        history_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建聊天记录文本控件
        self.chat_history = wx.TextCtrl(
            history_panel, 
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            size=(-1, 400)
        )
        
        # 设置字体
        font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.chat_history.SetFont(font)
        
        history_sizer.Add(self.chat_history, 1, wx.ALL | wx.EXPAND, 5)
        history_panel.SetSizer(history_sizer)
        sizer.Add(history_panel, 1, wx.ALL | wx.EXPAND, 5)
        
    def create_input_section(self, sizer):
        """创建输入区域"""
        # 输入面板
        input_panel = wx.Panel(self.panel)
        input_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 输入文本框
        self.message_input = wx.TextCtrl(input_panel, style=wx.TE_MULTILINE, size=(-1, 80))
        input_sizer.Add(self.message_input, 1, wx.ALL | wx.EXPAND, 5)
        
        # 按钮面板
        button_panel = wx.Panel(input_panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 发送按钮
        send_btn = wx.Button(button_panel, label="发送", size=(80, 30))
        send_btn.Bind(wx.EVT_BUTTON, self.on_send_message)
        
        # 清空按钮
        clear_btn = wx.Button(button_panel, label="清空", size=(80, 30))
        clear_btn.Bind(wx.EVT_BUTTON, self.on_clear_input)

        # 传文件按钮
        file_btn = wx.Button(button_panel, label="传文件", size=(80, 30))
        file_btn.Bind(wx.EVT_BUTTON, self.on_open_file_transfer)
        
        button_sizer.Add(send_btn, 0, wx.ALL, 5)
        button_sizer.Add(clear_btn, 0, wx.ALL, 5)
        button_sizer.Add(file_btn, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer(1)
        
        button_panel.SetSizer(button_sizer)
        input_sizer.Add(button_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        input_panel.SetSizer(input_sizer)
        sizer.Add(input_panel, 0, wx.ALL | wx.EXPAND, 5)
        
        # 绑定回车键发送消息
        self.message_input.Bind(wx.EVT_KEY_DOWN, self.on_key_press)
        
    def display_messages(self):
        """显示消息"""
        self.chat_history.Clear()
        
        for msg in self.messages_data:
            sender, content, timestamp = msg
            self.append_message(sender, content, timestamp)
        
        # 滚动到底部
        self.chat_history.SetInsertionPointEnd()
        
    def append_message(self, sender, content, timestamp):
        """添加消息到显示区域"""
        # 处理时间戳（可能是字符串或时间戳）
        if isinstance(timestamp, str):
            # 如果是字符串，直接使用（应为 'YYYY-MM-DD HH:MM:SS'）
            time_str = timestamp
        else:
            # 如果是时间戳，格式化为完整日期+时间
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        
        # 统一格式：时间在前，发送者在中间，内容在后
        message_line = f"[{time_str}] {sender}: {content}\n"
        
        # 根据发送者设置不同的颜色
        if sender == "我":
            # 我的消息蓝色显示
            self.chat_history.SetDefaultStyle(wx.TextAttr(wx.BLUE))
        else:
            # 好友的消息绿色显示
            self.chat_history.SetDefaultStyle(wx.TextAttr(wx.GREEN))
            
        self.chat_history.AppendText(message_line)
        
        # 重置默认样式
        self.chat_history.SetDefaultStyle(wx.TextAttr(wx.BLACK))
        
    def load_chat_history(self):
        """加载聊天记录"""
        if not self.user_id or not self.friend_id:
            return
            
        def fetch_messages():
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.FRIEND_HOST, self.FRIEND_PORT))
                
                request_data = {
                    'action': 'get_messages',
                    'user_id': self.user_id,
                    'friend_id': self.friend_id,
                    'limit': 0  # 0 或 <=0 表示返回全部历史
                }
                client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                response_data = client_socket.recv(4096).decode('utf-8')
                client_socket.close()
                
                response = json.loads(response_data)
                if response.get('status') == 'success':
                    messages = response.get('messages', [])
                    # 转换消息格式
                    formatted_messages = []
                    for msg in messages:
                        sender_name = "我" if msg['sender_id'] == self.user_id else self.friend_name
                        formatted_messages.append((
                            sender_name, 
                            msg['message'], 
                            msg['created_at']
                        ))
                    wx.CallAfter(self.update_messages, formatted_messages)
            except Exception as e:
                print(f"加载聊天记录失败: {e}")
        
        # 在后台线程中加载
        thread = threading.Thread(target=fetch_messages)
        thread.daemon = True
        thread.start()
    
    def update_messages(self, messages):
        """更新消息列表"""
        self.messages_data = messages
        self.display_messages()
    
    def on_send_message(self, event):
        """发送消息事件处理"""
        message = self.message_input.GetValue().strip()
        if not message or not self.user_id or not self.friend_id:
            return
            
        def send_to_server():
            try:
                # 1) 调用持久化服务器保存消息
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.FRIEND_HOST, self.FRIEND_PORT))
                
                request_data = {
                    'action': 'send_message',
                    'user_id': self.user_id,
                    'friend_id': self.friend_id,
                    'message': message,
                    'message_type': 'text'
                }
                client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                response_data = client_socket.recv(1024).decode('utf-8')
                client_socket.close()
                
                response = json.loads(response_data)
                if response.get('status') == 'success':
                    # 2) 通过实时聊天服务器发送私聊
                    self.send_private_message_realtime(message)
                    # 3) 本地即时追加
                    timestamp = time.time()
                    wx.CallAfter(self.add_local_message, "我", message, timestamp)
                else:
                    wx.CallAfter(wx.MessageBox, f"发送失败：{response.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"发送消息失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        
        # 在后台线程中发送
        thread = threading.Thread(target=send_to_server)
        thread.daemon = True
        thread.start()
        
        # 清空输入框
        self.message_input.Clear()

    def send_private_message_realtime(self, message):
        """通过实时聊天服务器发送私聊消息"""
        try:
            if not self.client_socket:
                return
            payload = {
                'type': 'private',
                'to': self.friend_name,
                'message': message
            }
            self.client_socket.send(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        except Exception:
            # 忽略实时发送错误，不影响已持久化
            pass

    def connect_to_realtime_server(self):
        """连接到聊天服务器并认证用户名"""
        def connect():
            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((self.CHAT_HOST, self.CHAT_PORT))
                auth_data = {
                    'username': self.username
                }
                self.client_socket.send(json.dumps(auth_data, ensure_ascii=False).encode('utf-8'))
                self.start_receive_thread()
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"连接聊天服务器失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        thread = threading.Thread(target=connect)
        thread.daemon = True
        thread.start()

    def start_receive_thread(self):
        """启动接收实时消息的线程"""
        if self.receive_thread and self.receive_thread.is_alive():
            return
        self._receiving = True

        def receive_messages():
            try:
                while self._receiving and self.client_socket:
                    data = self.client_socket.recv(4096).decode('utf-8')
                    if not data:
                        break
                    try:
                        message = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    wx.CallAfter(self.handle_incoming_message, message)
            except Exception:
                pass
        self.receive_thread = threading.Thread(target=receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def handle_incoming_message(self, message):
        """处理从聊天服务器接收到的消息"""
        msg_type = message.get('type')
        timestamp = time.time()
        if msg_type == 'private':
            sender = message.get('from') or message.get('sender') or '对方'
            content = message.get('message') or message.get('content') or ''
            self.messages_data.append((sender, content, timestamp))
            self.append_message(sender, content, timestamp)
            self.chat_history.SetInsertionPointEnd()
        elif msg_type in ('system', 'system_message'):
            content = message.get('message') or message.get('content') or ''
            self.append_system_message(content, timestamp)
        elif msg_type == 'error':
            content = message.get('message') or '发生错误'
            self.append_system_message(f"错误：{content}", timestamp)
        elif msg_type == 'chat':
            sender = message.get('from') or '房间'
            content = message.get('message') or ''
            self.messages_data.append((sender, content, timestamp))
            self.append_message(sender, content, timestamp)
            self.chat_history.SetInsertionPointEnd()

    def append_system_message(self, content, timestamp):
        """添加系统消息到显示区域"""
        time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
        message_line = f"[{time_str}] 系统: {content}\n"
        self.chat_history.SetDefaultStyle(wx.TextAttr(wx.Colour(128, 128, 128)))
        self.chat_history.AppendText(message_line)
        self.chat_history.SetDefaultStyle(wx.TextAttr(wx.BLACK))

    def on_close(self, event):
        """窗口关闭时清理资源"""
        try:
            self._receiving = False
            if self.client_socket:
                try:
                    self.client_socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                self.client_socket.close()
        finally:
            event.Skip()
    
    def add_local_message(self, sender, content, timestamp):
        """添加本地消息"""
        self.messages_data.append((sender, content, timestamp))
        self.append_message(sender, content, timestamp)
        self.chat_history.SetInsertionPointEnd()
            
    def on_clear_input(self, event):
        """清空输入框事件处理"""
        self.message_input.Clear()
        
    def on_key_press(self, event):
        """键盘按键事件处理"""
        # 如果按下回车键且没有按下Shift键，则发送消息
        if event.GetKeyCode() == wx.WXK_RETURN and not event.ShiftDown():
            self.on_send_message(None)
        else:
            event.Skip()

    def on_open_file_transfer(self, event):
        """打开文件传输窗口"""
        try:
            from file_ui import FileTransferFrame
            frame = FileTransferFrame(username=self.username, user_id=self.user_id, friend_id=self.friend_id)
            frame.Show()
        except Exception as e:
            wx.MessageBox(f"无法打开文件传输窗口：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)

    def on_activate(self, event):
        """窗口被激活时刷新历史消息"""
        try:
            if event.GetActive():
                # 重新拉取历史（limit=0 获取全部），确保显示离线期间收到的消息
                self.load_chat_history()
        finally:
            event.Skip()

class ChatApp(wx.App):
    def OnInit(self):
        # 定义虚拟消息数据
        virtual_messages = [
            ("我", "你好！", time.time() - 300),
            ("好友", "你好！有什么可以帮助你的吗？", time.time() - 240),
            ("我", "我想了解一下这个项目的情况", time.time() - 180),
            ("好友", "这个项目是我们团队的重点项目，目前进展顺利", time.time() - 120),
            ("我", "太好了，谢谢！", time.time() - 60)
        ]
        
        frame = ChatFrame("好友", virtual_messages)
        frame.Show()
        return True

if __name__ == '__main__':
    # 或者在这里定义虚拟消息数据
    messages_data = [
        ("我", "你好，我是测试消息1", time.time() - 300),
        ("好友", "你好，我是测试消息2", time.time() - 240),
        ("我", "这是第三条测试消息", time.time() - 180)
    ]
    
    app = wx.App()
    frame = ChatFrame("测试好友", messages_data, username="测试用户")
    frame.Show()
    app.MainLoop()