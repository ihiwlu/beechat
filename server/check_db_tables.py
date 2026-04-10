import pymysql
from config import DB_CONFIG

def check_table_names():
    """检查数据库中的表名"""
    try:
        # 连接到数据库
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port'],
            charset=DB_CONFIG['charset'],
            cursorclass=pymysql.cursors.DictCursor
        )
        
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        cursor.close()
        connection.close()
        
        # 提取表名
        table_names = []
        for table in tables:
            if isinstance(table, dict):
                # 如果是字典格式，尝试获取第一个值
                table_names.append(list(table.values())[0])
            else:
                # 如果是元组格式，获取第一个元素
                table_names.append(table[0])
        
        print("数据库中的表:")
        for name in table_names:
            print(f"  - {name}")
            
        return table_names
    except Exception as e:
        print(f"查询表名失败: {e}")
        return []

if __name__ == "__main__":
    check_table_names()