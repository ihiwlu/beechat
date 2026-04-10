import subprocess
import sys
import time
import os

def main():
    # 获取当前脚本所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 定义要启动的服务列表（按依赖顺序）
    servers = [
        "registerserver.py",
        "loginserver.py",
        "friendlistserver.py",  # 好友列表服务器需要优先启动
        "chatserver.py",
        "fileserver.py",
        "mail_id.py",
        "forgotserver.py"
    ]
    
    # 存储进程对象的字典
    processes = {}
    
    try:
        # 启动所有服务
        print("正在启动所有服务端程序...")
        for server in servers:
            print(f"启动 {server}...")
            # 启动进程并隐藏控制台窗口
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # 构建完整的服务器文件路径
            server_path = os.path.join(current_dir, server)
            
            # 检查文件是否存在
            if not os.path.exists(server_path):
                print(f"警告: 服务器文件 {server_path} 不存在，跳过启动")
                continue
            
            # 启动服务
            try:
                process = subprocess.Popen(
                    ["python", server_path],
                    cwd=current_dir,  # 设置工作目录
                    startupinfo=startupinfo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # 存储进程对象
                processes[server] = process
                # 对关键服务器增加更长的启动等待时间
                if server in ["friendlistserver.py", "loginserver.py"]:
                    time.sleep(1.0)  # 关键服务器等待1秒
                else:
                    time.sleep(0.2)  # 其他服务器短暂延迟
                print(f"  {server} 启动命令已发送")
            except Exception as e:
                print(f"  启动 {server} 失败: {e}")
            
        # 检查进程是否成功启动
        time.sleep(2)  # 等待2秒让进程启动
        print("\n检查服务启动状态...")
        running_services = []
        failed_services = []
        
        for server, process in processes.items():
            if process.poll() is None:
                print(f"✓ {server} 已成功启动并正在运行")
                running_services.append(server)
            else:
                stdout, stderr = process.communicate()
                print(f"✗ {server} 启动失败:")
                print(f"  返回码: {process.returncode}")
                if stdout:
                    print(f"  标准输出: {stdout}")
                if stderr:
                    print(f"  错误输出: {stderr}")
                failed_services.append(server)
                
        print(f"\n启动统计: {len(running_services)} 个服务运行中, {len(failed_services)} 个服务启动失败")
        
        if running_services:
            print("\n所有服务端已启动，输入 'exit' 并按回车停止所有服务...")
            
            # 等待用户输入
            while True:
                command = input("请输入命令: ").strip().lower()
                if command == "exit":
                    break
                else:
                    print("未知命令，请输入 'exit' 停止服务")
        else:
            print("\n没有服务成功启动，按回车键退出...")
            input()
            return
        
        # 停止所有服务
        print("\n开始停止所有服务端程序...")
        for server, process in processes.items():
            print(f"停止 {server}...")
            if process.poll() is None:  # 检查进程是否仍在运行
                process.terminate()  # 尝试正常终止
                # 等待终止
                try:
                    process.wait(timeout=5)
                    print(f"成功停止 {server}")
                except subprocess.TimeoutExpired:
                    # 正常终止失败，强制终止
                    process.kill()
                    print(f"强制停止 {server}")
            else:
                print(f"{server} 已停止")
                
    except Exception as e:
        print(f"发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n所有操作完成")
        input("按回车键退出...")

if __name__ == "__main__":
    main()
