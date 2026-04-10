import wx

class FriendInfoFrame(wx.Frame):
    def __init__(self, friend_name, friend_email, username=None, friend_id=None):
        super().__init__(None, title="好友信息", size=(400, 400))
        try:
            import os
            icon = wx.Icon(os.path.join(os.path.dirname(__file__), 'app.ico'))
            self.SetIcon(icon)
        except Exception:
            pass
        
        # 居中显示
        self.Center()
        
        # 保存当前用户名
        self.username = username
        # 保存好友ID
        self.friend_id = friend_id
        # 保存用户ID
        self.user_id = None
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加标题区域
        self.create_header_section(main_sizer)
        
        # 添加好友信息区域
        self.create_info_section(main_sizer, friend_name, friend_email)
        
        # 添加按钮区域
        self.create_button_section(main_sizer)
        
        # 设置主面板的布局
        self.panel.SetSizer(main_sizer)
        
        # 初始化时获取用户ID和备注
        self.init_data()
        
    def create_header_section(self, sizer):
        """创建标题区域"""
        # 标题区域
        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 添加标题
        title_text = wx.StaticText(self.panel, label="好友信息")
        title_font = title_text.GetFont()
        title_font.PointSize += 8
        title_font = title_font.Bold()
        title_text.SetFont(title_font)
        
        header_sizer.Add(title_text, 1, wx.ALL | wx.CENTER, 10)
        
        sizer.Add(header_sizer, 0, wx.ALL | wx.EXPAND, 5)
        
    def create_info_section(self, sizer, friend_name, friend_email):
        """创建好友信息区域"""
        # 创建信息面板
        info_panel = wx.Panel(self.panel)
        info_sizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=15)
        info_sizer.AddGrowableCol(1, 1)
        
        # 好友头像（使用标准图标占位）
        avatar_bitmap = wx.ArtProvider.GetBitmap(wx.ART_HELP_BOOK, wx.ART_OTHER, (64, 64))
        avatar_static_bitmap = wx.StaticBitmap(info_panel, bitmap=avatar_bitmap)
        
        # 好友信息
        info_right_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 用户名
        username_label = wx.StaticText(info_panel, label="用户名:")
        self.username_text = wx.TextCtrl(info_panel, value=friend_name, size=(200, -1))
        self.username_text.Enable(False)  # 设置为只读
        
        # 邮箱
        email_label = wx.StaticText(info_panel, label="邮箱:")
        self.email_text = wx.TextCtrl(info_panel, value=friend_email, size=(200, -1))
        self.email_text.Enable(False)  # 设置为只读
        
        # 备注
        remark_label = wx.StaticText(info_panel, label="备注:")
        remark_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.remark_text = wx.TextCtrl(info_panel, value="", size=(150, -1))
        self.remark_text.Enable(False)  # 默认只读
        self.edit_remark_btn = wx.Button(info_panel, label="修改", size=(50, -1))
        self.edit_remark_btn.Bind(wx.EVT_BUTTON, self.on_edit_remark)
        
        remark_sizer.Add(self.remark_text, 1, wx.EXPAND)
        remark_sizer.Add(self.edit_remark_btn, 0, wx.LEFT, 5)
        
        # 添加到信息布局
        info_right_sizer.Add(username_label, 0, wx.TOP, 5)
        info_right_sizer.Add(self.username_text, 0, wx.EXPAND)
        info_right_sizer.Add(email_label, 0, wx.TOP, 10)
        info_right_sizer.Add(self.email_text, 0, wx.EXPAND)
        info_right_sizer.Add(remark_label, 0, wx.TOP, 10)
        info_right_sizer.Add(remark_sizer, 0, wx.EXPAND)
        
        # 添加到信息面板布局
        info_sizer.Add(avatar_static_bitmap, 0, wx.ALL | wx.CENTER, 5)
        info_sizer.Add(info_right_sizer, 1, wx.ALL | wx.EXPAND, 5)
        
        info_panel.SetSizer(info_sizer)
        sizer.Add(info_panel, 0, wx.ALL | wx.EXPAND, 15)
        
    def create_button_section(self, sizer):
        """创建按钮区域"""
        # 按钮面板
        button_panel = wx.Panel(self.panel)
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 开始聊天按钮
        chat_btn = wx.Button(button_panel, label="开始聊天", size=(100, 35))
        chat_btn.SetBackgroundColour(wx.Colour(0, 120, 215))
        chat_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        chat_btn.Bind(wx.EVT_BUTTON, self.on_start_chat)
        
        # 删除好友按钮
        delete_btn = wx.Button(button_panel, label="删除好友", size=(100, 35))
        delete_btn.SetBackgroundColour(wx.Colour(255, 0, 0))
        delete_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        delete_btn.Bind(wx.EVT_BUTTON, self.on_delete_friend)
        
        # 关闭按钮
        close_btn = wx.Button(button_panel, label="关闭", size=(100, 35))
        close_btn.Bind(wx.EVT_BUTTON, self.on_close)
        
        # 添加按钮到布局
        button_sizer.Add(chat_btn, 0, wx.ALL, 5)
        button_sizer.AddStretchSpacer(1)
        button_sizer.Add(delete_btn, 0, wx.ALL, 5)
        button_sizer.Add(close_btn, 0, wx.ALL, 5)
        
        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.ALL | wx.EXPAND, 10)
        
    def init_data(self):
        """初始化数据"""
        import socket
        import json
        import threading
        
        def fetch_data():
            try:
                SERVER_HOST = 'localhost'
                SERVER_PORT = 8892
                
                # 获取用户ID
                if self.username:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((SERVER_HOST, SERVER_PORT))
                    client_socket.send(json.dumps({'action': 'get_user_id', 'username': self.username}, ensure_ascii=False).encode('utf-8'))
                    resp = json.loads(client_socket.recv(1024).decode('utf-8'))
                    client_socket.close()
                    if resp.get('status') == 'success':
                        self.user_id = resp.get('user_id')
                
                # 获取备注
                if self.user_id and self.friend_id:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((SERVER_HOST, SERVER_PORT))
                    client_socket.send(json.dumps({
                        'action': 'get_remark',
                        'user_id': self.user_id,
                        'friend_id': self.friend_id
                    }, ensure_ascii=False).encode('utf-8'))
                    resp = json.loads(client_socket.recv(1024).decode('utf-8'))
                    client_socket.close()
                    if resp.get('status') == 'success':
                        remark = resp.get('remark', '')
                        wx.CallAfter(self.remark_text.SetValue, remark)
            except Exception as e:
                print(f"初始化数据失败: {e}")
        
        # 在后台线程中获取数据
        thread = threading.Thread(target=fetch_data)
        thread.daemon = True
        thread.start()
    
    def on_edit_remark(self, event):
        """修改备注按钮事件处理"""
        if self.remark_text.IsEnabled():
            # 保存修改
            new_remark = self.remark_text.GetValue()
            self.save_remark(new_remark)
        else:
            # 开始编辑
            self.remark_text.Enable(True)
            self.edit_remark_btn.SetLabel("保存")
    
    def save_remark(self, remark):
        """保存备注到服务器"""
        if not self.user_id or not self.friend_id:
            wx.MessageBox("无法保存备注：缺少用户ID或好友ID", "错误", wx.OK | wx.ICON_ERROR)
            return
            
        import socket
        import json
        import threading
        
        def save_to_server():
            try:
                SERVER_HOST = 'localhost'
                SERVER_PORT = 8892
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((SERVER_HOST, SERVER_PORT))
                
                request_data = {
                    'action': 'set_remark',
                    'user_id': self.user_id,
                    'friend_id': self.friend_id,
                    'remark': remark
                }
                client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                response_data = client_socket.recv(1024).decode('utf-8')
                client_socket.close()
                response = json.loads(response_data)
                
                if response.get('status') == 'success':
                    wx.CallAfter(self.remark_text.Enable, False)
                    wx.CallAfter(self.edit_remark_btn.SetLabel, "修改")
                    wx.CallAfter(wx.MessageBox, f"备注已保存为: {remark}", "保存成功", wx.OK | wx.ICON_INFORMATION)
                else:
                    wx.CallAfter(wx.MessageBox, f"保存失败：{response.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"保存失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        
        # 在后台线程中保存
        thread = threading.Thread(target=save_to_server)
        thread.daemon = True
        thread.start()
            
    def on_start_chat(self, event):
        """开始聊天按钮事件处理"""
        friend_name = self.username_text.GetValue()
        # 使用备注构造显示名：好友名（备注）
        remark = self.remark_text.GetValue().strip() if hasattr(self, 'remark_text') else ''
        display_name = friend_name if not remark else f"{friend_name}（{remark}）"
        # 导入聊天界面模块
        from chat_ui import ChatFrame
        import wx
        
        # 确保在打开聊天前拿到 user_id（离线消息依赖 user_id/friend_id）
        if not self.user_id and self.username:
            import socket, json
            try:
                SERVER_HOST = 'localhost'
                SERVER_PORT = 8892
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((SERVER_HOST, SERVER_PORT))
                client_socket.send(json.dumps({'action': 'get_user_id', 'username': self.username}, ensure_ascii=False).encode('utf-8'))
                resp = json.loads(client_socket.recv(1024).decode('utf-8'))
                client_socket.close()
                if resp.get('status') == 'success':
                    self.user_id = resp.get('user_id')
            except Exception:
                pass
        
        # 创建聊天窗口，传递用户ID和好友ID
        chat_frame = ChatFrame(display_name, username=self.username, 
                              user_id=self.user_id, friend_id=self.friend_id)
        chat_frame.Show()
        
        # 关闭当前窗口
        self.Close()
        
    def on_delete_friend(self, event):
        """删除好友按钮事件处理"""
        friend_name = self.username_text.GetValue()
        confirm = wx.MessageBox(f"确定要删除好友 {friend_name} 吗？", "确认删除", 
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if confirm == wx.YES:
            import socket
            import json
            try:
                SERVER_HOST = 'localhost'
                SERVER_PORT = 8892

                # 先获取当前用户ID
                user_id = None
                if self.username:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((SERVER_HOST, SERVER_PORT))
                    client_socket.send(json.dumps({'action': 'get_user_id', 'username': self.username}, ensure_ascii=False).encode('utf-8'))
                    resp = json.loads(client_socket.recv(1024).decode('utf-8'))
                    client_socket.close()
                    if resp.get('status') == 'success':
                        user_id = resp.get('user_id')

                if not user_id:
                    wx.MessageBox("无法获取当前用户ID", "错误", wx.OK | wx.ICON_ERROR)
                    return

                if not self.friend_id:
                    wx.MessageBox("无法获取好友ID", "错误", wx.OK | wx.ICON_ERROR)
                    return

                # 发送删除请求，统一使用IDs
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((SERVER_HOST, SERVER_PORT))
                request_data = {
                    'action': 'remove_friend',
                    'user_id': user_id,
                    'friend_id': self.friend_id
                }
                client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                response_data = client_socket.recv(1024).decode('utf-8')
                client_socket.close()
                response = json.loads(response_data)
                if response.get('status') == 'success':
                    wx.MessageBox(f"好友 {friend_name} 已删除", "删除成功", wx.OK | wx.ICON_INFORMATION)
                    self.Close()
                else:
                    wx.MessageBox(f"删除失败：{response.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"删除失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        
    def on_close(self, event):
        """关闭按钮事件处理"""
        self.Close()

def main():
    # 虚拟信息定义在main函数中
    friend_name = "张三"
    friend_email = "zhangsan@example.com"
    
    app = wx.App()
    frame = FriendInfoFrame(friend_name, friend_email)
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    friend_name = "张三"
    friend_email = "zhangsan@example.com"
    
    app = wx.App()
    frame = FriendInfoFrame(friend_name, friend_email)
    frame.Show()
    app.MainLoop()