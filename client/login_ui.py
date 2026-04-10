import wx
import socket
import json
import threading

# 服务器配置
SERVER_HOST = 'localhost'
SERVER_PORT = 8888

class LoginFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="用户登录", size=(400, 500))
        try:
            import os
            icon = wx.Icon(os.path.join(os.path.dirname(__file__), 'app.ico'))
            self.SetIcon(icon)
        except Exception:
            pass
        
        # 居中显示
        self.Center()
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加logo区域（占位）
        self.create_logo_section(main_sizer)
        
        # 添加表单区域
        self.create_form_section(main_sizer)
        
        # 添加按钮区域
        self.create_button_section(main_sizer)
        
        # 设置主面板的布局
        self.panel.SetSizer(main_sizer)
        
    def create_logo_section(self, sizer):
        """创建logo区域"""
        # logo区域
        logo_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        # 使用标准图标作为logo占位符
        logo_bitmap = wx.ArtProvider.GetBitmap(wx.ART_TIP, wx.ART_OTHER, (64, 64))
        logo_static_bitmap = wx.StaticBitmap(self.panel, bitmap=logo_bitmap)
        
        logo_sizer.Add(logo_static_bitmap, 0, wx.ALL | wx.CENTER, 10)
        
        # 添加标题
        title_text = wx.StaticText(self.panel, label="用户登录")
        title_font = title_text.GetFont()
        title_font.PointSize += 10
        title_font = title_font.Bold()
        title_text.SetFont(title_font)
        
        logo_sizer.Add(title_text, 0, wx.ALL | wx.CENTER, 10)
        
        sizer.Add(logo_sizer, 0, wx.ALL | wx.CENTER, 10)
        
    def create_form_section(self, sizer):
        """创建表单区域"""
        # 创建表单面板
        form_panel = wx.Panel(self.panel)
        form_sizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=10)
        form_sizer.AddGrowableCol(1, 1)
        
        # 用户名标签和输入框
        username_label = wx.StaticText(form_panel, label="用户名:")
        self.username_text = wx.TextCtrl(form_panel, size=(200, -1))
        
        # 密码标签和输入框
        password_label = wx.StaticText(form_panel, label="密码:")
        self.password_text = wx.TextCtrl(form_panel, style=wx.TE_PASSWORD, size=(200, -1))
        
        # 添加到表单布局
        form_sizer.Add(username_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.username_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.password_text, 1, wx.EXPAND | wx.RIGHT, 10)
        
        form_panel.SetSizer(form_sizer)
        sizer.Add(form_panel, 0, wx.ALL | wx.EXPAND, 10)
        
    def create_button_section(self, sizer):
        """创建按钮区域"""
        # 按钮面板
        button_panel = wx.Panel(self.panel)
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 登录按钮
        login_btn = wx.Button(button_panel, label="登录", size=(200, 35))
        login_btn.SetBackgroundColour(wx.Colour(0, 120, 215))
        login_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        
        # 注册按钮
        register_btn = wx.Button(button_panel, label="注册账号", size=(200, 35))
        register_btn.Bind(wx.EVT_BUTTON, self.on_register)
        
        # 忘记密码按钮
        forget_btn = wx.Button(button_panel, label="忘记密码?", size=(200, 35))
        forget_btn.Bind(wx.EVT_BUTTON, self.on_forgot_password)
        
        # 添加按钮到布局
        button_sizer.Add(login_btn, 0, wx.ALL | wx.CENTER, 5)
        button_sizer.Add(register_btn, 0, wx.ALL | wx.CENTER, 5)
        button_sizer.Add(forget_btn, 0, wx.ALL | wx.CENTER, 5)
        
        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.ALL | wx.CENTER, 10)
        
    def on_login(self, event):
        """登录按钮事件处理"""
        username = self.username_text.GetValue()
        password = self.password_text.GetValue()
        
        if not username or not password:
            wx.MessageBox("请输入用户名和密码！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        # 创建一个线程来处理登录请求，避免阻塞UI
        login_thread = threading.Thread(target=self.perform_login, args=(username, password))
        login_thread.daemon = True
        login_thread.start()
        
    def perform_login(self, username, password):
        """执行登录操作"""
        try:
            # 创建socket连接
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            
            # 准备登录数据
            login_data = {
                'username': username,
                'password': password
            }
            
            # 发送数据到服务器
            client_socket.send(json.dumps(login_data, ensure_ascii=False).encode('utf-8'))
            
            # 接收服务器响应
            response_data = client_socket.recv(1024).decode('utf-8')
            response = json.loads(response_data)
            
            # 关闭socket连接
            client_socket.close()
            
            # 在主线程中更新UI
            wx.CallAfter(self.handle_login_response, response)
            
        except Exception as e:
            wx.CallAfter(wx.MessageBox, f"登录失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            
    def handle_login_response(self, response):
        """处理登录响应"""
        if response.get('status') == 'success':
            wx.MessageBox(f"登录成功！\n欢迎 {response.get('username')}", "登录结果", wx.OK | wx.ICON_INFORMATION)
            # 登录成功后打开好友列表界面
            username = response.get('username')
            from friendlist_ui import FriendListFrame
            friendlist_frame = FriendListFrame(username=username)  # 传递用户名给好友列表界面
            friendlist_frame.Show()
            self.Close()  # 关闭登录界面
        else:
            wx.MessageBox(f"登录失败：{response.get('message')}", "登录结果", wx.OK | wx.ICON_ERROR)
        
    def on_register(self, event):
        """注册按钮事件处理"""
        # 这里可以添加跳转到注册页面的逻辑
        from register_ui import RegisterFrame
        register_frame = RegisterFrame()
        register_frame.Show()
        self.Close()
        
    def on_forgot_password(self, event):
        """忘记密码按钮事件处理"""
        # 打开忘记密码界面
        from forgot_ui import ForgotPasswordFrame
        forgot_frame = ForgotPasswordFrame()
        forgot_frame.Show()
        # 关闭当前登录界面
        self.Close()

class LoginApp(wx.App):
    def OnInit(self):
        frame = LoginFrame()
        frame.Show()
        return True

if __name__ == '__main__':
    app = LoginApp()
    app.MainLoop()