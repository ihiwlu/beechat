import socket
import threading
import pymysql
import json
import traceback
import sys
import os
from config import DB_CONFIG, SERVER_HOST, SERVER_PORTS, VERIFICATION_DB_CONFIG

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入验证码验证模块
from server.code_insert_into_table import EmailVerificationDB

# 服务器配置
SERVER_PORT = SERVER_PORTS['forgot']

class ForgotServer:
    def __init__(self):
        self.server_socket = None
        self.running = False
        self.verification_db = EmailVerificationDB(**VERIFICATION_DB_CONFIG)
        
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
            
    def check_email_exists(self, email):
        """检查邮箱是否存在"""
        connection = self.connect_to_database()
        if not connection:
            return False, None
            
        try:
            cursor = connection.cursor()
            # 查询邮箱是否存在
            sql = "SELECT id, username FROM user WHERE email = %s"
            cursor.execute(sql, (email,))
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            # 如果查询到结果，说明邮箱存在
            if result:
                return True, result[1]  # 返回用户名
            return False, None
        except Exception as e:
            print(f"数据库查询出错: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return False, None
            
    def send_verification_code(self, email):
        """发送验证码到指定邮箱（仅用于忘记密码）"""
        try:
            # 先检查邮箱是否已注册
            exists, username = self.check_email_exists(email)
            if not exists:
                return False, "该邮箱未注册", None
            
            # 创建EmailVerifier实例
            from server.mail_id import EmailVerifier
            email_verifier = EmailVerifier(VERIFICATION_DB_CONFIG)
            success, message, code = email_verifier.send_verification_code(email)
            return success, message, code
        except Exception as e:
            print(f"发送验证码失败: {e}")
            return False, f"发送验证码失败: {str(e)}", None
            
    def verify_code(self, email, code):
        """验证验证码"""
        try:
            return self.verification_db.verify_code(email, code)
        except Exception as e:
            print(f"验证验证码失败: {e}")
            return False
            
    def reset_password(self, email, new_password):
        """重置用户密码"""
        connection = self.connect_to_database()
        if not connection:
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            # 更新用户密码
            sql = "UPDATE user SET password = %s WHERE email = %s"
            cursor.execute(sql, (new_password, email))
            affected_rows = cursor.rowcount
            connection.commit()
            cursor.close()
            connection.close()
            
            if affected_rows > 0:
                return True, "密码重置成功"
            else:
                return False, "用户不存在"
        except Exception as e:
            print(f"重置密码失败: {e}")
            traceback.print_exc()
            if connection:
                connection.close()
            return False, f"重置密码失败: {str(e)}"
            
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        print(f"忘记密码服务器：客户端 {address} 已连接")
        
        try:
            while True:
                # 接收客户端发送的数据
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                print(f"收到来自 {address} 的数据: {data}")
                
                try:
                    # 解析JSON数据
                    forgot_data = json.loads(data)
                    action = forgot_data.get('action')
                    
                    if action == 'send_code':
                        # 发送验证码
                        email = forgot_data.get('email')
                        if not email:
                            response = {
                                'status': 'error',
                                'message': '邮箱不能为空'
                            }
                        else:
                            # 检查邮箱是否存在
                            exists, username = self.check_email_exists(email)
                            if exists:
                                # 发送验证码
                                success, message, code = self.send_verification_code(email)
                                if success:
                                    response = {
                                        'status': 'success',
                                        'message': f'验证码已发送到 {email}，请查收'
                                    }
                                else:
                                    response = {
                                        'status': 'error',
                                        'message': message
                                    }
                            else:
                                response = {
                                    'status': 'error',
                                    'message': '该邮箱未注册'
                                }
                    
                    elif action == 'reset_password':
                        # 重置密码
                        email = forgot_data.get('email')
                        code = forgot_data.get('code')
                        new_password = forgot_data.get('password')
                        
                        if not all([email, code, new_password]):
                            response = {
                                'status': 'error',
                                'message': '参数不完整'
                            }
                        else:
                            # 验证验证码
                            if self.verify_code(email, code):
                                # 重置密码
                                success, message = self.reset_password(email, new_password)
                                response = {
                                    'status': 'success' if success else 'error',
                                    'message': message
                                }
                            else:
                                response = {
                                    'status': 'error',
                                    'message': '验证码无效或已过期'
                                }
                    
                    else:
                        response = {
                            'status': 'error',
                            'message': '未知操作'
                        }
                        
                except json.JSONDecodeError:
                    response = {
                        'status': 'error',
                        'message': '数据格式错误'
                    }
                except Exception as e:
                    print(f"处理客户端数据时出错: {e}")
                    traceback.print_exc()
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
            
            print(f"忘记密码服务器启动成功，监听地址: {SERVER_HOST}:{SERVER_PORT}")
            
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
        print("忘记密码服务器已停止")

def main():
    """主函数"""
    server = ForgotServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server.stop_server()

if __name__ == '__main__':
    main()