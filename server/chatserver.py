import socket
import threading
import json
import time
import pymysql
import traceback
from config import DB_CONFIG, SERVER_HOST, SERVER_PORTS

# 服务器配置
SERVER_PORT = SERVER_PORTS['chat']

class ChatServer:
    def __init__(self):
        self.server_socket = None
        self.clients = {}  # 存储客户端连接和信息
        # 不再使用聊天室/房间
        self.running = False
        # 使用集中配置的数据库配置
        self.DB_CONFIG = DB_CONFIG

    def connect_to_database(self):
        """连接到数据库（仅用于初始化表）"""
        try:
            connection = pymysql.connect(
                host=self.DB_CONFIG['host'],
                user=self.DB_CONFIG['user'],
                password=self.DB_CONFIG['password'],
                database='test',
                port=self.DB_CONFIG['port'],
                charset=self.DB_CONFIG['charset'],
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except Exception as e:
            print(f"聊天服务器：数据库连接失败: {e}")
            traceback.print_exc()
            return None

    def ensure_chat_table_exists(self):
        """检查聊天记录表是否存在，不存在则创建（与离线消息持久化保持一致）"""
        connection = self.connect_to_database()
        if not connection:
            return False
        try:
            cursor = connection.cursor()
            create_chat_table_sql = """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT NOT NULL,
                receiver_id INT NOT NULL,
                message TEXT NOT NULL,
                message_type ENUM('text', 'image', 'file') DEFAULT 'text',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_sender_receiver (sender_id, receiver_id),
                INDEX idx_created_at (created_at)
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_chat_table_sql)
            connection.commit()
            cursor.close()
            connection.close()
            print("聊天服务器：chat_messages 表已确认存在")
            return True
        except Exception as e:
            print(f"聊天服务器：创建 chat_messages 表失败: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return False
        
    def broadcast_message(self, message, exclude_client=None):
        """广播消息给所有客户端（除了exclude_client）"""
        for client_socket, client_info in self.clients.items():
            if client_socket != exclude_client:
                try:
                    client_socket.send(json.dumps(message, ensure_ascii=False).encode('utf-8'))
                except:
                    # 如果发送失败，移除客户端
                    self.remove_client(client_socket)
                    
    def send_to_client(self, client_socket, message):
        """发送消息给特定客户端"""
        try:
            client_socket.send(json.dumps(message, ensure_ascii=False).encode('utf-8'))
        except:
            self.remove_client(client_socket)
            
    # 房间相关功能已移除
        
    def send_private_message(self, sender_socket, target_username, message_content):
        """发送私聊消息（若对方不在线，不报错；实时通道仅最佳努力）"""
        sender_info = self.clients[sender_socket]
        sender_name = sender_info['username']
        
        # 查找目标用户
        target_socket = None
        for client_socket, client_info in self.clients.items():
            if client_info['username'] == target_username:
                target_socket = client_socket
                break
                
        delivered = False
        if target_socket:
            try:
                # 发送给目标用户
                private_message = {
                    'type': 'private',
                    'from': sender_name,
                    'message': message_content,
                    'timestamp': time.time()
                }
                self.send_to_client(target_socket, private_message)
                delivered = True
            except Exception:
                delivered = False

        # 始终给发送者一个确认，说明实时是否送达
        confirm_message = {
            'type': 'private_confirm',
            'to': target_username,
            'message': message_content,
            'delivered': delivered,
            'timestamp': time.time()
        }
        self.send_to_client(sender_socket, confirm_message)
            
    def handle_client_message(self, client_socket, message_data):
        """处理客户端消息"""
        client_info = self.clients[client_socket]
        message_type = message_data.get('type')
        
        if message_type == 'chat':
            # 不再支持房间群聊，提示使用私聊
            error_message = {
                'type': 'error',
                'message': '房间功能已关闭，请使用私聊'
            }
            self.send_to_client(client_socket, error_message)
            
        elif message_type == 'private':
            # 私聊消息
            target_username = message_data.get('to')
            message_content = message_data.get('message')
            if target_username and message_content:
                self.send_private_message(client_socket, target_username, message_content)
            else:
                error_message = {
                    'type': 'error',
                    'message': '私聊消息格式错误'
                }
                self.send_to_client(client_socket, error_message)
        # 其余房间相关消息类型已移除
                
        else:
            # 未知消息类型
            error_message = {
                'type': 'error',
                'message': '未知消息类型'
            }
            self.send_to_client(client_socket, error_message)
            
    def remove_client(self, client_socket):
        """移除客户端"""
        if client_socket in self.clients:
            client_info = self.clients[client_socket]
            username = client_info['username']
            
            # 从客户端列表中移除
            del self.clients[client_socket]
            # 不再广播进入/离开消息
            
            # 关闭连接
            try:
                client_socket.close()
            except:
                pass
                
            print(f"客户端 {username} 已断开连接")
            
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        print(f"客户端 {address} 已连接")
        
        try:
            # 等待客户端发送登录信息
            login_data = client_socket.recv(1024).decode('utf-8')
            if not login_data:
                client_socket.close()
                return
                
            login_info = json.loads(login_data)
            username = login_info.get('username')
            
            if not username:
                error_message = {
                    'type': 'error',
                    'message': '登录信息错误'
                }
                client_socket.send(json.dumps(error_message, ensure_ascii=False).encode('utf-8'))
                client_socket.close()
                return
                
            # 检查用户名是否已存在
            for client_info in self.clients.values():
                if client_info['username'] == username:
                    error_message = {
                        'type': 'error',
                        'message': '用户名已存在'
                    }
                    client_socket.send(json.dumps(error_message, ensure_ascii=False).encode('utf-8'))
                    client_socket.close()
                    return
                    
            # 添加客户端到列表
            self.clients[client_socket] = {
                'username': username,
                'address': address,
                'room': None,
                'connected_at': time.time()
            }
            
            # 不再发送任何进入聊天室相关系统消息
            
            # 处理客户端消息循环
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                        
                    message_data = json.loads(data)
                    self.handle_client_message(client_socket, message_data)
                    
                except json.JSONDecodeError:
                    # 数据格式错误
                    continue
                except ConnectionResetError:
                    # 客户端强制断开连接
                    break
                except Exception as e:
                    print(f"处理客户端消息时出错: {e}")
                    break
                    
        except Exception as e:
            print(f"处理客户端 {address} 时出错: {e}")
        finally:
            self.remove_client(client_socket)
            
    def start_server(self):
        """启动服务器"""
        try:
            # 启动前确保聊天记录表存在（便于与离线消息数据库结构保持一致）
            self.ensure_chat_table_exists()
            # 创建socket对象
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置socket选项，允许地址重用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定地址和端口
            self.server_socket.bind((SERVER_HOST, SERVER_PORT))
            
            # 开始监听，最大连接数为20
            self.server_socket.listen(20)
            self.running = True
            
            print(f"聊天服务器启动成功，监听地址: {SERVER_HOST}:{SERVER_PORT}")
            
            while self.running:
                try:
                    # 接受客户端连接
                    client_socket, address = self.server_socket.accept()
                    
                    # 为每个客户端创建一个线程处理
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"接受客户端连接时出错: {e}")
                        
        except Exception as e:
            print(f"服务器启动失败: {e}")
        finally:
            self.stop_server()
            
    def stop_server(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            
        # 关闭所有客户端连接
        for client_socket in list(self.clients.keys()):
            try:
                client_socket.close()
            except:
                pass
                
        self.clients.clear()
        # 不再维护 rooms
        print("聊天服务器已停止")

def main():
    """主函数"""
    server = ChatServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.stop_server()

if __name__ == '__main__':
    main()