import wx
import re
import socket
import json
import threading

# 服务器配置
SERVER_HOST = 'localhost'
SERVER_PORT = 8889

class RegisterFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="用户注册", size=(450, 650))
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
        title_text = wx.StaticText(self.panel, label="用户注册")
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
        form_sizer = wx.FlexGridSizer(cols=3, hgap=10, vgap=10)
        form_sizer.AddGrowableCol(1, 1)
        
        # 用户名标签和输入框
        username_label = wx.StaticText(form_panel, label="用户名:")
        self.username_text = wx.TextCtrl(form_panel, size=(200, -1))
        self.username_text.Bind(wx.EVT_TEXT, self.on_username_change)
        self.username_tip = wx.StaticText(form_panel, label="", size=(200, -1))
        self.username_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色提示
        
        # 密码标签和输入框
        password_label = wx.StaticText(form_panel, label="密码:")
        self.password_text = wx.TextCtrl(form_panel, style=wx.TE_PASSWORD, size=(200, -1))
        self.password_text.Bind(wx.EVT_TEXT, self.on_password_change)
        self.password_tip = wx.StaticText(form_panel, label="", size=(200, -1))
        
        # 邮箱标签和输入框
        email_label = wx.StaticText(form_panel, label="邮箱:")
        self.email_text = wx.TextCtrl(form_panel, size=(200, -1))
        self.email_text.Bind(wx.EVT_TEXT, self.on_email_change)
        self.email_tip = wx.StaticText(form_panel, label="", size=(200, -1))
        self.email_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色提示
        
        # 验证码标签、输入框和发送按钮
        captcha_label = wx.StaticText(form_panel, label="验证码:")
        captcha_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.captcha_text = wx.TextCtrl(form_panel, size=(120, -1))
        self.send_captcha_btn = wx.Button(form_panel, label="发送验证码", size=(80, -1))
        self.send_captcha_btn.Bind(wx.EVT_BUTTON, self.on_send_captcha)
        
        captcha_sizer.Add(self.captcha_text, 1, wx.EXPAND)
        captcha_sizer.Add(self.send_captcha_btn, 0, wx.LEFT, 5)
        
        # 添加到表单布局
        form_sizer.Add(username_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.username_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(self.username_tip, 0, wx.ALIGN_CENTER_VERTICAL)
        
        form_sizer.Add(password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.password_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(self.password_tip, 0, wx.ALIGN_CENTER_VERTICAL)
        
        form_sizer.Add(email_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.email_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(self.email_tip, 0, wx.ALIGN_CENTER_VERTICAL)
        
        form_sizer.Add(captcha_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(captcha_sizer, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.AddSpacer(0)
        
        form_panel.SetSizer(form_sizer)
        sizer.Add(form_panel, 0, wx.ALL | wx.EXPAND, 10)
        
    def create_button_section(self, sizer):
        """创建按钮区域"""
        # 按钮面板
        button_panel = wx.Panel(self.panel)
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 注册按钮
        self.register_btn = wx.Button(button_panel, label="注册", size=(200, 35))
        self.register_btn.SetBackgroundColour(wx.Colour(0, 120, 215))
        self.register_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.register_btn.Bind(wx.EVT_BUTTON, self.on_register)
        self.register_btn.Enable(False)  # 初始禁用注册按钮
        
        # 返回登录按钮
        back_login_btn = wx.Button(button_panel, label="返回登录", size=(200, 35))
        back_login_btn.Bind(wx.EVT_BUTTON, self.on_back_to_login)
        
        # 添加按钮到布局
        button_sizer.Add(self.register_btn, 0, wx.ALL | wx.CENTER, 5)
        button_sizer.Add(back_login_btn, 0, wx.ALL | wx.CENTER, 5)
        
        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.ALL | wx.CENTER, 10)
        
    def on_username_change(self, event):
        """用户名输入变化事件处理"""
        username = self.username_text.GetValue()
        
        if not username:
            self.username_tip.SetLabel("")
            self.check_all_fields()
            return
            
        # 检查用户名合法性（仅字母、数字、下划线）
        if re.match(r'^[a-zA-Z0-9_]+$', username):
            if len(username) < 3:
                self.username_tip.SetLabel("用户名至少3个字符")
                self.username_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色
            elif len(username) > 20:
                self.username_tip.SetLabel("用户名最多20个字符")
                self.username_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色
            else:
                self.username_tip.SetLabel("✓ 用户名可用")
                self.username_tip.SetForegroundColour(wx.Colour(0, 128, 0))  # 绿色
        else:
            self.username_tip.SetLabel("只能包含字母、数字、下划线")
            self.username_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色
            
        self.check_all_fields()
        self.Layout()
        self.Refresh()
        
    def on_password_change(self, event):
        """密码输入变化事件处理"""
        password = self.password_text.GetValue()
        
        if not password:
            self.password_tip.SetLabel("")
            self.check_all_fields()
            return
            
        # 检查密码强度
        strength = self.check_password_strength(password)
        self.password_tip.SetLabel(strength[1])
        self.password_tip.SetForegroundColour(strength[2])
        
        self.check_all_fields()
        self.Layout()
        self.Refresh()
        
    def on_email_change(self, event):
        """邮箱输入变化事件处理"""
        email = self.email_text.GetValue()
        
        if not email:
            self.email_tip.SetLabel("")
            self.check_all_fields()
            return
            
        # 检查邮箱合法性
        if self.is_valid_email(email):
            self.email_tip.SetLabel("✓ 邮箱格式正确")
            self.email_tip.SetForegroundColour(wx.Colour(0, 128, 0))  # 绿色
        else:
            self.email_tip.SetLabel("请输入有效的邮箱地址")
            self.email_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色
            
        self.check_all_fields()
        self.Layout()
        self.Refresh()
        
    def check_password_strength(self, password):
        """
        检查密码强度
        返回: (强度等级, 描述文本, 颜色)
        """
        length = len(password)
        has_lower = bool(re.search(r'[a-z]', password))
        has_upper = bool(re.search(r'[A-Z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        # 计算强度分数
        score = 0
        if length >= 8:
            score += 1
        if has_lower:
            score += 1
        if has_upper:
            score += 1
        if has_digit:
            score += 1
        if has_special:
            score += 1
            
        # 根据分数判断强度
        if score < 3:
            return (1, "弱密码", wx.Colour(255, 0, 0))  # 红色
        elif score < 5:
            return (2, "中等强度", wx.Colour(255, 165, 0))  # 橙色
        else:
            return (3, "强密码", wx.Colour(0, 128, 0))  # 绿色
            
    def is_valid_email(self, email):
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
        
    def check_all_fields(self):
        """检查所有字段是否都有效，以决定是否启用注册按钮"""
        username = self.username_text.GetValue()
        password = self.password_text.GetValue()
        email = self.email_text.GetValue()
        
        # 检查用户名是否合法
        username_valid = False
        if username and re.match(r'^[a-zA-Z0-9_]+$', username) and 3 <= len(username) <= 20:
            username_valid = True
        
        # 检查密码是否至少为弱强度
        password_valid = False
        if password:
            strength = self.check_password_strength(password)
            password_valid = strength[0] >= 1  # 至少为弱强度
            
        # 检查邮箱是否合法
        email_valid = self.is_valid_email(email) if email else False
        
        # 只有所有字段都有效时才启用注册按钮
        self.register_btn.Enable(username_valid and password_valid and email_valid)
        
    def on_send_captcha(self, event):
        """发送验证码按钮事件处理"""
        email = self.email_text.GetValue()
        
        if not email:
            wx.MessageBox("请输入邮箱地址！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        # 验证邮箱格式
        if not self.is_valid_email(email):
            wx.MessageBox("请输入有效的邮箱地址！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        # 创建一个线程来处理验证码发送请求，避免阻塞UI
        captcha_thread = threading.Thread(target=self.send_captcha_request, args=(email,))
        captcha_thread.daemon = True
        captcha_thread.start()
        
    def send_captcha_request(self, email):
        """向服务端发送获取验证码请求"""
        print(f"[DEBUG] 开始发送验证码请求到邮箱: {email}")
        try:
            # 连接到服务端
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15)  # 延长超时时间到15秒
            print("[DEBUG] 尝试连接到验证码服务器 localhost:12123...")
            s.connect(('localhost', 12123))  # 连接到服务端
            print("[DEBUG] 成功连接到验证码服务器")
            
            # 发送获取验证码请求
            request = f"SEND|{email}"
            print(f"[DEBUG] 发送请求: {request}")
            s.send(request.encode('utf-8'))
            
            # 接收服务端响应
            response = s.recv(1024).decode('utf-8')
            print(f"[DEBUG] 收到服务器响应: {response}")
            
            s.close()  # 关闭连接
            
            if response.startswith("SUCCESS"):
                wx.CallAfter(wx.MessageBox, "验证码已发送到您的邮箱，请查收！", "成功", wx.OK | wx.ICON_INFORMATION)
                return True
            elif response.startswith("EMAIL_ERROR"):
                wx.CallAfter(wx.MessageBox, "请输入正确的邮箱地址！", "邮箱格式错误", wx.OK | wx.ICON_WARNING)
                return False
            elif response.startswith("FREQUENCY_ERROR"):
                wx.CallAfter(wx.MessageBox, "验证码发送过于频繁，请稍后再试！", "发送频繁", wx.OK | wx.ICON_WARNING)
                return False
            elif response.startswith("SERVER_ERROR"):
                error_msg = response.split('|')[1] if '|' in response else "未知服务器错误"
                wx.CallAfter(wx.MessageBox, f"服务器内部错误：{error_msg}", "服务器错误", wx.OK | wx.ICON_ERROR)
                return False
            else:
                wx.CallAfter(wx.MessageBox, f"收到未知响应：{response}", "未知错误", wx.OK | wx.ICON_ERROR)
                return False
                
        except socket.timeout:
            error_msg = "验证码服务器连接超时，请稍后重试！"
            wx.CallAfter(wx.MessageBox, error_msg, "连接超时", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")  # 添加日志输出
            return False
        except ConnectionRefusedError:
            error_msg = "无法连接到验证码服务器，请检查服务器是否启动！"
            wx.CallAfter(wx.MessageBox, error_msg, "连接失败", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")  # 添加日志输出
            return False
        except Exception as e:
            error_msg = f"连接验证码服务器时发生错误：{str(e)}"
            wx.CallAfter(wx.MessageBox, error_msg, "连接错误", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")  # 添加日志输出
            return False
            
    def on_register(self, event):
        """注册按钮事件处理"""
        username = self.username_text.GetValue()
        password = self.password_text.GetValue()
        email = self.email_text.GetValue()
        captcha = self.captcha_text.GetValue()
        
        if not username or not password or not email or not captcha:
            wx.MessageBox("请填写所有必填信息！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        # 创建一个线程来处理注册请求，避免阻塞UI
        register_thread = threading.Thread(target=self.perform_register, args=(username, password, email))
        register_thread.daemon = True
        register_thread.start()
            
    def perform_register(self, username, password, email):
        """执行注册操作"""
        # 获取验证码
        captcha = self.captcha_text.GetValue()
        
        try:
            # 创建socket连接
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((SERVER_HOST, SERVER_PORT))
            
            # 准备注册数据，包含验证码
            register_data = {
                'username': username,
                'password': password,
                'email': email,
                'captcha': captcha
            }
            
            # 发送数据到服务器
            client_socket.send(json.dumps(register_data, ensure_ascii=False).encode('utf-8'))
            
            # 接收服务器响应
            response_data = client_socket.recv(1024).decode('utf-8')
            response = json.loads(response_data)
            
            # 关闭socket连接
            client_socket.close()
            
            # 在主线程中更新UI
            wx.CallAfter(self.handle_register_response, response)
            
        except Exception as e:
            wx.CallAfter(wx.MessageBox, f"注册失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
            
    def handle_register_response(self, response):
        """处理注册响应"""
        if response.get('status') == 'success':
            wx.MessageBox(f"注册成功！\n用户名: {response.get('username')}", "注册结果", wx.OK | wx.ICON_INFORMATION)
            # 注册成功后关闭当前窗口并返回登录界面
            from login_ui import LoginFrame
            login_frame = LoginFrame()
            login_frame.Show()
            self.Close()
        else:
            wx.MessageBox(f"注册失败：{response.get('message')}", "注册结果", wx.OK | wx.ICON_ERROR)

    def on_back_to_login(self, event):
        """返回登录按钮事件处理"""
        # 打开登录界面
        from login_ui import LoginFrame
        login_frame = LoginFrame()
        login_frame.Show()
        # 关闭当前注册界面
        self.Close()

class RegisterApp(wx.App):
    def OnInit(self):
        frame = RegisterFrame()
        frame.Show()
        return True

if __name__ == '__main__':
    app = RegisterApp()
    app.MainLoop()