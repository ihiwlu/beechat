import socket
import threading
import pymysql
import json
import traceback
import sys
import os
from config import DB_CONFIG, VERIFICATION_DB_CONFIG, SERVER_HOST, SERVER_PORTS

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入验证码验证模块
from server.code_insert_into_table import EmailVerificationDB

# 服务器配置
SERVER_PORT = SERVER_PORTS['register']

class RegisterServer:
    def __init__(self):
        self.server_socket = None
        self.running = False
        self.verification_db = EmailVerificationDB(**VERIFICATION_DB_CONFIG)
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
                email VARCHAR(100) NOT NULL UNIQUE,
                nickname VARCHAR(50) DEFAULT '',
                status VARCHAR(20) DEFAULT 'offline',
                avatar VARCHAR(255) DEFAULT ''
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_table_sql)
            print("数据表 'user' 已创建或已存在")
            
            # 创建user_info表（如果不存在），用于存储用户详细信息
            create_user_info_table_sql = """
            CREATE TABLE IF NOT EXISTS user_info (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_user_info_table_sql)
            print("数据表 'user_info' 已创建或已存在")
            
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
                
                # 插入user_info表的测试数据
                cursor.execute("SELECT id, email FROM user")
                users = cursor.fetchall()
                user_info_data = [(user[0], user[1]) for user in users]
                cursor.executemany(
                    "INSERT INTO user_info (user_id, email) VALUES (%s, %s)",
                    user_info_data
                )
                print("已插入用户信息测试数据")
            
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
            
    def check_user_exists(self, username, email):
        """检查用户名或邮箱是否已存在"""
        connection = self.connect_to_database()
        if not connection:
            return True  # 连接失败时默认已存在
            
        try:
            cursor = connection.cursor()
            
            # 检查用户名是否已存在
            sql = "SELECT COUNT(*) FROM user WHERE username = %s OR email = %s"
            cursor.execute(sql, (username, email))
            count = cursor.fetchone()[0]
            
            cursor.close()
            connection.close()
            
            # 如果count > 0，说明用户名或邮箱已存在
            return count > 0
        except Exception as e:
            print(f"数据库查询出错: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return True  # 出错时默认已存在
            
    def register_user(self, username, password, email):
        """注册新用户"""
        connection = self.connect_to_database()
        if not connection:
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            
            # 插入新用户
            sql = "INSERT INTO user (username, password, email, nickname, status, avatar) VALUES (%s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, (username, password, email, username, 'offline', ''))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return True, "注册成功"
        except pymysql.IntegrityError as e:
            if connection:
                connection.close()
            if "username" in str(e):
                return False, "用户名已存在"
            elif "email" in str(e):
                return False, "邮箱已存在"
            else:
                return False, "注册失败：数据冲突"
        except Exception as e:
            print(f"数据库插入出错: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return False, "注册失败：服务器内部错误"
            
    def verify_captcha(self, email, captcha):
        """验证验证码"""
        try:
            # 使用验证码数据库对象验证验证码
            is_valid = self.verification_db.verify_code(email, captcha)
            return is_valid
        except Exception as e:
            print(f"验证码验证出错: {e}")
            traceback.print_exc()
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
                    register_data = json.loads(data)
                    username = register_data.get('username')
                    password = register_data.get('password')
                    email = register_data.get('email')
                    captcha = register_data.get('captcha')  # 获取验证码
                    
                    # 验证数据完整性
                    if not username or not password or not email or not captcha:
                        response = {
                            'status': 'error',
                            'message': '用户名、密码、邮箱和验证码不能为空'
                        }
                    else:
                        # 验证验证码
                        if not self.verify_captcha(email, captcha):
                            response = {
                                'status': 'error',
                                'message': '验证码错误或已过期'
                            }
                        else:
                            # 检查用户名或邮箱是否已存在
                            if self.check_user_exists(username, email):
                                response = {
                                    'status': 'error',
                                    'message': '用户名或邮箱已存在'
                                }
                            else:
                                # 注册新用户
                                success, message = self.register_user(username, password, email)
                                if success:
                                    response = {
                                        'status': 'success',
                                        'message': message,
                                        'username': username
                                    }
                                else:
                                    response = {
                                        'status': 'error',
                                        'message': message
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
            
            print(f"注册服务器启动成功，监听地址: {SERVER_HOST}:{SERVER_PORT}")
            
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
        # 关闭验证码数据库连接
        if self.verification_db:
            self.verification_db.close_connection()
        print("注册服务器已停止")

def main():
    """主函数"""
    server = RegisterServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.stop_server()

if __name__ == '__main__':
    main()