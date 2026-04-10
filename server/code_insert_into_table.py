__author__ = 'gg'
import pymysql
from datetime import datetime, timedelta
from pymysql.cursors import DictCursor

class EmailVerificationDB:
    def __init__(self, host="localhost", port=3306, user="root", password="", db_name=""):
        """
        初始化数据库连接（适配 email_verification 表结构）
        :param host: 数据库地址（默认本地）
        :param port: 数据库端口（默认3306）
        :param user: 数据库用户名
        :param password: 数据库密码
        :param db_name: 数据库名（需包含 email_verification 表）
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db_name = db_name
        self.connection = None  # 数据库连接对象
        # 初始化时检查并创建表
        self.ensure_tables()

    def _get_db_connection(self):
        """获取数据库连接（自动重连）"""
        if not self.connection or not self.connection.open:
            try:
                self.connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.db_name,
                    charset="utf8",
                    cursorclass=DictCursor,  # 返回字典格式结果，便于取值
                    connect_timeout=10  # 连接超时时间
                )
            except Exception as e:
                raise Exception(f"数据库连接失败：{str(e)}（请检查账号密码和数据库是否存在）")
        return self.connection

    def ensure_tables(self):
        """检查并创建必要的表"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 检查email_verification表是否存在
                    check_table_sql = """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_name = 'email_verification'
                    """
                    cursor.execute(check_table_sql, (self.db_name,))
                    table_exists = cursor.fetchone()['COUNT(*)']
                    
                    if not table_exists:
                        # 创建email_verification表
                        create_table_sql = """
                        CREATE TABLE email_verification (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            email VARCHAR(255) NOT NULL,
                            code VARCHAR(20) NOT NULL,
                            created_at DATETIME NOT NULL,
                            expires_at DATETIME NOT NULL,
                            is_used TINYINT(1) NOT NULL DEFAULT 0,
                            INDEX idx_email (email),
                            INDEX idx_code (code),
                            INDEX idx_expires_at (expires_at)
                        )
                        """
                        cursor.execute(create_table_sql)
                        conn.commit()
                        print(f"[EmailVerificationDB] email_verification表已创建")
                    else:
                        print(f"[EmailVerificationDB] email_verification表已存在")
                        
                    # 检查user_info表是否存在
                    check_user_info_table_sql = """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_name = 'user_info'
                    """
                    cursor.execute(check_user_info_table_sql, (self.db_name,))
                    user_info_table_exists = cursor.fetchone()['COUNT(*)']
                    
                    if not user_info_table_exists:
                        # 创建user_info表
                        create_user_info_table_sql = """
                        CREATE TABLE user_info (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id INT NOT NULL,
                            email VARCHAR(100) NOT NULL UNIQUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            INDEX idx_user_id (user_id),
                            INDEX idx_email (email)
                        )
                        """
                        cursor.execute(create_user_info_table_sql)
                        conn.commit()
                        print(f"[EmailVerificationDB] user_info表已创建")
                    else:
                        print(f"[EmailVerificationDB] user_info表已存在")
                        
        except Exception as e:
            print(f"[EmailVerificationDB] 表检查/创建失败: {e}")
            # 不抛出异常，允许程序继续运行

    def save_verification_code(self, email, code, valid_minutes=5):
        """
        保存验证码到 email_verification 表
        :param email: 接收验证码的邮箱
        :param code: 生成的验证码（如5位数字）
        :param valid_minutes: 有效期（分钟），用于计算 expires_at
        :return: 成功返回 True，失败返回 False
        """
        try:
            # 1. 计算关键时间：生成时间（created_at）和过期时间（expires_at）
            created_at = datetime.now()  # 当前时间（生成时间）
            expires_at = created_at + timedelta(minutes=valid_minutes)  # 过期时间=生成时间+有效期

            # 2. 数据库操作：失效该邮箱旧验证码，然后插入新验证码
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 将该邮箱所有未使用且未过期的旧验证码标记为已使用（防止重复验证）
                    update_old_sql = """
                    UPDATE email_verification
                    SET is_used = 1
                    WHERE email = %s
                      AND is_used = 0
                      AND expires_at > NOW()  -- 只失效未过期的旧验证码
                    """
                    cursor.execute(update_old_sql, (email,))

                    # 执行插入操作
                    insert_sql = """
                    INSERT INTO email_verification
                    (email, code, created_at, expires_at, is_used)
                    VALUES (%s, %s, %s, %s, 0)  -- is_used 默认0（未使用）
                    """

                    # 执行插入，使用计算得到的时间而非硬编码时间
                    affected_rows = cursor.execute(
                        insert_sql,
                        (email, code, created_at.strftime("%Y-%m-%d %H:%M:%S"), 
                         expires_at.strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    conn.commit()  # 提交事务
                    print("验证码已成功插入")

            # 插入成功的判断：影响行数>0（成功插入1条数据）
            return affected_rows > 0

        except Exception as e:
            # 出错时回滚事务，避免脏数据
            if "conn" in locals() and conn.open:
                conn.rollback()
            print(f"保存验证码失败：{str(e)}（检查SQL语句是否与表结构匹配）")
            return False

    def verify_code(self, email, input_code):
        """
        验证用户输入的验证码是否有效（适配你的表结构）
        有效条件：邮箱匹配 + 验证码匹配 + 未使用 + 未过期
        :param email: 用户的邮箱
        :param input_code: 用户输入的验证码
        :return: 有效返回 True，无效返回 False
        """
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 查询条件：严格匹配你的表字段和有效规则
                    query_sql = """
                    SELECT id FROM email_verification
                    WHERE email = %s
                      AND code = %s
                      AND is_used = 0
                      AND expires_at > NOW()  -- 未过期（当前时间 < 过期时间）
                    LIMIT 1  -- 只取1条有效数据（避免重复）
                    """
                    cursor.execute(query_sql, (email, input_code))
                    valid_record = cursor.fetchone()  # 获取查询结果

                    # 若存在有效记录：标记为已使用，返回True
                    if valid_record:
                        update_used_sql = """
                        UPDATE email_verification
                        SET is_used = 1
                        WHERE id = %s  -- 根据唯一ID更新，避免误改
                        """
                        cursor.execute(update_used_sql, (valid_record["id"],))
                        conn.commit()
                        return True
                    # 无有效记录：返回False
                    return False

        except Exception as e:
            print(f"验证验证码失败：{str(e)}")
            return False

    def close_connection(self):
        """关闭数据库连接（避免资源泄露）"""
        if self.connection and self.connection.open:
            self.connection.close()
            print("数据库连接已关闭")

    def clean_expired_codes(self):
        """清理数据库中所有已过期的验证码（expires_at < 当前时间）"""
        try:
            with self._get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 删除所有过期且已使用/未使用的记录（过期后均无价值）
                    delete_sql = """
                    DELETE FROM email_verification
                    WHERE expires_at < NOW()
                    """
                    affected_rows = cursor.execute(delete_sql)
                    conn.commit()
                    print(f" 已清理 {affected_rows} 条过期验证码记录")
                    return affected_rows  # 返回清理的记录数
        except Exception as e:
            print(f"清理过期验证码失败：{str(e)}")
            return 0

# ------------------- 使用示例 -------------------
if __name__ == "__main__":
    MYSQL_CONFIG = {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "abc123",
        "db_name": "test"
    }
    
    # 初始化数据库操作对象
    db_handler = EmailVerificationDB(** MYSQL_CONFIG)

    # 1. 先清理过期记录（可在项目启动时、或每天首次执行验证码操作时调用）
    db_handler.clean_expired_codes()

    # 2. 模拟场景1：发送邮件后，保存验证码到数据库
    user_email = "2726322671@qq.com"  # 用户的邮箱
    generated_code = "85274"          # 生成的5位数字验证码（邮件发送的验证码）
    valid_minutes = 5                 # 有效期5分钟

    # 调用保存方法
    save_success = db_handler.save_verification_code(user_email, generated_code, valid_minutes)
    if save_success:
        print(f" 验证码 {generated_code} 已保存到数据库（邮箱：{user_email}）")
    else:
        print(f"验证码保存失败")

    # 3. 模拟场景2：用户输入验证码后，验证有效性
    user_input_code = "85274"  # 用户输入的验证码（正确情况）
    # user_input_code = "12345"  # 错误情况（测试用）

    verify_result = db_handler.verify_code(user_email, user_input_code)
    if verify_result:
        print(f"验证码验证通过，可继续后续操作（如密码重置）")
    else:
        print(f"验证码无效（可能：不匹配/已使用/已过期）")

    # 4. 关闭数据库连接（必须调用，避免资源占用）
    db_handler.close_connection()
