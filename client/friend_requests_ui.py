import wx
import socket
import json
import threading

class FriendRequestsFrame(wx.Frame):
    def __init__(self, username=None):
        super().__init__(None, title="好友请求", size=(400, 500))
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
        
        # 初始化请求数据
        self.requests_data = []
        
        # 创建主面板
        self.panel = wx.Panel(self)
        
        # 创建垂直布局
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 添加标题
        title_text = wx.StaticText(self.panel, label="好友请求")
        title_font = title_text.GetFont()
        title_font.PointSize += 8
        title_font = title_font.Bold()
        title_text.SetFont(title_font)
        main_sizer.Add(title_text, 0, wx.ALL | wx.CENTER, 10)
        
        # 添加分隔线
        main_sizer.Add(wx.StaticLine(self.panel), 0, wx.ALL | wx.EXPAND, 5)
        
        # 创建好友请求列表
        self.create_requests_list(main_sizer)
        
        # 添加刷新按钮
        refresh_btn = wx.Button(self.panel, label="刷新")
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        main_sizer.Add(refresh_btn, 0, wx.ALL | wx.CENTER, 10)
        
        # 设置主面板的布局
        self.panel.SetSizer(main_sizer)
        
        # 获取好友请求数据
        self.refresh_requests()
        
    def create_requests_list(self, sizer):
        """创建好友请求列表"""
        # 创建列表控件
        self.requests_list = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.requests_list.InsertColumn(0, "请求者", width=150)
        self.requests_list.InsertColumn(1, "状态", width=100)
        
        # 绑定事件
        self.requests_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_item_selected)
        self.requests_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_item_deselected)
        
        # 添加操作按钮
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.accept_btn = wx.Button(self.panel, label="接受")
        self.accept_btn.Bind(wx.EVT_BUTTON, self.on_accept)
        self.accept_btn.Enable(False)
        
        self.reject_btn = wx.Button(self.panel, label="拒绝")
        self.reject_btn.Bind(wx.EVT_BUTTON, self.on_reject)
        self.reject_btn.Enable(False)
        
        btn_sizer.Add(self.accept_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.reject_btn, 0, wx.ALL, 5)
        
        sizer.Add(self.requests_list, 1, wx.ALL | wx.EXPAND, 10)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.CENTER, 5)
        
    def on_item_selected(self, event):
        """列表项被选中时启用按钮"""
        self.accept_btn.Enable(True)
        self.reject_btn.Enable(True)
        
    def on_item_deselected(self, event):
        """列表项被取消选中时禁用按钮"""
        self.accept_btn.Enable(False)
        self.reject_btn.Enable(False)
        
    def on_accept(self, event):
        """接受好友请求"""
        selected_index = self.requests_list.GetFirstSelected()
        if selected_index != -1:
            # 获取请求ID
            request_id = self.requests_data[selected_index]['id']
            self.handle_friend_request(request_id, 'accept')
        
    def on_reject(self, event):
        """拒绝好友请求"""
        selected_index = self.requests_list.GetFirstSelected()
        if selected_index != -1:
            # 获取请求ID
            request_id = self.requests_data[selected_index]['id']
            self.handle_friend_request(request_id, 'reject')
        
    def on_refresh(self, event):
        """刷新好友请求"""
        self.refresh_requests()
        
    def refresh_requests(self):
        """刷新好友请求列表"""
        import socket
        import json
        import threading
        
        # 好友列表服务器配置
        SERVER_HOST = 'localhost'
        SERVER_PORT = 8892  # 好友列表服务器端口
        
        def fetch_requests():
            try:
                # 创建socket连接
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((SERVER_HOST, SERVER_PORT))
                
                # 准备请求数据
                request_data = {
                    'action': 'get_requests',
                    'username': self.username
                }
                
                # 发送数据到服务器
                client_socket.send(json.dumps(request_data, ensure_ascii=False).encode('utf-8'))
                
                # 接收服务器响应
                response_data = client_socket.recv(1024).decode('utf-8')
                response = json.loads(response_data)
                
                # 关闭socket连接
                client_socket.close()
                
                # 在主线程中更新UI
                if response.get('status') == 'success':
                    requests = response.get('requests', [])
                    wx.CallAfter(self.update_requests_list, requests)
                else:
                    wx.CallAfter(wx.MessageBox, f"获取好友请求失败：{response.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
                    
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"获取好友请求失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        
        # 创建一个线程来获取好友请求，避免阻塞UI
        fetch_thread = threading.Thread(target=fetch_requests)
        fetch_thread.daemon = True
        fetch_thread.start()
        
    def update_requests_list(self, requests_data):
        """更新好友请求列表"""
        self.requests_data = requests_data if requests_data else []
        
        # 清空当前列表
        self.requests_list.DeleteAllItems()
        
        # 添加请求到列表
        if requests_data:
            for request in requests_data:
                index = self.requests_list.InsertItem(self.requests_list.GetItemCount(), request.get('requester_name', ''))
                status = request.get('status', 'pending')
                status_text = '待处理' if status == 'pending' else '已接受' if status == 'accepted' else '已拒绝' if status == 'rejected' else status
                self.requests_list.SetItem(index, 1, status_text)
            
    def handle_friend_request(self, request_id, action):
        """处理好友请求（接受或拒绝）"""
        import socket
        import json
        import threading
        
        # 好友列表服务器配置
        SERVER_HOST = 'localhost'
        SERVER_PORT = 8892  # 好友列表服务器端口
        
        def process_request():
            try:
                # 创建socket连接
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((SERVER_HOST, SERVER_PORT))
                
                # 准备请求数据
                request_data = {
                    'action': 'handle_request',
                    'username': self.username,
                    'request_id': request_id,
                    'action_type': action
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
                    wx.CallAfter(wx.MessageBox, f"好友请求已{('接受' if action == 'accept' else '拒绝')}", "操作成功", wx.OK | wx.ICON_INFORMATION)
                    # 刷新好友请求列表
                    wx.CallAfter(self.refresh_requests)
                else:
                    wx.CallAfter(wx.MessageBox, f"操作失败：{response.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
                    
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"操作失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
        
        # 创建一个线程来处理好友请求，避免阻塞UI
        process_thread = threading.Thread(target=process_request)
        process_thread.daemon = True
        process_thread.start()

class FriendRequestsApp(wx.App):
    def OnInit(self):
        frame = FriendRequestsFrame(username="testuser")
        frame.Show()
        return True

if __name__ == '__main__':
    app = wx.App()
    frame = FriendRequestsFrame(username="testuser")
    frame.Show()
    app.MainLoop()