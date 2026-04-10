import pymysql
from config import DB_CONFIG

def check_table_names():
    """检查数据库中的表名"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            charset=DB_CONFIG['charset']
        )
        
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # 提取表名
        table_names = [table[0] for table in tables]
        print(f"数据库中的表: {table_names}")
        return table_names
    except Exception as e:
        print(f"查询表名失败: {e}")
        return []

if __name__ == "__main__":
    check_table_names()