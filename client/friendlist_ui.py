import wx

class FriendListFrame(wx.Frame):
    def __init__(self, friends_data=None, username=None):
        title_username = username or ""
        super().__init__(None, title=f"{title_username}的好友列表", size=(350, 500))
        try:
            import os
            icon = wx.Icon(os.path.join(os.path.dirname(__file__), 'app.ico'))
            self.SetIcon(icon)
        except Exception:
            pass
        
        # 居中显示
        self.Center()
        
        # 保存用户名
        self.username = username
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加标题区域
        self.create_header_section(main_sizer)
        
        # 添加好友列表区域
        self.create_friend_list_section(main_sizer)
        
        # 添加按钮区域
        self.create_button_section(main_sizer)
        
        # 设置主面板的布局
        self.panel.SetSizer(main_sizer)
        
        # 初始化好友数据
        if friends_data:
            self.friends_data = friends_data
        else:
            # 空的好友数据列表
            self.friends_data = []
        # 好友名到ID映射
        self.friend_name_to_id = {}
        
        # 初始化好友列表
        self.init_friends_data()
        
        # 创建定时器，每10秒刷新一次好友列表
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(10000)  # 10秒刷新一次
        
        # 立即获取好友列表数据
        self.refresh_friend_list()
        
    def create_header_section(self, sizer):
        """创建标题区域"""
        # 标题区域
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 添加标题
        shown_username = self.username or ""
        title_text = wx.StaticText(self.panel, label=f"{shown_username}的好友列表")
        title_font = title_text.GetFont()
        title_font.PointSize += 8
        title_font = title_font.Bold()
        title_text.SetFont(title_font)
        
        header_sizer.Add(title_text, 1, wx.ALL | wx.CENTER, 10)
        
        sizer.Add(header_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
    def create_friend_list_section(self, sizer):
        """创建好友列表区域"""
        # 创建列表面板
        list_panel = wx.Panel(self.panel)
        list_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 创建好友列表
        self.friend_list = wx.ListCtrl(list_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.friend_list.InsertColumn(0, "好友昵称", width=320)
        
        # 绑定双击事件
        self.friend_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_friend_double_click)
        
        # 添加滚动条
        list_sizer.Add(self.friend_list, 1, wx.ALL | wx.EXPAND, 5)
        
        list_panel.SetSizer(list_sizer)
        sizer.Add(list_panel, 1, wx.ALL | wx.EXPAND, 5)
        
    def create_button_section(self, sizer):
        """创建按钮区域"""
        # 按钮面板
        button_panel = wx.Panel(self.panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 添加好友按钮
        add_friend_btn = wx.Button(button_panel, label="添加好友", size=(100, 35))
        add_friend_btn.Bind(wx.EVT_BUTTON, self.on_add_friend)
        
        # 查看好友请求按钮
        view_requests_btn = wx.Button(button_panel, label="好友请求", size=(100, 35))
        view_requests_btn.Bind(wx.EVT_BUTTON, self.on_view_requests)
        
        # 刷新按钮
        refresh_btn = wx.Button(button_panel, label="刷新", size=(100, 35))
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        
        # 添加按钮到布局
        button_sizer.Add(add_friend_btn, 0, wx.ALL, 5)
        button_sizer.Add(view_requests_btn, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(refresh_btn, 0, wx.ALL, 5)
        
        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.ALL | wx.EXPAND, 5)
        
    def init_friends_data(self):
        """初始化好友数据"""
        # 清空当前列表
        self.friend_list.DeleteAllItems()
        
        # 添加好友到列表
        for i, item in enumerate(self.friends_data):
            # 支持数据结构 (name, remark) 或旧结构 (name)
            name = item[0]
            remark = item[1] if len(item) > 1 else ''
            display_name = name if not remark else f"{name}（{remark}）"
            index = self.friend_list.InsertItem(self.friend_list.GetItemCount(), display_name)
                
    def on_friend_double_click(self, event):
        """好友列表双击事件处理"""
        selected_index = self.friend_list.GetFirstSelected()
        if selected_index != -1:
            # 兼容：row 结构可能为 (name, remark) 或 (name)
            row = self.friends_data[selected_index]
            friend_name = row[0]
            
            # 显示好友详细信息
            from friendinfo import FriendInfoFrame
            import wx
            
            # 创建好友信息窗口（这里使用虚拟邮箱，实际应用中应从服务器获取）
            friend_email = f"{friend_name.lower()}@example.com"
            friend_id = self.friend_name_to_id.get(friend_name)
            friend_info_frame = FriendInfoFrame(friend_name, friend_email, username=self.username, friend_id=friend_id)
            friend_info_frame.Show()
        
    def on_add_friend(self, event):
        """添加好友按钮事件处理"""
        # 弹出对话框让用户输入要添加的好友用户名
        dialog = wx.TextEntryDialog(self, "请输入要添加的好友用户名:", "添加好友", "")
        if dialog.ShowModal() == wx.ID_OK:
            friend_name = dialog.GetValue().strip()
            if friend_name:
                import socket
                import json
                import threading
                
                # 好友列表服务器配置
                SERVER_HOST = 'localhost'
                SERVER_PORT = 8892  # 好友列表服务器端口
                
                def send_friend_request():
                    try:
                        # 创建socket连接
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.connect((SERVER_HOST, SERVER_PORT))
                        
                        # 准备请求数据
                        request_data = {
                            'action': 'send_request',
                            'username': self.username,
                            'friend_username': friend_name
                        }
                        
                        # 发送数据到服务器
                        client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                        
                        # 接收服务器响应
                        response_data = client_socket.recv(1024).decode('utf-8')
                        response = json.loads(response_data)
                        
                        # 关闭socket连接
                        client_socket.close()
                        
                        # 在主线程中显示结果
                        if response.get('status') == 'success':
                            wx.CallAfter(wx.MessageBox, f"已发送好友请求给 {friend_name}", "添加好友", wx.OK | wx.ICON_INFORMATION)
                            # 刷新好友列表
                            wx.CallAfter(self.refresh_friend_list)
                        else:
                            wx.CallAfter(wx.MessageBox, f"添加好友失败：{response.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
                            
                    except Exception as e:
                        wx.CallAfter(wx.MessageBox, f"添加好友失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
                
                # 创建一个线程来发送好友请求，避免阻塞UI
                request_thread = threading.Thread(target=send_friend_request)
                request_thread.daemon = True
                request_thread.start()
            else:
                wx.MessageBox("用户名不能为空", "错误", wx.OK | wx.ICON_ERROR)
        dialog.Destroy()
        
    def on_view_requests(self, event):
        """查看好友请求按钮事件处理"""
        # 导入好友请求界面模块
        from friend_requests_ui import FriendRequestsFrame
        import wx
        
        # 创建好友请求窗口
        requests_frame = FriendRequestsFrame(username=self.username)
        requests_frame.Show()

    def on_refresh(self, event):
        """刷新按钮事件处理"""
        # 从服务端重新获取好友数据
        self.refresh_friend_list()
    
    def on_timer(self, event):
        """定时器事件处理"""
        self.refresh_friend_list()
    
    def refresh_friend_list(self):
        """刷新好友列表"""
        import socket
        import json
        import threading
        import time
        
        # 好友列表服务器配置
        SERVER_HOST = 'localhost'
        SERVER_PORT = 8892  # 好友列表服务器端口
        
        def fetch_friends():
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                response = None  # 初始化response变量
                try:
                    # 创建socket连接
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(10.0)  # 设置连接超时
                    client_socket.connect((SERVER_HOST, SERVER_PORT))
                    
                    # 准备请求数据
                    request_data = {
                        'action': 'get_friends',
                        'username': self.username
                    }
                    
                    # 发送数据到服务器
                    client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                    
                    # 接收服务器响应（聚合直到可解析为完整JSON）
                    client_socket.settimeout(10.0)
                    buf = b''
                    while True:
                        try:
                            chunk = client_socket.recv(4096)
                            if not chunk:
                                break
                            buf += chunk
                            try:
                                response = json.loads(buf.decode('utf-8'))
                                break
                            except json.JSONDecodeError:
                                continue
                        except socket.timeout:
                            raise Exception('等待服务器响应超时')
                    
                    # 关闭socket连接
                    client_socket.close()
                    
                    # 检查是否成功接收到响应
                    if response is None:
                        raise Exception('未收到服务器响应')
                    
                    # 在主线程中更新UI
                    if response.get('status') == 'success':
                        friends = response.get('friends', [])
                        # 转换好友数据格式（昵称+备注）
                        formatted_friends = []
                        # 重建映射
                        name_to_id = {}
                        for friend in friends:
                            name = friend.get('username', '')
                            remark = friend.get('remark', '') or ''
                            formatted_friends.append((name, remark))
                            if name:
                                name_to_id[name] = friend.get('friend_id')
                        
                        def apply_update():
                            self.friend_name_to_id = name_to_id
                            self.update_friends_data(formatted_friends)
                        wx.CallAfter(apply_update)
                        return  # 成功获取，退出重试循环
                    else:
                        error_msg = f"获取好友列表失败：{response.get('message')}"
                        if retry_count < max_retries - 1:
                            retry_count += 1
                            time.sleep(1)  # 等待1秒后重试，不显示重试提示
                            continue
                        else:
                            wx.CallAfter(wx.MessageBox, error_msg, "错误", wx.OK | wx.ICON_ERROR)
                            return
                    
                except Exception as e:
                    error_msg = f"获取好友列表失败：{str(e)}"
                    if retry_count < max_retries - 1:
                        retry_count += 1
                        time.sleep(1)  # 等待1秒后重试，不显示重试提示
                        continue
                    else:
                        wx.CallAfter(wx.MessageBox, error_msg, "错误", wx.OK | wx.ICON_ERROR)
                        return
        
        # 创建一个线程来获取好友列表，避免阻塞UI
        fetch_thread = threading.Thread(target=fetch_friends)
        fetch_thread.daemon = True
        fetch_thread.start()
    
    def update_friends_data(self, friends_data):
        """更新好友数据"""
        self.friends_data = friends_data
        self.init_friends_data()

class FriendListApp(wx.App):
    def OnInit(self):
        # 创建不带预设数据的好友列表窗口
        frame = FriendListFrame()
        frame.Show()
        return True

if __name__ == '__main__':
    app = wx.App()
    frame = FriendListFrame()
    frame.Show()
    app.MainLoop()