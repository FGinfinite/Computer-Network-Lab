import sys
import subprocess
import time
import json
import socket


# 读取参数
# 设置相邻路由文件
# 拉起程序
#

# 迭代器获取大写字母
def get_letter():
    for i in range(65, 91):
        yield chr(i)


class DataPacket:
    def __init__(self, type_, source_node, destination_node, msg):
        self.type = type_
        self.source_node = source_node
        self.destination_node = destination_node
        self.msg = msg

    def to_dict(self):
        return {
            "type": self.type,
            "source_node": self.source_node,
            "destination_node": self.destination_node,
            "msg": self.msg
        }


def main():
    with open('config.json', 'r') as f:
        config = json.load(f)

    port = int(config['port'])
    context = config['context']

    count = 1
    for node in context:
        with open(f"./tables/{node['router_name']}.txt", 'w') as f:
            for neighbor_node in node['DV']:
                f.write(
                    f"{neighbor_node['router_name']} {neighbor_node['distance']} {port + (ord(neighbor_node['router_name']) - ord('A')) + 1}\n")
        subprocess.Popen(
            [sys.executable, 'router.py', f"./tables/{node['router_name']}.txt", f"{node['router_name']}",
             str(port + count)])
        count += 1

    time.sleep(1)
    command_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sending_count = 0
    while sending_count < 5:
        count = 1
        for _ in context:
            command_data.sendto(json.dumps({"type": "send_table", }).encode('utf-8'), ('localhost', port + count))
            count += 1

        time.sleep(1)
        sending_count += 1

    time.sleep(3)

    # 发送数据包：
    data_packet = DataPacket("data_packet", "F", "C", "Hello, Mr. C, I'm F")
    command_data.sendto(json.dumps(data_packet.to_dict()).encode('utf-8'), ('localhost', port + 6))

    time.sleep(1)

    data_packet = DataPacket("data_packet", "C", "F", "Hello, Miss. F, I'm C")
    command_data.sendto(json.dumps(data_packet.to_dict()).encode('utf-8'), ('localhost', port + 3))

    time.sleep(1)

    count = 1
    for _ in context:
        command_data.sendto(json.dumps({"type": "exit", }).encode('utf-8'), ('localhost', port + count))
        count += 1


if __name__ == '__main__':
    main()
