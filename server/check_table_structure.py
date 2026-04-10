import pymysql
import traceback
from config import DB_CONFIG

def check_table_structure():
    """检查数据库表结构"""
    try:
        # 连接到数据库
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # 检查user表结构
        print("检查user表结构...")
        cursor.execute("DESCRIBE user")
        user_columns = cursor.fetchall()
        print("user表字段:")
        for column in user_columns:
            print(f"  {column[0]} - {column[1]} - {column[2]} - {column[3]} - {column[4]} - {column[5]}")
        
        print("\n检查friends表结构...")
        cursor.execute("DESCRIBE friends")
        friends_columns = cursor.fetchall()
        print("friends表字段:")
        for column in friends_columns:
            print(f"  {column[0]} - {column[1]} - {column[2]} - {column[3]} - {column[4]} - {column[5]}")
        
        # 检查表中的数据
        print("\n检查user表数据...")
        cursor.execute("SELECT COUNT(*) FROM user")
        user_count = cursor.fetchone()[0]
        print(f"user表记录数: {user_count}")
        
        print("\n检查friends表数据...")
        cursor.execute("SELECT COUNT(*) FROM friends")
        friends_count = cursor.fetchone()[0]
        print(f"friends表记录数: {friends_count}")
        
        # 检查user表中是否包含必要的字段
        user_field_names = [column[0] for column in user_columns]
        required_fields = ['id', 'username', 'password', 'email', 'nickname', 'status', 'avatar']
        missing_fields = [field for field in required_fields if field not in user_field_names]
        
        if missing_fields:
            print(f"\n警告: user表缺少以下字段: {missing_fields}")
        else:
            print("\nuser表包含所有必需字段")
        
        cursor.close()
        connection.close()
        
        print("\n检查完成!")
        
    except Exception as e:
        print(f"检查过程中出错: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    check_table_structure()