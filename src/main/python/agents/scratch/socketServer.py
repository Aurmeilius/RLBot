import socket
import select
import json

HOST = ''  # Symbolic name, meaning all available interfaces
PORT = 42008  # Arbitrary non-privileged port


class SocketServer:

    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = None
        self.connected = False
        pass

    def connect(self):
        # Bind socket to local host and port
        try:
            if self.conn is not None:
                self.conn.close()
            self.s.bind((HOST, PORT))
        except socket.error as msg:
            print('Bind failed. ' + str(msg))
            return

        print('Socket bind complete')

        # Start listening on socket
        self.s.listen(10)
        print('Socket now listening')

        # wait to accept a connection - blocking call
        self.conn, addr = self.s.accept()
        print('Connected with ' + addr[0] + ':' + str(addr[1]))
        self.connected = True

    def fetchControllerState(self):
        """
        Returns a dict with the controller state fetched from scratch
        """

        if self.conn is not None and self.connected:
            ready = select.select([self.conn], [], [], 0)
            data = None
            while ready[0]:
                size_data = self.conn.recv(2)
                size = int.from_bytes(size_data, byteorder='big')
                data = self.conn.recv(size)
                ready = select.select([self.conn], [], [], 0)

            if not data is None:
                return json.loads(data)

        return None

    def sendGameTickData(self, data):
        """
        :param data: A dict that should be serialized to JSON and sent to scratch
        """
        if self.conn is not None and self.connected:
            data_bytes = bytes(json.dumps(data), 'utf-8')
            self.conn.send(len(data_bytes).to_bytes(2, byteorder='big') + data_bytes)

    def destroy(self):
        self.connected = False
        if self.conn is not None:
            self.conn.close()
        if self.s is not None:
            self.s.close()