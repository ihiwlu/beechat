import wx
import os
import socket
import json
import time
import base64
import threading


class FileTransferFrame(wx.Frame):
    def __init__(self, username=None, user_id=None, friend_id=None):
        super().__init__(None, title="文件传输", size=(520, 420))
        try:
            icon = wx.Icon(os.path.join(os.path.dirname(__file__), 'app.ico'))
            self.SetIcon(icon)
        except Exception:
            pass

        self.username = username
        self.user_id = user_id
        self.friend_id = friend_id

        # 服务器
        self.FILE_HOST = 'localhost'
        self.FILE_PORT = 8893

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # 选择文件
        pick_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.path_input = wx.TextCtrl(panel, size=(320, -1))
        pick_btn = wx.Button(panel, label="选择文件", size=(90, 30))
        pick_btn.Bind(wx.EVT_BUTTON, self.on_pick_file)
        upload_btn = wx.Button(panel, label="上传", size=(90, 30))
        upload_btn.Bind(wx.EVT_BUTTON, self.on_upload)
        pick_sizer.Add(self.path_input, 1, wx.ALL | wx.EXPAND, 5)
        pick_sizer.Add(pick_btn, 0, wx.ALL, 5)
        pick_sizer.Add(upload_btn, 0, wx.ALL, 5)

        # 文件列表
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, "文件名", width=240)
        self.list_ctrl.InsertColumn(1, "大小(B)", width=100)
        self.list_ctrl.InsertColumn(2, "时间", width=150)

        list_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        refresh_btn = wx.Button(panel, label="刷新列表", size=(100, 30))
        refresh_btn.Bind(wx.EVT_BUTTON, self.on_refresh)
        download_btn = wx.Button(panel, label="下载选中", size=(100, 30))
        download_btn.Bind(wx.EVT_BUTTON, self.on_download)
        list_btn_sizer.Add(refresh_btn, 0, wx.ALL, 5)
        list_btn_sizer.Add(download_btn, 0, wx.ALL, 5)

        sizer.Add(pick_sizer, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.list_ctrl, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(list_btn_sizer, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(sizer)

        # 初始拉取
        self.on_refresh(None)

    def on_pick_file(self, event):
        with wx.FileDialog(self, "选择文件", wildcard="*.*",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            pathname = fileDialog.GetPath()
            self.path_input.SetValue(pathname)

    def on_upload(self, event):
        path = self.path_input.GetValue().strip()
        if not path or not self.user_id or not self.friend_id:
            wx.MessageBox("请选择文件且确保用户/好友ID存在", "错误", wx.OK | wx.ICON_ERROR)
            return

        def worker():
            try:
                filesize = 0
                filename = path.split('\\')[-1]
                # 先发送 JSON 头，声明流式上传
                head = {
                    'action': 'upload_stream',
                    'user_id': self.user_id,
                    'friend_id': self.friend_id,
                    'filename': filename,
                    'size': os.path.getsize(path)
                }
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(60.0)  # 设置60秒超时
                client_socket.connect((self.FILE_HOST, self.FILE_PORT))
                client_socket.send(json.dumps(head, ensure_ascii=False).encode('utf-8'))
                
                # 等待服务端确认继续
                cont_data = b''
                while True:
                    try:
                        chunk = client_socket.recv(1024)
                        if not chunk:
                            break
                        cont_data += chunk
                        try:
                            cont = json.loads(cont_data.decode('utf-8'))
                            break
                        except json.JSONDecodeError:
                            continue
                    except socket.timeout:
                        wx.CallAfter(wx.MessageBox, "服务器响应超时", "错误", wx.OK | wx.ICON_ERROR)
                        client_socket.close()
                        return
                
                if cont.get('status') != 'continue':
                    client_socket.close()
                    wx.CallAfter(wx.MessageBox, "握手失败", "错误", wx.OK | wx.ICON_ERROR)
                    return
                
                # 流式发送原始字节
                with open(path, 'rb') as f:
                    while True:
                        chunk = f.read(1024*1024)  # 增加块大小
                        if not chunk:
                            break
                        try:
                            client_socket.sendall(chunk)
                            filesize += len(chunk)
                        except socket.timeout:
                            wx.CallAfter(wx.MessageBox, "上传超时", "错误", wx.OK | wx.ICON_ERROR)
                            client_socket.close()
                            return
                
                # 接收最终响应
                resp_data = b''
                while True:
                    try:
                        chunk = client_socket.recv(4096)
                        if not chunk:
                            break
                        resp_data += chunk
                        try:
                            resp = json.loads(resp_data.decode('utf-8'))
                            break
                        except json.JSONDecodeError:
                            continue
                    except socket.timeout:
                        wx.CallAfter(wx.MessageBox, "接收响应超时", "错误", wx.OK | wx.ICON_ERROR)
                        client_socket.close()
                        return
                
                client_socket.close()
                if resp.get('status') == 'success':
                    wx.CallAfter(wx.MessageBox, "上传成功", "提示", wx.OK | wx.ICON_INFORMATION)
                    wx.CallAfter(self.on_refresh, None)
                else:
                    wx.CallAfter(wx.MessageBox, f"上传失败：{resp.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"上传失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)

        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()

    def on_refresh(self, event):
        if not self.user_id or not self.friend_id:
            return

        def worker():
            try:
                req = {
                    'action': 'list',
                    'user_id': self.user_id,
                    'friend_id': self.friend_id,
                    'limit': 50
                }
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.FILE_HOST, self.FILE_PORT))
                client_socket.send(json.dumps(req, ensure_ascii=False).encode('utf-8'))
                resp = json.loads(client_socket.recv(8192).decode('utf-8'))
                client_socket.close()
                if resp.get('status') == 'success':
                    files = resp.get('files', [])
                    def apply():
                        self.list_ctrl.DeleteAllItems()
                        for row in files:
                            idx = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), row.get('filename',''))
                            self.list_ctrl.SetItem(idx, 1, str(row.get('size', 0)))
                            self.list_ctrl.SetItem(idx, 2, row.get('created_at',''))
                            self.list_ctrl.SetItemData(idx, int(row.get('id', 0)))
                    wx.CallAfter(apply)
                else:
                    wx.CallAfter(wx.MessageBox, f"获取列表失败：{resp.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"获取列表失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)

        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()

    def on_download(self, event):
        idx = self.list_ctrl.GetFirstSelected()
        if idx == -1:
            wx.MessageBox("请先选择一个文件", "提示", wx.OK | wx.ICON_INFORMATION)
            return
        file_id = self.list_ctrl.GetItemData(idx)

        def worker():
            try:
                # 流式下载：先收 JSON 头再收原始字节
                req = {'action': 'download_stream', 'file_id': int(file_id)}
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.settimeout(60.0)  # 设置60秒超时
                client_socket.connect((self.FILE_HOST, self.FILE_PORT))
                client_socket.send(json.dumps(req, ensure_ascii=False).encode('utf-8'))
                
                # 接收JSON头
                header_data = b''
                while True:
                    try:
                        chunk = client_socket.recv(4096)
                        if not chunk:
                            break
                        header_data += chunk
                        try:
                            header = json.loads(header_data.decode('utf-8'))
                            break
                        except json.JSONDecodeError:
                            continue
                    except socket.timeout:
                        wx.CallAfter(wx.MessageBox, "接收文件信息超时", "错误", wx.OK | wx.ICON_ERROR)
                        client_socket.close()
                        return
                
                if header.get('status') != 'success':
                    client_socket.close()
                    wx.CallAfter(wx.MessageBox, f"下载失败：{header.get('message')}", "错误", wx.OK | wx.ICON_ERROR)
                    return
                
                filename = header.get('filename', 'download.bin')
                total = int(header.get('size', 0))
                
                with wx.FileDialog(self, "保存文件", wildcard="*.*",
                                   style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                                   defaultFile=filename) as fileDialog:
                    if fileDialog.ShowModal() == wx.ID_CANCEL:
                        client_socket.close()
                        return
                    save_path = fileDialog.GetPath()
                
                received = 0
                retry_count = 0
                max_retries = 5  # 增加重试次数
                consecutive_empty = 0  # 连续空数据计数
                
                with open(save_path, 'wb') as f:
                    while received < total:
                        try:
                            chunk_size = min(1024*1024, total - received)  # 1MB块大小
                            chunk = client_socket.recv(chunk_size)
                            
                            if not chunk:
                                consecutive_empty += 1
                                if consecutive_empty >= 3:  # 连续3次空数据
                                    retry_count += 1
                                    if retry_count >= max_retries:
                                        break
                                    wx.CallAfter(wx.MessageBox, f"网络连接中断，正在重试 ({retry_count}/{max_retries})", "重试中", wx.OK | wx.ICON_INFORMATION)
                                    time.sleep(2)  # 等待2秒后重试
                                    consecutive_empty = 0
                                    continue
                                else:
                                    time.sleep(0.1)  # 短暂等待
                                    continue
                            
                            f.write(chunk)
                            received += len(chunk)
                            retry_count = 0  # 重置重试计数
                            consecutive_empty = 0  # 重置空数据计数
                            
                            # 显示下载进度（每10%显示一次）
                            progress = (received / total) * 100
                            if int(progress) % 10 == 0 and int(progress) > 0:
                                wx.CallAfter(wx.MessageBox, f"下载进度：{int(progress)}% ({received}/{total} 字节)", "下载中", wx.OK | wx.ICON_INFORMATION)
                                
                        except socket.timeout:
                            retry_count += 1
                            if retry_count >= max_retries:
                                break
                            wx.CallAfter(wx.MessageBox, f"接收超时，正在重试 ({retry_count}/{max_retries})", "重试中", wx.OK | wx.ICON_INFORMATION)
                            time.sleep(2)  # 等待2秒后重试
                            continue
                        except Exception as e:
                            wx.CallAfter(wx.MessageBox, f"下载过程中出错：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)
                            break
                
                client_socket.close()
                
                if received == total:
                    wx.CallAfter(wx.MessageBox, f"下载完成！文件大小：{received} 字节", "成功", wx.OK | wx.ICON_INFORMATION)
                else:
                    wx.CallAfter(wx.MessageBox, f"下载中断！已下载：{received}/{total} 字节", "错误", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.CallAfter(wx.MessageBox, f"下载失败：{str(e)}", "错误", wx.OK | wx.ICON_ERROR)

        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()


class FileApp(wx.App):
    def OnInit(self):
        frame = FileTransferFrame()
        frame.Show()
        return True


if __name__ == '__main__':
    app = FileApp()
    app.MainLoop()


