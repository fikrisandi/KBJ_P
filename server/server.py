import os
import socket
import threading
from Crypto.Cipher import Blowfish
from Crypto.Util.Padding import pad, unpad
import base64

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
clients = {}
ENCRYPTION_KEY = "kel4"

class Server:
    @staticmethod
    def encrypt_message(key, message):
        cipher = Blowfish.new(key.encode('utf-8'), Blowfish.MODE_ECB)
        padded_message = pad(message.encode('utf-8'), Blowfish.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return base64.b64encode(encrypted_message).decode('utf-8')
    
    @staticmethod
    def decrypt_message(key, encrypted_message):
        cipher = Blowfish.new(key.encode('utf-8'), Blowfish.MODE_ECB)
        decoded_message = base64.b64decode(encrypted_message.encode('utf-8'))
        decrypted_message = cipher.decrypt(decoded_message)
        return unpad(decrypted_message, Blowfish.block_size).decode('utf-8')

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
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
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
        self.broadcast_message(username, f"{username} joined the chat!")

        while True:
            try:
                encrypted_data = conn.recv(1024).decode()
                if not encrypted_data:
                    break
                print("encrypt data :", encrypted_data)
                data = self.decrypt_message(ENCRYPTION_KEY, encrypted_data)
                print("decrypt data :", data)
                if data.startswith("/send_file"):
                    _, recipient, filename = data.split(" ", 2)
                    self.receive_and_forward_file(conn, username, recipient, filename)
                else:
                    self.broadcast_message(username, data)

            except Exception as e:
                print(f"Error handling client {username}: {e}")
                break

        del clients[username]
        conn.close()
        print(f"{username} left the chat.")
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
            conn.sendall(self.encrypt_message(ENCRYPTION_KEY, f"Pengguna {recipient} tidak ditemukan atau sedang offline.").encode())
            return

        recipient_conn = clients[recipient]

        header = conn.recv(1024).decode()
        file_name, file_size = self.parse_header(header)

        recipient_conn.sendall(header.encode())

        total_data = 0
        with open(os.path.join(BASE_DIR, "temp", file_name), "wb") as f:
            while total_data < file_size:
                data = conn.recv(1024)
                if not data:
                    break
                f.write(data)
                total_data += len(data)
                recipient_conn.sendall(data)

        print(f"File {filename} berhasil dikirim dari {sender} ke {recipient}")

    def parse_header(self, header):
        file_name = header.split('file-name: ')[1].split(',')[0]
        file_size = int(header.split('file-size: ')[1].split(',')[0])
        return file_name, file_size

if __name__ == "__main__":
    server = Server("127.0.0.1", 65432)
    server.start()