import pymysql
from config import DB_CONFIG

def check_user_table():
    """检查数据库中的user/users表"""
    try:
        # 连接到数据库
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            charset=DB_CONFIG['charset'],
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        cursor = connection.cursor()
        
        # 检查user表是否存在
        try:
            cursor.execute("SELECT COUNT(*) as count FROM user")
            result = cursor.fetchone()
            print(f"user表存在，记录数: {result['count'] if isinstance(result, dict) else result[0]}")
        except Exception as e:
            print(f"user表不存在或查询失败: {e}")
        
        # 检查users表是否存在
        try:
            cursor.execute("SELECT COUNT(*) as count FROM users")
            result = cursor.fetchone()
            print(f"users表存在，记录数: {result['count'] if isinstance(result, dict) else result[0]}")
        except Exception as e:
            print(f"users表不存在或查询失败: {e}")
            
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"数据库连接失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_user_table()