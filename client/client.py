import os
import socket
import threading
from Crypto.Cipher import Blowfish
from Crypto.Util.Padding import pad, unpad
import base64

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
ENCRYPTION_KEY = "kel4"

class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, self.port))

    def send_username(self, message):
        self.socket.sendall(message.encode())

    def send_message(self, message):
        encrypted_message = self.encrypt_message(ENCRYPTION_KEY, message)
        self.socket.sendall(encrypted_message.encode())

    def recv(self, size):
        encrypted_message = self.socket.recv(size).decode()
        return self.decrypt_message(ENCRYPTION_KEY, encrypted_message)

    def disconnect(self):
        self.socket.close()

    def parse_header(self, header):
        file_name = header.split('file-name: ')[1].split(',')[0]
        file_size = int(header.split('file-size: ')[1].split(',')[0])
        return file_name, file_size

    @staticmethod
    def encrypt_message(key, message):
        cipher = Blowfish.new(key.encode('utf-8'), Blowfish.MODE_ECB)
        padded_message = pad(message.encode('utf-8'), Blowfish.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return base64.b64encode(encrypted_message).decode('utf-8')
    
    @staticmethod
    def decrypt_message(key, encrypted_message):
        try:
            cipher = Blowfish.new(key.encode('utf-8'), Blowfish.MODE_ECB)
            decoded_message = base64.b64decode(encrypted_message.encode('utf-8'))
            decrypted_message = cipher.decrypt(decoded_message)
            return unpad(decrypted_message, Blowfish.block_size).decode('utf-8')
        except:
            return encrypted_message  # Return as-is if decryption fails (e.g., for file transfers)

def receive_messages(client):
    while True:
        try:
            message = client.recv(1024)
            if message:
                if "\r\n\r\n" in message:
                    header, _ = message.split("\r\n\r\n")
                    file_name, file_size = client.parse_header(header)
                    file_path = os.path.join(BASE_DIR, 'downloads', file_name)

                    with open(file_path, 'wb') as f:
                        total_data = 0
                        while total_data < file_size:
                            data = client.socket.recv(1024)
                            if not data:
                                break
                            f.write(data)
                            total_data += len(data)
                            print(f"Menerima data: {len(data)} bytes")
                        print(f"File {file_name} downloaded successfully.")
                else:
                    print(message)
        except Exception as e:
            print(f"Error receiving message: {e}")
            print("Disconnected from server.")
            break

if __name__ == "__main__":
    client = Client('127.0.0.1', 65432)
    client.connect()

    username = input("Enter your username: ")
    client.send_username(username)

    receive_thread = threading.Thread(target=receive_messages, args=(client,))
    receive_thread.start()

    while True:
        message = input()
        if message == "/quit":
            break

        elif message.startswith("/send_file"):
            try:
                _, recipient, filename = message.split(" ", 2)
                filepath = os.path.join(BASE_DIR, filename)

                if not os.path.exists(filepath):
                    print(f"File {filename} tidak ditemukan.")
                    continue

                filesize = os.path.getsize(filepath)
                header = f"file-name: {filename},\r\nfile-size: {filesize}\r\n\r\n"
                client.send_message(message)
                client.socket.sendall(header.encode())  # Send header unencrypted

                with open(filepath, "rb") as f:
                    data = f.read(1024)
                    while data:
                        client.socket.sendall(data)  # Send file data unencrypted
                        data = f.read(1024)

                print(f"File {filename} berhasil dikirim ke {recipient}")

            except ValueError:
                print("Format perintah salah. Gunakan: /send_file <penerima> <nama_file>")

        else:
            client.send_message(message)

    client.disconnect()