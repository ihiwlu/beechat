import smtplib
import random
import string
import re
import time
import threading
import socket
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formatdate
from code_insert_into_table import EmailVerificationDB
from config import VERIFICATION_DB_CONFIG

class EmailVerifier:
    """邮件验证码发送类"""
    def __init__(self, db_config):
        # 配置邮件服务器信息（使用163邮箱）
        # 
        # 163邮箱SMTP配置说明：
        # 1. 登录163邮箱，进入"设置" -> "POP3/SMTP/IMAP"
        # 2. 开启"IMAP/SMTP服务"
        # 3. 通过手机短信获取授权码
        # 4. 将sender_email替换为您的163邮箱地址
        # 5. 将sender_password替换为获取到的授权码（不是登录密码）
        #
        # 常用端口：
        # - 端口25: 普通SMTP端口
        # - 端口465: SSL加密端口
        # - 端口994: TLS加密端口
        self.config = {
            "smtp_server": "smtp.163.com",  # 163邮箱SMTP服务器
            "smtp_port": 25,                # 163邮箱SMTP端口（也可使用465或994）
            "sender_email": "18963442649@163.com",  # 请替换为您的163邮箱地址
            "sender_password": "CRp2g7TNKa64yiWZ",  # 请替换为您的163邮箱授权码（不是密码）
            "sender_name": "BeeChat",
            "timeout": 30,                  # 增加超时时间到30秒
            "retry_count": 3                # 增加重试次数到3次
        }
        
        # 初始化数据库连接
        self.db = EmailVerificationDB(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 3306),
            user=db_config.get("user", "root"),
            password=db_config.get("password", "abc123"),
            db_name=db_config.get("db_name", "test")
        )
        self.db.clean_expired_codes()

    def _generate_auth_code(self, length=5):
        """生成指定长度的验证码"""
        possible_chars = string.digits
        return ''.join(random.choice(possible_chars) for _ in range(length))

    def _is_valid_email(self, email):
        """验证邮箱格式是否正确"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "邮箱格式不正确"

        # 邮箱格式正确即可，不检查是否已注册
        # 因为验证码发送可能用于注册（邮箱未注册）或忘记密码（邮箱已注册）
        return True, ""

    def _can_send(self, email):
        """检查是否可以发送（防频繁发送）"""
        try:
            # 检查发送频率，使用已有的数据库连接
            with self.db._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                    SELECT id FROM email_verification
                    WHERE email = %s
                      AND created_at >= NOW() - INTERVAL 10 SECOND
                      AND expires_at > NOW()
                    LIMIT 1
                    """, (email,))
                    if cursor.fetchone():
                        return False, "10秒内只能发送一次验证码"
            return True, ""
        except Exception as e:
            return False, f"检查发送频率失败: {str(e)}"

    def send_verification_code(self, recipient_email, valid_minutes=5):
            """发送验证码到指定邮箱，修复SMTP认证问题"""
            print(f"开始处理发送验证码请求: {recipient_email}")
            
            # 1. 验证邮箱格式
            valid, msg = self._is_valid_email(recipient_email)
            if not valid:
                print(f"邮箱验证失败: {msg}")
                return False, msg, None

            # 2. 检查发送频率
            can_send, msg = self._can_send(recipient_email)
            if not can_send:
                print(f"发送频率检查失败: {msg}")
                return False, msg, None

            # 3. 生成验证码
            auth_code = self._generate_auth_code()
            print(f"生成验证码: {auth_code} 有效期: {valid_minutes}分钟")

            # 4. 构建邮件内容
            subject = f"BeeChat验证码:{auth_code}"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body>
                <h2>尊敬的用户：</h2>
                <p>您的验证码是：<strong style="font-size: 20px; color: #ff4500;">{auth_code}</strong></p>
                <p>该验证码有效期为 {valid_minutes} 分钟，请在有效期内使用。</p>
                <p>如果您没有进行相关操作，请忽略此邮件。</p>
            </body>
            </html>
            """

            # 5. 创建邮件
            try:
                email_msg = MIMEText(html_content, 'html', 'utf-8')
                email_msg['Subject'] = Header(subject, 'utf-8')
                email_msg['From'] = f"{Header(self.config['sender_name'], 'utf-8')} <{self.config['sender_email']}>"
                email_msg['To'] = Header(recipient_email, 'utf-8')
                email_msg['Date'] = formatdate(localtime=True)
            except Exception as e:
                return False, f"邮件构建失败：{str(e)}", None

            # 6. 发送邮件（修复SMTP认证问题）
            last_error = ""
            # 尝试不同的端口组合
            ports_to_try = [self.config['smtp_port'], 587, 465, 25]
            
            for port in ports_to_try:
                for attempt in range(self.config["retry_count"] + 1):
                    try:
                        print(f"尝试连接SMTP服务器 {self.config['smtp_server']}:{port} (尝试 {attempt + 1}/{self.config['retry_count'] + 1})")
                        
                        # 根据端口选择合适的连接方式
                        if port == 465:
                            # 465端口使用SSL直接连接
                            print(f"使用SMTP_SSL连接端口 {port}")
                            server = smtplib.SMTP_SSL(
                                self.config['smtp_server'], 
                                port,
                                timeout=self.config["timeout"]
                            )
                        else:
                            # 其他端口使用普通SMTP连接
                            print(f"使用SMTP连接端口 {port}")
                            server = smtplib.SMTP(
                                self.config['smtp_server'], 
                                port,
                                timeout=self.config["timeout"]
                            )

                        # 启用调试模式（开发环境可选）
                        # server.set_debuglevel(1)
                        
                        # 获取服务器信息
                        print(f"SMTP服务器信息: {server.ehlo_resp if hasattr(server, 'ehlo_resp') else 'N/A'}")
                        
                        # 发送EHLO命令标识客户端身份（比HELO更现代）
                        ehlo_code, ehlo_msg = server.ehlo()
                        print(f"EHLO响应: {ehlo_code} {ehlo_msg.decode() if isinstance(ehlo_msg, bytes) else ehlo_msg}")
                        
                        # 对于非SSL端口，尝试启用TLS
                        if port != 465:
                            if server.has_extn('starttls'):
                                print(f"端口 {port} 支持STARTTLS，正在启用...")
                                server.starttls()
                                # TLS连接后需要重新EHLO
                                tls_ehlo_code, tls_ehlo_msg = server.ehlo()
                                print(f"TLS后EHLO响应: {tls_ehlo_code} {tls_ehlo_msg.decode() if isinstance(tls_ehlo_msg, bytes) else tls_ehlo_msg}")
                            else:
                                print(f"端口 {port} 不支持STARTTLS")

                        # 检查服务器是否支持认证
                        if server.has_extn('auth'):
                            print(f"端口 {port} 支持认证")
                        else:
                            print(f"警告: 端口 {port} 不支持认证，但仍尝试登录...")
                        
                        # 登录邮箱
                        print(f"正在使用账号 {self.config['sender_email']} 登录...")
                        server.login(self.config['sender_email'], self.config['sender_password'])
                        print("邮箱登录成功")
                        
                        # 发送邮件
                        print(f"正在发送邮件到 {recipient_email}...")
                        # 修复 'bytes' object has no attribute 'as_string' 错误
                        if isinstance(email_msg, bytes):
                            msg_content = email_msg
                        else:
                            msg_content = email_msg.as_string().encode('utf-8')
                            
                        server.sendmail(
                            self.config['sender_email'], 
                            recipient_email, 
                            msg_content
                        )
                        print("邮件发送成功")
                        
                        # 关闭连接
                        server.quit()
                        print("SMTP连接已关闭")

                        # 发送成功，保存到数据库
                        if self.db.save_verification_code(recipient_email, auth_code, valid_minutes):
                            print(f"验证码已发送并保存: {recipient_email}")
                            return True, f"验证码已发送至 {recipient_email}", auth_code
                        else:
                            return False, "验证码发送成功，但保存到数据库失败", auth_code

                    except smtplib.SMTPServerDisconnected as e:
                        last_error = f"连接被服务器断开: {str(e)}"
                        print(f"端口 {port} 尝试 {attempt + 1} 失败: {last_error}")
                    except smtplib.SMTPAuthenticationError as e:
                        last_error = f"邮箱认证失败，请检查账号和授权码: {str(e)}"
                        print(f"端口 {port} 认证失败: {last_error}")
                        # 认证失败时记录详细信息
                        print(f"认证失败详情 - 账号: {self.config['sender_email']}, 密码长度: {len(self.config['sender_password'])}")
                        break  # 认证失败不需要重试同一端口
                    except smtplib.SMTPRecipientsRefused as e:
                        last_error = f"收件人被拒绝: {str(e)}"
                        print(f"端口 {port} 发送失败: {last_error}")
                        break  # 收件人问题不需要重试
                    except smtplib.SMTPException as e:
                        last_error = f"SMTP错误: {str(e)}"
                        print(f"端口 {port} SMTP错误: {last_error}")
                    except Exception as e:
                        last_error = f"发送失败：{str(e)}"
                        print(f"端口 {port} 尝试 {attempt + 1} 失败: {last_error}")
                        # 打印异常的详细信息
                        import traceback
                        print(f"详细错误信息: {traceback.format_exc()}")

                    # 重试判断
                    if attempt < self.config["retry_count"]:
                        print(f"等待1秒后重试...")
                        time.sleep(1)
                        continue
                    else:
                        break  # 该端口所有尝试都失败，换端口

            return False, last_error, None




class VerificationServer:
    """验证码服务端，处理客户端的验证码请求"""
    def __init__(self, host='localhost', port=12123, db_config=None, cleanup_interval=30):
        self.host = host
        self.port = port
        # 初始化数据库配置，默认使用本地数据库
        self.db_config = db_config or {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "abc123",
            "db_name": "test"
        }
        self.email_verifier = EmailVerifier(self.db_config)
        self.running = False
        self.cleanup_interval = cleanup_interval  # 清理间隔时间（秒）
        self.cleanup_thread = None  # 定时清理线程
        print(f"验证码服务初始化完成，监听地址: {self.host}:{self.port}")

    def start_cleanup_thread(self):
        """启动定时清理线程"""
        def cleanup_task():
            """定时清理过期验证码的任务"""
            while self.running:
                try:
                    # 执行清理操作
                    self.email_verifier.db.clean_expired_codes()
                    # 等待指定间隔时间
                    time.sleep(self.cleanup_interval)
                except Exception as e:
                    print(f"定时清理任务出错: {str(e)}")
                    # 出错后等待一段时间再重试
                    time.sleep(5)
        
        # 创建并启动清理线程
        self.cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
        self.cleanup_thread.start()

    def start(self):
        """启动服务端"""
        self.running = True
        # 启动定时清理线程
        self.start_cleanup_thread()
        
        # 创建一个可重用的socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置SO_REUSEADDR选项，允许端口重用
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"验证码服务已启动，监听 {self.host}:{self.port}")
            print(f"将每 {self.cleanup_interval} 秒自动清理过期验证码")
        except Exception as e:
            print(f"验证码服务启动失败: {str(e)}")
            print("请检查以下几点:")
            print("1. 端口是否被其他程序占用")
            print("2. 是否有足够的权限绑定该端口")
            print("3. 网络配置是否正确")
            self.running = False
            return
            
        while self.running:
            try:
                conn, addr = s.accept()
                print(f"连接来自 {addr}")
                # 为每个连接创建一个新线程处理
                client_handler = threading.Thread(target=self.handle_client, args=(conn,))
                client_handler.start()
            except Exception as e:
                if self.running:  # 如果不是主动停止服务，才显示错误
                    print(f"接受连接时出错: {str(e)}")
                    
        # 关闭socket
        try:
            s.close()
            print("验证码服务socket已关闭")
        except:
            pass

    def stop(self):
        """停止服务端"""
        self.running = False
        # 等待清理线程结束
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        # 关闭数据库连接
        self.email_verifier.db.close_connection()
        print("验证码服务已停止")

    def handle_client(self, conn):
        """处理客户端请求"""
        client_addr = None
        # 使用try-finally确保连接正确关闭
        try:
            # 获取客户端地址信息
            client_addr = conn.getpeername()
            print(f"[DEBUG] 处理来自 {client_addr} 的客户端请求")
            
            # 设置连接超时时间
            conn.settimeout(10.0)
            
            # 接收客户端请求
            data = conn.recv(1024).decode('utf-8')
            print(f"[DEBUG] 收到数据: {data}")
            
            if not data:
                print("[DEBUG] 收到空数据，关闭连接")
                return
                
            # 解析请求：命令|参数
            parts = data.split('|')
            command = parts[0]
            print(f"[DEBUG] 解析命令: {command}")
            
            # 处理测试请求
            if command == "TEST":
                print("[DEBUG] 处理TEST命令")
                response = "SUCCESS|验证码服务正常运行"
                if conn.fileno() != -1:
                    conn.sendall(response.encode('utf-8'))
                    print(f"[DEBUG] 发送响应: {response}")
                return
                
            if len(parts) < 2:
                response = "ERROR|无效的请求格式"
                conn.sendall(response.encode('utf-8'))
                print(f"[DEBUG] 发送错误响应: {response}")
                return
                
            if command == "SEND":
                email = parts[1]
                print(f"[DEBUG] 处理SEND命令，目标邮箱: {email}")
                # 发送验证码
                success, message, code = self.email_verifier.send_verification_code(email)
                print(f"[DEBUG] 验证码发送结果: success={success}, message={message}")
                
                # 构建响应：状态|消息|验证码(成功时)
                if success:
                    response = f"SUCCESS|{message}|{code}"
                else:
                    response = f"ERROR|{message}"
                    
                # 发送响应前检查连接是否仍然有效
                if conn.fileno() != -1:  # 检查套接字是否仍然打开
                    conn.sendall(response.encode('utf-8'))
                    print(f"[DEBUG] 发送响应: {response}")
            elif command == "VERIFY":
                # 处理验证码验证请求
                if len(parts) < 3:
                    response = "ERROR|验证请求格式错误，应为VERIFY|email|code"
                    conn.sendall(response.encode('utf-8'))
                    print(f"[DEBUG] 发送错误响应: {response}")
                    return
                
                email = parts[1]
                code = parts[2]
                print(f"[DEBUG] 处理VERIFY命令，邮箱: {email}, 验证码: {code}")
                # 验证验证码
                is_valid = self.email_verifier.db.verify_code(email, code)
                print(f"[DEBUG] 验证结果: {is_valid}")
                
                if is_valid:
                    response = "SUCCESS|验证码验证通过"
                else:
                    response = "ERROR|验证码无效或已过期"
                    
                if conn.fileno() != -1:
                    conn.sendall(response.encode('utf-8'))
                    print(f"[DEBUG] 发送响应: {response}")
            else:
                response = "ERROR|未知命令"
                if conn.fileno() != -1:
                    conn.sendall(response.encode('utf-8'))
                    print(f"[DEBUG] 发送错误响应: {response}")
                
        except socket.timeout:
            error_msg = f"客户端 {client_addr} 连接超时"
            print(f"[ERROR] {error_msg}")
        except Exception as e:
            error_msg = f"处理客户端 {client_addr} 请求时出错: {str(e)}"
            print(f"[ERROR] {error_msg}")
            # 尝试发送错误响应，但先检查连接状态
            try:
                if conn.fileno() != -1:  # 检查套接字是否仍然打开
                    response = f"ERROR|{error_msg}"
                    conn.sendall(response.encode('utf-8'))
                    print(f"[DEBUG] 发送错误响应: {response}")
            except:
                pass  # 如果发送也失败，就忽略
        finally:
            try:
                conn.close()  # 确保关闭连接
                print(f"[DEBUG] 关闭与 {client_addr} 的连接")
            except:
                pass

if __name__ == "__main__":
    try:
        # 可以通过cleanup_interval参数调整清理间隔时间（秒）
        server = VerificationServer(db_config=VERIFICATION_DB_CONFIG, cleanup_interval=120)
        server.start()
    except KeyboardInterrupt:
        server.stop()
    