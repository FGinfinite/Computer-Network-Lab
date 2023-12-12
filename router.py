# 距离矢量路由算法的客户端

# 分析参数
import sys
import json
import argparse
import socket
import time


# 命令行参数列表：
# table_file: 相邻路由表文件
# node_name: 节点名称
# port: 端口号

class DV:
    def __init__(self, destination_node, next_node, distance, port):
        self.destination_node = destination_node
        self.next_node = next_node
        self.distance = distance
        self.port = port

    def __str__(self):
        return "Destination Node: %s, Next Node: %s, Distance: %s, Port: %s; " % (
            self.destination_node, self.next_node, self.distance, self.port)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return self.destination_node == other.destination_node and self.next_node == other.next_node and self.distance == other.distance and self.port == other.port

    def to_dict(self):
        return {
            "destination_node": self.destination_node,
            "next_node": self.next_node,
            "distance": str(self.distance),
            "port": str(self.port)
        }


class NeighborNode:
    def __init__(self, node_name, distance, port):
        self.node_name = node_name
        self.distance = distance
        self.port = str(port)


class Router:
    def __init__(self, router_name, port, table_file):
        self.log_count = 0
        self.router_name = router_name
        self.port = str(port)
        self.table_file = table_file
        self.log_print('Received args: ' + str(router_name) + ' ' + str(port) + ' ' + str(table_file))
        self.dv_table = []
        self.neighbor_nodes = []
        self.read_dv_table_file()
        # 监听本地端口
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('localhost', int(port)))

        self.log_print('Start listening on port ' + str(port))

    def listen(self):
        while True:
            data, addr = self.socket.recvfrom(65535)
            # 将data转换为json
            data = json.loads(data.decode('utf-8'))
            # 判断data的类型
            if data['type'] == 'update_table':
                # 接收到新的路由表
                self.log_print('Receive new dv_table from ' + data['router_name'])
                self.receive_dv_table_handle(data)
            elif data['type'] == 'send_table':
                self.log_print('Receive command for sending dv_table')
                # 接收到请求路由表的请求
                self.send_dv_table_handle(data)
            elif data['type'] == 'data_packet':
                self.log_print('Receive data packet')
                # 接收到数据包
                self.data_packet_handle(data)
            elif data['type'] == 'exit':
                # 接收到退出请求
                self.log_print('Receive exit command')
                # 解除监听
                self.socket.close()
                exit(0)

    def receive_dv_table_handle(self, data):
        # 读取dv_table
        dv_table = data['dv_table']
        # 读取router_name
        router_name = data['router_name']
        # 读取port
        port = data['port']
        # 更新dv_table
        self.update_dv_table(
            [DV(dv['destination_node'], dv['next_node'], dv['distance'], dv['port']) for dv in dv_table],
            router_name, str(port))

    def send_dv_table_handle(self, data):
        # 发送自己的路由表
        self.send_dv_table()

    def data_packet_handle(self, data):
        # 读取目的节点
        destination_node = data['destination_node']
        source_node = data['source_node']
        if destination_node != self.router_name:
            # 读取数据
            msg = data['msg']
            # 读取下一跳节点
            next_port = None
            next_node = ''
            for dv in self.dv_table:
                if dv.destination_node == destination_node:
                    next_port = dv.port
                    next_node = dv.next_node
                    break
            # 发送数据包
            self.socket.sendto(
                json.dumps({
                    "type": "data_packet",
                    "source_node": source_node,
                    "destination_node": destination_node,
                    "msg": msg}).encode(
                    'utf-8'), ('localhost', int(next_port)))
            self.log_print(
                'Forward msg to: ' + next_node + ' which is from ' + source_node + ' to ' + destination_node)
        else:
            self.log_print('Receive msg:' + data['msg'] + ' from: ' + source_node)

    def update_dv_table(self, dv_table, router_name, port):
        # 将新dv_table中的next_node改为router_name并增加对应距离
        for neighbor_node in self.neighbor_nodes:
            if neighbor_node.node_name == router_name:
                for dv in dv_table:
                    dv.next_node = router_name
                    dv.port = port
                    dv.distance = int(dv.distance) + int(neighbor_node.distance)

        # 对于dv_table中的每一项
        for dv_new in dv_table:
            # 若目的节点等于自己，则跳过
            if dv_new.destination_node != self.router_name:
                # 对于原dv_table中的每一项
                flag = False
                for dv_src in self.dv_table:
                    # 若新旧目的节点相同
                    if dv_src.destination_node == dv_new.destination_node:
                        flag = True
                        # 若新旧下一跳节点相同，则更新距离
                        if dv_src.next_node == dv_new.next_node:
                            dv_src.distance = dv_new.distance
                        # 若新旧下一跳节点不同，则比较距离，更新距离与下一跳节点
                        elif int(dv_src.distance) > int(dv_new.distance):
                            dv_src.distance = dv_new.distance
                            dv_src.next_node = dv_new.next_node
                            dv_src.port = dv_new.port
                        break
                if not flag:
                    self.dv_table.append(dv_new)
        self.log_print('Updated dv_table: ' + str(self.dv_table))

    def read_dv_table_file(self):
        # 读取相邻路由表文件
        with open(self.table_file, 'r') as f:
            lines = f.readlines()

        # 解析相邻路由表文件
        for line in lines:
            # 去除行尾的换行符
            line = line.strip()

            # 跳过空行
            if not line:
                continue

            # 解析一行
            neighbor_name, distance, port = line.split(' ')
            self.neighbor_nodes.append(NeighborNode(neighbor_name, distance, port))
            self.dv_table.append(DV(neighbor_name, neighbor_name, distance, port))
        self.log_print('Read dv_table file successfully')
        self.log_print('dv_table: ' + str(self.dv_table))

    def send_dv_table(self):
        # 发送自己的路由表给相邻节点
        for neighbor_node in self.neighbor_nodes:
            # 发送dv_table、self.router_name、self.port
            json_data = json.dumps({
                "type": "update_table",
                "router_name": self.router_name,
                "port": str(self.port),
                "dv_table": [dv.to_dict() for dv in self.dv_table]}
            ).encode(
                'utf-8')
            self.log_print('Send file size of : ' + str(sys.getsizeof(json_data)) + ' bytes')
            self.socket.sendto(
                json_data, ('localhost', int(neighbor_node.port)))

    def log_print(self, msg):
        with open(f'./logs/{self.router_name}_log.txt', 'a', encoding="UTF-8") as f:
            f.write(str(self.log_count) + ': ' + msg + '\n')
        self.log_count += 1


def read_args():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description='Process command line arguments.')

    # 添加要识别的命令行参数
    parser.add_argument('file', type=str, help='路由表文件名')
    parser.add_argument('node_name', type=str, help='节点名称')
    parser.add_argument('port', type=int, help='端口号')

    # 使用 parse_args() 方法解析命令行参数
    args = parser.parse_args()

    # 返回解析结果
    return args.file, args.node_name, args.port


def main():
    # 读取命令行参数
    table_file, cur_node_name, cur_port = read_args()

    # 创建路由器对象
    router = Router(cur_node_name, cur_port, table_file)

    # 启动路由器
    router.listen()


if __name__ == '__main__':
    main()
