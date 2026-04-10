import wx
import re
import socket
import threading
import json

class ForgotPasswordFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="忘记密码", size=(450, 500))
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
        title_text = wx.StaticText(self.panel, label="忘记密码")
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
        
        # 新密码标签和输入框
        password_label = wx.StaticText(form_panel, label="新密码:")
        self.password_text = wx.TextCtrl(form_panel, style=wx.TE_PASSWORD, size=(200, -1))
        self.password_text.Bind(wx.EVT_TEXT, self.on_password_change)
        self.password_tip = wx.StaticText(form_panel, label="", size=(200, -1))
        
        # 确认密码标签和输入框
        confirm_label = wx.StaticText(form_panel, label="确认密码:")
        self.confirm_text = wx.TextCtrl(form_panel, style=wx.TE_PASSWORD, size=(200, -1))
        self.confirm_text.Bind(wx.EVT_TEXT, self.on_confirm_change)
        self.confirm_tip = wx.StaticText(form_panel, label="", size=(200, -1))
        self.confirm_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色提示
        
        # 添加到表单布局
        form_sizer.Add(email_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.email_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(self.email_tip, 0, wx.ALIGN_CENTER_VERTICAL)
        
        form_sizer.Add(captcha_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(captcha_sizer, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.AddSpacer(0)
        
        form_sizer.Add(password_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.password_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(self.password_tip, 0, wx.ALIGN_CENTER_VERTICAL)
        
        form_sizer.Add(confirm_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        form_sizer.Add(self.confirm_text, 1, wx.EXPAND | wx.RIGHT, 10)
        form_sizer.Add(self.confirm_tip, 0, wx.ALIGN_CENTER_VERTICAL)
        
        form_panel.SetSizer(form_sizer)
        sizer.Add(form_panel, 0, wx.ALL | wx.EXPAND, 10)
        
    def create_button_section(self, sizer):
        """创建按钮区域"""
        # 按钮面板
        button_panel = wx.Panel(self.panel)
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 确认重置按钮
        self.reset_btn = wx.Button(button_panel, label="重置密码", size=(200, 35))
        self.reset_btn.SetBackgroundColour(wx.Colour(0, 120, 215))
        self.reset_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.reset_btn.Bind(wx.EVT_BUTTON, self.on_reset_password)
        self.reset_btn.Enable(False)  # 初始禁用重置按钮
        
        # 返回登录按钮
        back_btn = wx.Button(button_panel, label="返回登录", size=(200, 35))
        back_btn.Bind(wx.EVT_BUTTON, self.on_back_to_login)
        
        # 添加按钮到布局
        button_sizer.Add(self.reset_btn, 0, wx.ALL | wx.CENTER, 5)
        button_sizer.Add(back_btn, 0, wx.ALL | wx.CENTER, 5)
        
        button_panel.SetSizer(button_sizer)
        sizer.Add(button_panel, 0, wx.ALL | wx.CENTER, 10)
        
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
        
    def on_confirm_change(self, event):
        """确认密码输入变化事件处理"""
        password = self.password_text.GetValue()
        confirm = self.confirm_text.GetValue()
        
        if not confirm:
            self.confirm_tip.SetLabel("")
            self.check_all_fields()
            return
            
        # 检查密码是否一致
        if password == confirm:
            self.confirm_tip.SetLabel("✓ 密码一致")
            self.confirm_tip.SetForegroundColour(wx.Colour(0, 128, 0))  # 绿色
        else:
            self.confirm_tip.SetLabel("✗ 密码不一致")
            self.confirm_tip.SetForegroundColour(wx.Colour(255, 0, 0))  # 红色
            
        self.check_all_fields()
        self.Layout()
        self.Refresh()
        
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
            # 连接到forgot服务器
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15)  # 延长超时时间到15秒
            print("[DEBUG] 尝试连接到忘记密码服务器 localhost:8890...")
            s.connect(('localhost', 8890))  # 连接到forgot服务器
            print("[DEBUG] 成功连接到忘记密码服务器")
            
            # 发送获取验证码请求
            request = {
                'action': 'send_code',
                'email': email
            }
            request_json = json.dumps(request, ensure_ascii=False)
            print(f"[DEBUG] 发送请求: {request_json}")
            s.send(request_json.encode('utf-8'))
            
            # 接收服务端响应
            response = s.recv(1024).decode('utf-8')
            print(f"[DEBUG] 收到服务器响应: {response}")
            
            s.close()  # 关闭连接
            
            # 解析响应
            try:
                response_data = json.loads(response)
                if response_data.get('status') == 'success':
                    wx.CallAfter(wx.MessageBox, response_data.get('message', '验证码已发送到您的邮箱，请查收！'), "成功", wx.OK | wx.ICON_INFORMATION)
                    return True
                else:
                    wx.CallAfter(wx.MessageBox, response_data.get('message', '发送失败'), "发送失败", wx.OK | wx.ICON_WARNING)
                    return False
            except json.JSONDecodeError:
                wx.CallAfter(wx.MessageBox, f"收到无效响应：{response}", "响应错误", wx.OK | wx.ICON_ERROR)
                return False
                
        except socket.timeout:
            error_msg = "忘记密码服务器连接超时，请稍后重试！"
            wx.CallAfter(wx.MessageBox, error_msg, "连接超时", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")
            return False
        except ConnectionRefusedError:
            error_msg = "无法连接到忘记密码服务器，请检查服务器是否启动！"
            wx.CallAfter(wx.MessageBox, error_msg, "连接失败", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")
            return False
        except Exception as e:
            error_msg = f"连接忘记密码服务器时发生错误：{str(e)}"
            wx.CallAfter(wx.MessageBox, error_msg, "连接错误", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")
            return False
            
    def on_reset_password(self, event):
        """重置密码按钮事件处理"""
        email = self.email_text.GetValue()
        captcha = self.captcha_text.GetValue()
        password = self.password_text.GetValue()
        confirm = self.confirm_text.GetValue()
        
        if not email or not captcha or not password or not confirm:
            wx.MessageBox("请填写所有必填信息！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        # 检查密码是否一致
        if password != confirm:
            wx.MessageBox("两次输入的密码不一致！", "提示", wx.OK | wx.ICON_INFORMATION)
            return
            
        # 创建一个线程来处理密码重置请求，避免阻塞UI
        reset_thread = threading.Thread(target=self.reset_password_request, args=(email, captcha, password))
        reset_thread.daemon = True
        reset_thread.start()
        
    def reset_password_request(self, email, captcha, password):
        """向服务端发送密码重置请求"""
        print(f"[DEBUG] 开始发送密码重置请求: {email}")
        try:
            # 连接到forgot服务器
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(15)
            print("[DEBUG] 尝试连接到忘记密码服务器 localhost:8890...")
            s.connect(('localhost', 8890))
            print("[DEBUG] 成功连接到忘记密码服务器")
            
            # 发送密码重置请求
            request = {
                'action': 'reset_password',
                'email': email,
                'code': captcha,
                'password': password
            }
            request_json = json.dumps(request, ensure_ascii=False)
            print(f"[DEBUG] 发送请求: {request_json}")
            s.send(request_json.encode('utf-8'))
            
            # 接收服务端响应
            response = s.recv(1024).decode('utf-8')
            print(f"[DEBUG] 收到服务器响应: {response}")
            
            s.close()
            
            # 解析响应
            try:
                response_data = json.loads(response)
                if response_data.get('status') == 'success':
                    wx.CallAfter(wx.MessageBox, response_data.get('message', '密码重置成功！'), "重置成功", wx.OK | wx.ICON_INFORMATION)
                    # 重置成功后返回登录界面
                    wx.CallAfter(self.on_back_to_login, None)
                else:
                    wx.CallAfter(wx.MessageBox, response_data.get('message', '密码重置失败'), "重置失败", wx.OK | wx.ICON_ERROR)
            except json.JSONDecodeError:
                wx.CallAfter(wx.MessageBox, f"收到无效响应：{response}", "响应错误", wx.OK | wx.ICON_ERROR)
                
        except socket.timeout:
            error_msg = "忘记密码服务器连接超时，请稍后重试！"
            wx.CallAfter(wx.MessageBox, error_msg, "连接超时", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")
        except ConnectionRefusedError:
            error_msg = "无法连接到忘记密码服务器，请检查服务器是否启动！"
            wx.CallAfter(wx.MessageBox, error_msg, "连接失败", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")
        except Exception as e:
            error_msg = f"连接忘记密码服务器时发生错误：{str(e)}"
            wx.CallAfter(wx.MessageBox, error_msg, "连接错误", wx.OK | wx.ICON_ERROR)
            print(f"[ERROR] {error_msg}")
        
    def on_back_to_login(self, event):
        """返回登录按钮事件处理"""
        # 打开登录界面
        from login_ui import LoginFrame
        login_frame = LoginFrame()
        login_frame.Show()
        # 关闭当前忘记密码界面
        self.Close()
        
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
        """检查所有字段是否都有效，以决定是否启用重置按钮"""
        email = self.email_text.GetValue()
        password = self.password_text.GetValue()
        confirm = self.confirm_text.GetValue()
        
        # 检查邮箱是否合法
        email_valid = self.is_valid_email(email) if email else False
        
        # 检查密码是否至少为弱强度
        password_valid = False
        if password:
            strength = self.check_password_strength(password)
            password_valid = strength[0] >= 1  # 至少为弱强度
            
        # 检查密码是否一致
        confirm_valid = (password == confirm) if password and confirm else False
        
        # 只有所有字段都有效时才启用重置按钮
        self.reset_btn.Enable(email_valid and password_valid and confirm_valid)

class ForgotPasswordApp(wx.App):
    def OnInit(self):
        frame = ForgotPasswordFrame()
        frame.Show()
        return True

if __name__ == '__main__':
    app = ForgotPasswordApp()
    app.MainLoop()