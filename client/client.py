import os
import socket
import threading

BASE_DIR = os.path.dirname(os.path.realpath(__file__))


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        self.socket.connect((self.host, self.port))

    def send_message(self, message):
        self.socket.sendall(message.encode())

    def recv(self, size):
        return self.socket.recv(size).decode()

    def disconnect(self):
        self.socket.close()

    def parse_header(self, header):
        file_name = header.split('file-name: ')[1].split(',')[0]
        file_size = int(header.split('file-size: ')[1].split(',')[0])
        return file_name, file_size


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

        except:
            print("Disconnected from server.")
            break


if __name__ == "__main__":
    client = Client('127.0.0.1', 65432)
    client.connect()

    username = input("Enter your username: ")
    client.send_message(username)

    receive_thread = threading.Thread(target=receive_messages, args=(client,))
    receive_thread.start()

    while True:
        message = input()
        if message == "/quit":
            break

        elif message.startswith("/send_file"):
            try:
                _, recipient, filename = message.split(
                    " ", 2)  # Split maksimal 2 spasi
                filepath = os.path.join(BASE_DIR, filename)

                if not os.path.exists(filepath):
                    print(f"File {filename} tidak ditemukan.")
                    continue

                filesize = os.path.getsize(filepath)
                header = f"file-name: {filename},\r\nfile-size: {filesize}\r\n\r\n"
                client.send_message(message)
                client.send_message(header)

                with open(filepath, "rb") as f:
                    data = f.read(1024)
                    while data:
                        client.socket.sendall(data)
                        data = f.read(1024)

                # with open(filepath, "rb") as f:
                #     while True:
                #         data = f.read(1024)
                #         if not data:
                #             break
                #         client.socket.sendall(data)  # Kirim data file

                print(f"File {filename} berhasil dikirim ke {recipient}")

            except ValueError:
                print(
                    "Format perintah salah. Gunakan: /send_file <penerima> <nama_file>")

        else:
            client.send_message(message)

    client.disconnect()
