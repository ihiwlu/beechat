import socket
import threading
import json
import os
import base64
import time
import pymysql
import traceback
import sys
from config import DB_CONFIG, SERVER_HOST, SERVER_PORTS, STORAGE_DIR

# 服务器配置
SERVER_PORT = SERVER_PORTS['file']


class FileServer:
    def __init__(self):
        self.server_socket = None
        self.running = False
        os.makedirs(STORAGE_DIR, exist_ok=True)

    def connect_to_database(self):
        try:
            connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database='test',
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset'],
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except Exception as e:
            print(f"文件服务器：数据库连接失败: {e}")
            traceback.print_exc()
            return None

    def ensure_tables(self):
        connection = self.connect_to_database()
        if not connection:
            return False
        try:
            cursor = connection.cursor()
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS chat_files (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT NOT NULL,
                receiver_id INT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                path VARCHAR(512) NOT NULL,
                size BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_sender_receiver (sender_id, receiver_id),
                INDEX idx_created_at (created_at)
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_sql)
            connection.commit()
            cursor.close()
            connection.close()
            print("文件服务器：chat_files 表已确认存在")
            return True
        except Exception as e:
            print(f"文件服务器：创建 chat_files 表失败: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return False

    def save_file_record(self, sender_id, receiver_id, filename, path, size):
        connection = self.connect_to_database()
        if not connection:
            return None
        try:
            cursor = connection.cursor()
            sql = """
            INSERT INTO chat_files (sender_id, receiver_id, filename, path, size)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (sender_id, receiver_id, filename, path, size))
            file_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            connection.close()
            return file_id
        except Exception as e:
            print(f"保存文件记录失败: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return None

    def list_files(self, user_id, friend_id, limit=50):
        connection = self.connect_to_database()
        if not connection:
            return []
        try:
            cursor = connection.cursor()
            sql = """
            SELECT id, sender_id, receiver_id, filename, size, created_at
            FROM chat_files
            WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
            ORDER BY created_at DESC
            LIMIT %s
            """
            cursor.execute(sql, (user_id, friend_id, friend_id, user_id, int(limit)))
            rows = cursor.fetchall()
            for r in rows:
                r['created_at'] = str(r['created_at'])
            cursor.close()
            connection.close()
            return rows
        except Exception as e:
            print(f"获取文件列表失败: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return []

    def get_file_path(self, file_id):
        connection = self.connect_to_database()
        if not connection:
            return None
        try:
            cursor = connection.cursor()
            sql = "SELECT id, filename, path FROM chat_files WHERE id = %s"
            cursor.execute(sql, (file_id,))
            row = cursor.fetchone()
            cursor.close()
            connection.close()
            return row
        except Exception as e:
            print(f"获取文件路径失败: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return None

    def handle_client(self, client_socket, address):
        print(f"文件服务器：客户端 {address} 已连接")
        try:
            # 聚合分片，直到能成功解析成一个完整 JSON
            client_socket.settimeout(60.0)  # 增加超时时间以支持大文件传输
            buffer = ''
            req = None
            while True:
                try:
                    chunk = client_socket.recv(8192)
                except socket.timeout:
                    chunk = b''
                if not chunk:
                    # 无新数据，尝试解析现有缓冲
                    if buffer:
                        try:
                            req = json.loads(buffer)
                            break
                        except json.JSONDecodeError:
                            # 继续等待下一轮
                            continue
                    else:
                        break
                buffer += chunk.decode('utf-8')
                try:
                    req = json.loads(buffer)
                    break
                except json.JSONDecodeError:
                    continue

            if req is None:
                resp = {'status': 'error', 'message': '空请求或解析失败'}
            else:
                try:
                    action = req.get('action')
                    if action == 'upload':
                        sender_id = int(req.get('user_id'))
                        friend_id = int(req.get('friend_id'))
                        filename = req.get('filename', 'file.bin')
                        file_b64 = req.get('data', '')
                        if not (sender_id and friend_id and file_b64):
                            resp = {'status': 'error', 'message': '参数错误'}
                        else:
                            raw = base64.b64decode(file_b64)
                            ts = int(time.time())
                            safe_name = f"{sender_id}_{friend_id}_{ts}_{os.path.basename(filename)}"
                            save_path = os.path.join(STORAGE_DIR, safe_name)
                            with open(save_path, 'wb') as f:
                                f.write(raw)
                            file_id = self.save_file_record(sender_id, friend_id, filename, save_path, len(raw))
                            resp = {'status': 'success', 'file_id': file_id}
                    elif action == 'upload_stream':
                        # 流式上传：JSON 头 + 原始字节流
                        sender_id = int(req.get('user_id'))
                        friend_id = int(req.get('friend_id'))
                        filename = req.get('filename', 'file.bin')
                        total_size = int(req.get('size', 0))
                        if not (sender_id and friend_id and total_size > 0):
                            resp = {'status': 'error', 'message': '参数错误'}
                        else:
                            ts = int(time.time())
                            safe_name = f"{sender_id}_{friend_id}_{ts}_{os.path.basename(filename)}"
                            save_path = os.path.join(STORAGE_DIR, safe_name)
                            received = 0
                            # 先回复一个确认，客户端随后发送原始字节
                            try:
                                client_socket.send(json.dumps({'status':'continue'}).encode('utf-8'))
                            except Exception:
                                resp = {'status': 'error', 'message': '握手失败'}
                                raise
                            with open(save_path, 'wb', buffering=1024*1024) as f:  # 增加缓冲区大小
                                while received < total_size:
                                    chunk = client_socket.recv(min(1024*1024, total_size - received))  # 增加块大小
                                    if not chunk:
                                        break
                                    f.write(chunk)
                                    received += len(chunk)
                            if received == total_size:
                                file_id = self.save_file_record(sender_id, friend_id, filename, save_path, total_size)
                                resp = {'status': 'success', 'file_id': file_id}
                            else:
                                # 接收不完整，删除临时文件
                                try:
                                    if os.path.exists(save_path):
                                        os.remove(save_path)
                                except Exception:
                                    pass
                                resp = {'status': 'error', 'message': '接收中断'}
                    elif action == 'list':
                        user_id = int(req.get('user_id'))
                        friend_id = int(req.get('friend_id'))
                        limit = int(req.get('limit', 50))
                        rows = self.list_files(user_id, friend_id, limit)
                        resp = {'status': 'success', 'files': rows}
                    elif action == 'download':
                        file_id = int(req.get('file_id'))
                        row = self.get_file_path(file_id)
                        if not row or not os.path.exists(row['path']):
                            resp = {'status': 'error', 'message': '文件不存在'}
                        else:
                            with open(row['path'], 'rb') as f:
                                raw = f.read()
                            data_b64 = base64.b64encode(raw).decode('utf-8')
                            resp = {'status': 'success', 'filename': row['filename'], 'data': data_b64}
                    elif action == 'download_stream':
                        # 流式下载：先发 JSON 头，再发原始字节
                        file_id = int(req.get('file_id'))
                        row = self.get_file_path(file_id)
                        if not row or not os.path.exists(row['path']):
                            resp = {'status': 'error', 'message': '文件不存在'}
                        else:
                            try:
                                size = os.path.getsize(row['path'])
                                header = {'status': 'success', 'filename': row['filename'], 'size': size}
                                client_socket.send(json.dumps(header, ensure_ascii=False).encode('utf-8'))
                                with open(row['path'], 'rb') as f:
                                    sent_bytes = 0
                                    while sent_bytes < size:
                                        chunk = f.read(1024*1024)  # 1MB块大小
                                        if not chunk:
                                            break
                                        try:
                                            client_socket.sendall(chunk)
                                            sent_bytes += len(chunk)
                                        except Exception as e:
                                            print(f"文件服务器：发送文件数据失败: {e}")
                                            break
                                # 流式下载结束后不再发送额外 JSON
                                resp = None
                            except Exception as e:
                                print(f"文件服务器：流式下载失败: {e}")
                                traceback.print_exc()
                                resp = {'status': 'error', 'message': '下载失败'}
                    else:
                        resp = {'status': 'error', 'message': '未知操作'}
                except Exception as e:
                    print(f"文件服务器：处理请求错误: {e}")
                    traceback.print_exc()
                    resp = {'status': 'error', 'message': '服务器内部错误'}

            if resp is not None:
                try:
                    client_socket.send(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
                except Exception:
                    pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
            print(f"文件服务器：客户端 {address} 连接已关闭")

    def start_server(self):
        if not self.ensure_tables():
            print("文件服务器：初始化表失败")
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((SERVER_HOST, SERVER_PORT))
            self.server_socket.listen(10)
            self.running = True
            print(f"文件服务器启动成功，监听地址: {SERVER_HOST}:{SERVER_PORT}")
            while self.running:
                client_socket, address = self.server_socket.accept()
                t = threading.Thread(target=self.handle_client, args=(client_socket, address))
                t.daemon = True
                t.start()
        except Exception as e:
            print(f"文件服务器：启动失败: {e}")
            traceback.print_exc()
        finally:
            self.stop_server()

    def stop_server(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        print("文件服务器已停止")


def main():
    server = FileServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭文件服务器...")
        server.stop_server()


if __name__ == '__main__':
    main()


