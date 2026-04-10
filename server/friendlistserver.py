import socket
import threading
import pymysql
import json
import traceback
from config import DB_CONFIG, SERVER_HOST, SERVER_PORTS

# 服务器配置
SERVER_PORT = SERVER_PORTS['friendlist']

class FriendListServer:
    def __init__(self):
        self.server_socket = None
        self.running = False
        
    def connect_to_database(self):
        """连接到数据库"""
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
            print(f"数据库连接失败: {e}")
            traceback.print_exc()
            return None
            
    def check_table_names(self):
        """检查数据库中的表名"""
        connection = self.connect_to_database()
        if not connection:
            print("无法连接到数据库进行表名检查")
            return []
            
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            cursor.close()
            
            # 提取表名
            table_names = []
            for table in tables:
                if isinstance(table, dict):
                    # 如果是字典格式，尝试获取第一个值
                    table_names.append(list(table.values())[0])
                else:
                    # 如果是元组格式，获取第一个元素
                    table_names.append(table[0])
            
            return table_names
        except Exception as e:
            print(f"查询表名失败: {e}")
            traceback.print_exc()
            return []
        finally:
            if connection and connection.open:
                connection.close()
            
    def init_friends_table(self):
        """初始化好友表"""
        connection = self.connect_to_database()
        if not connection:
            return False
            
        try:
            cursor = connection.cursor()
            
            # 创建好友表
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS friends (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                friend_id INT NOT NULL,
                status ENUM('pending', 'accepted', 'rejected', 'blocked') DEFAULT 'pending',
                remark VARCHAR(255) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_friendship (user_id, friend_id)
                -- 暂时移除外键约束，确保在user表创建前也能初始化friends表
                -- FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
                -- FOREIGN KEY (friend_id) REFERENCES user(id) ON DELETE CASCADE
            )
            """
            cursor.execute(create_table_sql)
            
            # 创建好友备注表，每个用户独立维护对好友的备注
            create_remarks_table_sql = """
            CREATE TABLE IF NOT EXISTS friend_remarks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                friend_id INT NOT NULL,
                remark VARCHAR(255) DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY unique_user_friend_remark (user_id, friend_id)
            ) DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            cursor.execute(create_remarks_table_sql)
            
            # 创建聊天记录表（移除阅读状态依赖，不再使用已读逻辑）
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
            return True
        except Exception as e:
            print(f"创建好友表失败: {e}")
            if connection:
                connection.close()
            return False
            
    def get_user_id(self, username):
        """根据用户名获取用户ID"""
        print(f"开始查询用户名 '{username}' 的ID")
        connection = self.connect_to_database()
        if not connection:
            print("数据库连接失败")
            return None
            
        try:
            cursor = connection.cursor()
            print(f"执行SQL查询: SELECT id FROM user WHERE username = %s, 参数: ({username})")
            cursor.execute("SELECT id FROM user WHERE username = %s", (username,))
            result = cursor.fetchone()
            print(f"查询结果: {result}")
            cursor.close()
            connection.close()
            
            if result:
                # 由于使用了 DictCursor，结果为字典
                user_id = result['id']
                print(f"找到用户ID: {user_id}")
                return user_id
            print("未找到用户")
            return None
        except Exception as e:
            print(f"查询用户ID失败: {str(e)}")  # 打印具体错误信息
            traceback.print_exc()  # 输出完整堆栈信息
            if connection:
                connection.close()
            return None
            
    def get_friends(self, user_id):
        """获取用户的好友列表"""
        print(f"开始获取用户 {user_id} 的好友列表")
        connection = self.connect_to_database()
        if not connection:
            print("数据库连接失败")
            return []
            
        try:
            # 连接已设置 DictCursor，这里直接使用默认游标
            cursor = connection.cursor()
            print(f"数据库连接成功，用户ID: {user_id}")
            
            # 获取好友列表，包括发送和接收的已接受好友，并去重
            # 获取好友列表，包括发送和接收的已接受好友，并去重
            sql = """
            SELECT DISTINCT u.id as friend_id, u.username, 
                   COALESCE(f1.remark, '') as remark
            FROM (
                SELECT friend_id as uid FROM friends WHERE user_id = %s AND status = 'accepted'
                UNION
                SELECT user_id as uid FROM friends WHERE friend_id = %s AND status = 'accepted'
            ) f
            JOIN user u ON f.uid = u.id
            LEFT JOIN friends f1 ON f1.user_id = %s AND f1.friend_id = u.id AND f1.status = 'accepted'
            ORDER BY u.username
            """
            print(f"执行SQL查询: {sql.strip()}，参数: ({user_id}, {user_id}, {user_id})")
            cursor.execute(sql, (user_id, user_id, user_id))
            friends = cursor.fetchall()
            print(f"查询结果: {friends}")
            cursor.close()
            connection.close()
            print(f"成功获取到 {len(friends)} 个好友")
            return friends
                
        except Exception as e:
            print(f"获取好友列表失败: {str(e)}")  # 打印具体错误信息
            traceback.print_exc()  # 输出完整堆栈信息
            if connection:
                connection.close()
            return []
            
    def get_friend_requests(self, user_id):
        """获取好友请求列表"""
        print(f"开始获取用户 {user_id} 的好友请求列表")
        connection = self.connect_to_database()
        if not connection:
            print("数据库连接失败")
            return []
            
        try:
            # 连接已设置 DictCursor，这里直接使用默认游标
            cursor = connection.cursor()
            print(f"数据库连接成功，用户ID: {user_id}")
            
            # 查询发送给用户的好友请求
            sql = """
            SELECT f.id, u.id as requester_id, u.username as requester_name, 
                   u.email as requester_email, f.created_at, f.status
            FROM friends f
            JOIN user u ON (f.user_id = u.id)
            WHERE f.friend_id = %s AND f.status = 'pending'
            ORDER BY f.created_at DESC
            """
            print(f"执行SQL查询: {sql.strip()}，参数: ({user_id})")
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            print(f"查询结果: {results}")
            cursor.close()
            connection.close()
            
            # 格式化好友请求列表
            requests = []
            for row in results:
                requests.append({
                    'id': row['id'],
                    'requester_id': row['requester_id'],
                    'requester_name': row['requester_name'],
                    'requester_email': row['requester_email'],
                    'created_at': str(row['created_at']),
                    'status': row['status']
                })
                
            print(f"成功获取到 {len(requests)} 个好友请求")
            return requests
                
        except Exception as e:
            print(f"查询好友请求失败: {str(e)}")  # 打印具体错误信息
            traceback.print_exc()  # 输出完整堆栈信息
            if connection:
                connection.close()
            return []
            
    def send_friend_request(self, user_id, friend_username):
        """发送好友请求"""
        print(f"用户 {user_id} 尝试添加好友 '{friend_username}'")
        # 获取好友的用户ID
        friend_id = self.get_user_id(friend_username)
        if not friend_id:
            print(f"未找到用户名为 '{friend_username}' 的用户")
            return False, "用户不存在"
            
        # 不能添加自己为好友
        if user_id == friend_id:
            print(f"用户 {user_id} 尝试添加自己为好友")
            return False, "不能添加自己为好友"
            
        print(f"找到好友ID: {friend_id}，准备检查好友关系")
        connection = self.connect_to_database()
        if not connection:
            print("数据库连接失败")
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            
            # 检查是否已经存在好友关系
            check_sql = "SELECT status FROM friends WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)"
            print(f"检查好友关系SQL: {check_sql}, 参数: ({user_id}, {friend_id}, {friend_id}, {user_id})")
            cursor.execute(check_sql, (user_id, friend_id, friend_id, user_id))
            result = cursor.fetchone()
            print(f"好友关系检查结果: {result}")
            
            if result:
                # 由于使用了 DictCursor，结果为字典
                status = result['status']
                print(f"已存在好友关系，状态: {status}")
                if status == 'accepted':
                    print("已经是好友关系")
                    return False, "你们已经是好友了"
                elif status == 'pending':
                    print("好友请求已发送但未确认")
                    return False, "好友请求已发送，请等待对方确认"
                elif status == 'rejected':
                    # 如果之前被拒绝，可以重新发送请求
                    print("之前被拒绝，重新发送请求")
                    update_sql = "UPDATE friends SET status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE user_id = %s AND friend_id = %s"
                    print(f"更新好友关系SQL: {update_sql}, 参数: ({user_id}, {friend_id})")
                    cursor.execute(update_sql, (user_id, friend_id))
                elif status == 'blocked':
                    print("用户被对方屏蔽")
                    return False, "您已被对方屏蔽"
            else:
                # 插入新的好友请求
                print("未找到现有好友关系，插入新请求")
                insert_sql = "INSERT INTO friends (user_id, friend_id, status) VALUES (%s, %s, 'pending')"
                print(f"插入好友请求SQL: {insert_sql}, 参数: ({user_id}, {friend_id})")
                cursor.execute(insert_sql, (user_id, friend_id))
                
            connection.commit()
            print("好友请求操作提交成功")
            cursor.close()
            connection.close()
            return True, "好友请求已发送"
        except Exception as e:
            print(f"发送好友请求失败: {str(e)}")  # 打印具体错误信息
            traceback.print_exc()  # 输出完整堆栈信息
            if connection:
                connection.close()
            return False, "发送好友请求失败"
            
    def handle_friend_request(self, request_id, user_id, action):
        """处理好友请求"""
        if action not in ['accept', 'reject']:
            return False, "无效的操作"
            
        connection = self.connect_to_database()
        if not connection:
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            
            # 验证请求是否属于该用户
            check_sql = "SELECT user_id, friend_id FROM friends WHERE id = %s AND friend_id = %s AND status = 'pending'"
            cursor.execute(check_sql, (request_id, user_id))
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                connection.close()
                return False, "无效的好友请求"
                
            # 由于使用了 DictCursor，结果为字典
            requester_id = result['user_id']
            
            # 更新好友请求状态
            status = 'accepted' if action == 'accept' else 'rejected'
            update_sql = "UPDATE friends SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
            cursor.execute(update_sql, (status, request_id))
            
            # 如果接受好友请求，需要在反向关系中也添加一条记录
            if action == 'accept':
                # 检查是否已存在反向关系
                check_reverse_sql = "SELECT id FROM friends WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)"
                cursor.execute(check_reverse_sql, (user_id, requester_id, requester_id, user_id))
                reverse_result = cursor.fetchone()
                
                if reverse_result:
                    # 更新反向关系状态
                    update_reverse_sql = "UPDATE friends SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE id = %s"
                    cursor.execute(update_reverse_sql, (reverse_result['id'],))
                else:
                    # 插入反向关系
                    insert_reverse_sql = "INSERT INTO friends (user_id, friend_id, status) VALUES (%s, %s, 'accepted')"
                    cursor.execute(insert_reverse_sql, (user_id, requester_id))
                    
            connection.commit()
            cursor.close()
            connection.close()
            return True, f"好友请求已{('接受' if action == 'accept' else '拒绝')}"
        except Exception as e:
            print(f"处理好友请求失败: {e}")
            if connection:
                connection.close()
            return False, "处理好友请求失败"
            
    def remove_friend(self, user_id, friend_id):
        """删除好友"""
        connection = self.connect_to_database()
        if not connection:
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            
            # 删除双向好友关系
            delete_sql = "DELETE FROM friends WHERE (user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)"
            cursor.execute(delete_sql, (user_id, friend_id, friend_id, user_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            return True, "好友关系已解除"
        except Exception as e:
            print(f"删除好友失败: {e}")
            if connection:
                connection.close()
            return False, "删除好友失败"
            
    def set_friend_remark(self, user_id, friend_id, remark):
        """设置好友备注"""
        connection = self.connect_to_database()
        if not connection:
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            
            # 只更新当前用户对好友的备注，不涉及反向关系
            update_sql = """
            UPDATE friends 
            SET remark = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = %s AND friend_id = %s AND status = 'accepted'
            """
            cursor.execute(update_sql, (remark, user_id, friend_id))
            
            # 如果没有更新到记录，说明没有直接关系，尝试插入
            if cursor.rowcount == 0:
                # 检查是否存在反向关系
                check_sql = """
                SELECT id FROM friends 
                WHERE user_id = %s AND friend_id = %s AND status = 'accepted'
                """
                cursor.execute(check_sql, (friend_id, user_id))
                if cursor.fetchone():
                    # 存在反向关系，插入当前用户对好友的备注记录
                    insert_sql = """
                    INSERT INTO friends (user_id, friend_id, status, remark) 
                    VALUES (%s, %s, 'accepted', %s)
                    """
                    cursor.execute(insert_sql, (user_id, friend_id, remark))
            
            connection.commit()
            cursor.close()
            connection.close()
            return True, "备注设置成功"
        except Exception as e:
            print(f"设置备注失败: {e}")
            if connection:
                connection.close()
            return False, "设置备注失败"
            
    def get_friend_remark(self, user_id, friend_id):
        """获取好友备注"""
        connection = self.connect_to_database()
        if not connection:
            return None
            
        try:
            cursor = connection.cursor()
            
            # 只获取当前用户对好友的备注，不涉及反向关系
            select_sql = """
            SELECT remark FROM friends 
            WHERE user_id = %s AND friend_id = %s AND status = 'accepted'
            """
            cursor.execute(select_sql, (user_id, friend_id))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return result['remark'] if result else ''
        except Exception as e:
            print(f"获取备注失败: {e}")
            if connection:
                connection.close()
            return ''
            
    def save_chat_message(self, sender_id, receiver_id, message, message_type='text'):
        """保存聊天消息"""
        connection = self.connect_to_database()
        if not connection:
            return False, "数据库连接失败"
            
        try:
            cursor = connection.cursor()
            
            insert_sql = """
            INSERT INTO chat_messages (sender_id, receiver_id, message, message_type) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (sender_id, receiver_id, message, message_type))
            
            connection.commit()
            cursor.close()
            connection.close()
            return True, "消息保存成功"
        except Exception as e:
            print(f"保存消息失败: {e}")
            if connection:
                connection.close()
            return False, "保存消息失败"
            
    def get_chat_messages(self, user_id, friend_id, limit=50):
        """获取聊天记录"""
        connection = self.connect_to_database()
        if not connection:
            return []
            
        try:
            cursor = connection.cursor()
            
            # 获取双方聊天记录，按时间排序；当 limit <= 0 时返回全部
            if limit and int(limit) > 0:
                select_sql = """
                SELECT sender_id, receiver_id, message, message_type, created_at
                FROM chat_messages 
                WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
                ORDER BY created_at ASC
                LIMIT %s
                """
                cursor.execute(select_sql, (user_id, friend_id, friend_id, user_id, int(limit)))
            else:
                select_sql = """
                SELECT sender_id, receiver_id, message, message_type, created_at
                FROM chat_messages 
                WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
                ORDER BY created_at ASC
                """
                cursor.execute(select_sql, (user_id, friend_id, friend_id, user_id))
            messages = cursor.fetchall()
            # 转换 datetime 为字符串，便于 JSON 序列化
            formatted_messages = []
            for row in messages:
                formatted_messages.append({
                    'sender_id': row['sender_id'],
                    'receiver_id': row['receiver_id'],
                    'message': row['message'],
                    'message_type': row['message_type'],
                    'created_at': str(row['created_at'])
                })
            
            # 不再标记已读，也不更新任何阅读状态
            
            cursor.close()
            connection.close()
            return formatted_messages
        except Exception as e:
            print(f"获取聊天记录失败: {e}")
            if connection:
                connection.close()
            return []
            
    def handle_client(self, client_socket, address):
        """处理客户端连接"""
        print(f"好友列表服务器：客户端 {address} 已连接")
        
        try:
            client_socket.settimeout(15.0)
            while True:
                # 接收客户端发送的数据（聚合直到可解析为完整JSON）
                buf = b''
                request_data = None
                while True:
                    try:
                        chunk = client_socket.recv(4096)
                        if not chunk:
                            break
                        buf += chunk
                        try:
                            request_data = json.loads(buf.decode('utf-8'))
                            break
                        except json.JSONDecodeError:
                            continue
                    except socket.timeout:
                        # 若超时且还没有数据，继续等待下一轮；若已有数据但未完整，返回错误
                        if not buf:
                            continue
                        else:
                            request_data = None
                            break
                if request_data is None:
                    # 客户端已关闭或未发送有效数据
                    break
                print(f"好友列表服务器：收到来自 {address} 的数据: {request_data}")
                
                try:
                    # 解析JSON数据（已在上面完成）
                    action = request_data.get('action')
                    username = request_data.get('username')
                    
                    # 获取用户ID
                    user_id = self.get_user_id(username) if username else None
                    
                    if action == 'get_user_id':
                        # 返回当前用户名对应的ID
                        if user_id:
                            response = {
                                'status': 'success',
                                'user_id': user_id
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '用户不存在'
                            }
                    elif action == 'get_friends':
                        # 获取好友列表
                        if user_id:
                            friends = self.get_friends(user_id)
                            response = {
                                'status': 'success',
                                'friends': friends
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '用户不存在'
                            }
                            
                    elif action == 'get_requests':
                        # 获取好友请求
                        if user_id:
                            requests = self.get_friend_requests(user_id)
                            response = {
                                'status': 'success',
                                'requests': requests
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '用户不存在'
                            }
                            
                    elif action == 'send_request':
                        # 发送好友请求
                        friend_username = request_data.get('friend_username')
                        if user_id and friend_username:
                            success, message = self.send_friend_request(user_id, friend_username)
                            response = {
                                'status': 'success' if success else 'error',
                                'message': message
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误'
                            }
                            
                    elif action == 'handle_request':
                        # 处理好友请求
                        request_id = request_data.get('request_id')
                        action_type = request_data.get('action_type')  # accept 或 reject
                        if user_id and request_id and action_type:
                            success, message = self.handle_friend_request(request_id, user_id, action_type)
                            response = {
                                'status': 'success' if success else 'error',
                                'message': message
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误'
                            }
                            
                    elif action == 'remove_friend':
                        # 删除好友
                        # 优先使用IDs
                        req_user_id = request_data.get('user_id') or user_id
                        friend_id = request_data.get('friend_id')
                        if req_user_id and friend_id:
                            success, message = self.remove_friend(int(req_user_id), int(friend_id))
                            response = {
                                'status': 'success' if success else 'error',
                                'message': message
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误，需要 user_id 与 friend_id'
                            }
                            
                    elif action == 'set_remark':
                        # 设置好友备注
                        req_user_id = request_data.get('user_id') or user_id
                        friend_id = request_data.get('friend_id')
                        remark = request_data.get('remark', '')
                        if req_user_id and friend_id:
                            success, message = self.set_friend_remark(int(req_user_id), int(friend_id), remark)
                            response = {
                                'status': 'success' if success else 'error',
                                'message': message
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误，需要 user_id 与 friend_id'
                            }
                            
                    elif action == 'get_remark':
                        # 获取好友备注
                        req_user_id = request_data.get('user_id') or user_id
                        friend_id = request_data.get('friend_id')
                        if req_user_id and friend_id:
                            remark = self.get_friend_remark(int(req_user_id), int(friend_id))
                            response = {
                                'status': 'success',
                                'remark': remark
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误，需要 user_id 与 friend_id'
                            }
                            
                    elif action == 'send_message':
                        # 发送聊天消息
                        req_user_id = request_data.get('user_id') or user_id
                        friend_id = request_data.get('friend_id')
                        message = request_data.get('message', '')
                        message_type = request_data.get('message_type', 'text')
                        if req_user_id and friend_id and message:
                            success, msg = self.save_chat_message(int(req_user_id), int(friend_id), message, message_type)
                            response = {
                                'status': 'success' if success else 'error',
                                'message': msg
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误，需要 user_id, friend_id 和 message'
                            }
                            
                    elif action == 'get_messages':
                        # 获取聊天记录
                        req_user_id = request_data.get('user_id') or user_id
                        friend_id = request_data.get('friend_id')
                        limit = request_data.get('limit', 50)
                        if req_user_id and friend_id:
                            messages = self.get_chat_messages(int(req_user_id), int(friend_id), int(limit))
                            response = {
                                'status': 'success',
                                'messages': messages
                            }
                        else:
                            response = {
                                'status': 'error',
                                'message': '参数错误，需要 user_id 与 friend_id'
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
                try:
                    client_socket.send(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                except Exception as e:
                    print(f"发送响应失败: {e}")
                    traceback.print_exc()
                
        except ConnectionResetError:
            print(f"好友列表服务器：客户端 {address} 强制断开连接")
        except Exception as e:
            print(f"好友列表服务器：处理客户端 {address} 时出错: {e}")
            traceback.print_exc()
        finally:
            client_socket.close()
            print(f"好友列表服务器：客户端 {address} 连接已关闭")
            
    def start_server(self):
        """启动服务器"""
        # 初始化好友表
        if not self.init_friends_table():
            print("好友列表服务器：初始化好友表失败")
            return
            
        # 检查数据库中的表名
        try:
            table_names = self.check_table_names()
            if 'users' in table_names:
                print("使用 'users' 表")
            elif 'user' in table_names:
                print("使用 'user' 表")
            else:
                print("警告：未找到用户表")
        except Exception as e:
            print(f"检查表名时出错: {e}")
            
        try:
            # 创建socket对象
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 设置socket选项，允许地址重用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # 绑定地址和端口
            self.server_socket.bind((SERVER_HOST, SERVER_PORT))
            
            # 开始监听，最大连接数为10
            self.server_socket.listen(10)
            self.running = True
            
            print(f"好友列表服务器启动成功，监听地址: {SERVER_HOST}:{SERVER_PORT}")
            
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
                        print(f"好友列表服务器：接受客户端连接时出错: {e}")
                        
        except Exception as e:
            print(f"好友列表服务器：服务器启动失败: {e}")
            traceback.print_exc()
        finally:
            self.stop_server()
            
    def stop_server(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("好友列表服务器已停止")

def main():
    """主函数"""
    server = FriendListServer()
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n正在关闭好友列表服务器...")
        server.stop_server()

if __name__ == '__main__':
    main()