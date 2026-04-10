import socket
import threading
import pymysql
import json
import traceback
from config import DB_CONFIG, SERVER_HOST, SERVER_PORTS

# 服务器配置
SERVER_PORT = SERVER_PORTS['login']

class LoginServer:
    def __init__(self):
        self.server_socket = None
        self.running = False
        self.init_database()
        
    def init_database(self):
        """初始化数据库和数据表"""
        try:
            # 连接到MySQL服务器（不指定数据库）
            connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset']
            )
            
            cursor = connection.cursor()
            
            # 创建test数据库（如果不存在）
            cursor.execute("CREATE DATABASE IF NOT EXISTS test")
            print("数据库 'test' 已创建或已存在")
            
            # 选择test数据库
            cursor.execute("USE test")
            
            # 创建user表（如果不存在）
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(50) NOT NULL,
                email VARCHAR(100) NOT NULL,
                nickname VARCHAR(50) DEFAULT '',
                status VARCHAR(20) DEFAULT 'offline',
                avatar VARCHAR(255) DEFAULT ''
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_sql)
            print("数据表 'user' 已创建或已存在")
            
            # 插入一些测试数据（如果表为空）
            cursor.execute("SELECT COUNT(*) FROM user")
            count = cursor.fetchone()[0]
            if count == 0:
                test_users = [
                    ('admin', 'admin123', 'admin@example.com', '管理员', 'offline', ''),
                    ('user1', 'pass123', 'user1@example.com', '用户1', 'offline', ''),
                    ('test', 'test123', 'test@example.com', '测试用户', 'offline', '')
                ]
                cursor.executemany(
                    "INSERT INTO user (username, password, email, nickname, status, avatar) VALUES (%s, %s, %s, %s, %s, %s)",
                    test_users
                )
                print("已插入测试用户数据")
            
            connection.commit()
            cursor.close()
            connection.close()
            
        except Exception as e:
            print(f"数据库初始化失败: {e}")
            traceback.print_exc()
            
    def connect_to_database(self):
        """连接到数据库"""
        try:
            connection = pymysql.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database='test',
                port=DB_CONFIG['port'],
                charset=DB_CONFIG['charset']
            )
            return connection
        except Exception as e:
            print(f"数据库连接失败: {e}")
            return None
            
    def verify_user(self, username, password):
        """验证用户账号密码"""
        connection = self.connect_to_database()
        if not connection:
            return False
            
        try:
            cursor = connection.cursor()
            # 查询用户信息
            sql = "SELECT username, password FROM user WHERE username = %s AND password = %s"
            cursor.execute(sql, (username, password))
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            # 如果查询到结果，说明账号密码正确
            return result is not None
        except Exception as e:
            print(f"数据库查询出错: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return False
            
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        print(f"客户端 {address} 已连接")
        
        try:
            while True:
                # 接收客户端发送的数据
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                print(f"收到来自 {address} 的数据: {data}")
                
                try:
                    # 解析JSON数据
                    login_data = json.loads(data)
                    username = login_data.get('username')
                    password = login_data.get('password')
                    
                    if not username or not password:
                        response = {
                            'status': 'error',
                            'message': '用户名或密码不能为空'
                        }
                    else:
                        # 验证账号密码
                        is_valid = self.verify_user(username, password)
                        
                        if is_valid:
                            response = {
                                'status': 'success',
                                'message': '登录成功',
                                'username': username
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '用户名或密码错误'
                            }
                except json.JSONDecodeError:
                    response = {
                        'status': 'error',
                        'message': '数据格式错误'
                    }
                except Exception as e:
                    print(f"处理客户端数据时出错: {e}")
                    response = {
                        'status': 'error',
                        'message': '服务器内部错误'
                    }
                
                # 发送响应给客户端
                client_socket.send(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                
        except ConnectionResetError:
            print(f"客户端 {address} 强制断开连接")
        except Exception as e:
            print(f"处理客户端 {address} 时出错: {e}")
            traceback.print_exc()
        finally:
            client_socket.close()
            print(f"客户端 {address} 连接已关闭")
            
    def start_server(self):
        """启动服务器"""
        try:
            # 创建socket对象
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置socket选项，允许地址重用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定地址和端口
            self.server_socket.bind((SERVER_HOST, SERVER_PORT))
            
            # 开始监听，最大连接数为5
            self.server_socket.listen(5)
            self.running = True
            
            print(f"登录服务器启动成功，监听地址: {SERVER_HOST}:{SERVER_PORT}")
            
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
            traceback.print_exc()
        finally:
            self.stop_server()
            
    def stop_server(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("登录服务器已停止")

def main():
    """主函数"""
    server = LoginServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.stop_server()

if __name__ == '__main__':
    main()