import os
import socket
import threading

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
clients = {}


class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))

    def start(self):
        self.socket.listen()
        print(f"Server listening on {self.host}:{self.port}")
        while True:
            conn, addr = self.socket.accept()
            thread = threading.Thread(
                target=self.handle_client, args=(conn, addr))
            thread.start()

    def handle_client(self, conn, addr):
        print(f"Connected by {addr}")

        username = conn.recv(1024).decode().strip()
        if username in clients:
            conn.sendall("Username sudah terpakai!".encode())
            conn.close()
            return

        clients[username] = conn
        print(f"{username} joined the chat!")
        # Umumkan ketika user bergabung
        self.broadcast_message(username, f"{username} joined the chat!")

        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

                if data.startswith("/send_file"):
                    _, recipient, filename = data.split(
                        " ", 2)  # Split dengan maksimal 2 spasi
                    self.receive_and_forward_file(
                        conn, username, recipient, filename)
                else:
                    self.broadcast_message(username, data)

            except:
                break

        del clients[username]
        conn.close()
        print(f"{username} left the chat.")
        # Umumkan ketika user keluar
        self.broadcast_message(username, f"{username} left the chat!")

    def broadcast_message(self, sender, message):
        for recipient, client_conn in clients.items():
            if recipient != sender:
                try:
                    client_conn.sendall(f"{sender}: {message}".encode())
                except:
                    pass

    def receive_and_forward_file(self, conn, sender, recipient, filename):
        if recipient not in clients:
            conn.sendall(
                f"Pengguna {recipient} tidak ditemukan atau sedang offline.".encode())
            return

        recipient_conn = clients[recipient]

        # Terima header file dari pengirim
        header = conn.recv(1024).decode()
        file_name, file_size = self.parse_header(header)

        # Kirim header file ke penerima
        recipient_conn.sendall(header.encode())

        # Terima dan teruskan data file ke penerima
        total_data = 0
        # Simpan file sementara di server
        with open(os.path.join(BASE_DIR, "temp", file_name), "wb") as f:
            while total_data < file_size:
                data = conn.recv(1024)
                if not data:
                    break
                f.write(data)
                total_data += len(data)
                recipient_conn.sendall(data)

        print(f"File {filename} berhasil dikirim dari {sender} ke {recipient}")

        # Hapus file sementara jika diperlukan
        # os.remove(os.path.join(BASE_DIR, 'temp', file_name))

    def parse_header(self, header):
        file_name = header.split('file-name: ')[1].split(',')[0]
        file_size = int(header.split('file-size: ')[1].split(',')[0])
        return file_name, file_size


if __name__ == "__main__":
    server = Server("127.0.0.1", 65432)
    server.start()
