from flask import Flask, jsonify
import threading
import socket
import os
import zipfile
import base64

PORT=443
BUFFER_SIZE = 4096
NUM_DEVICES = 4

class MainDevice:
    def __init__(self):
        self.app = Flask(__name__)
        self.server_running = False
        self.text_contents = []

        # Define Flask routes
        self.app.add_url_rule('/get-texts', 'get_texts', self.get_texts, methods=['GET'])
        self.app.add_url_rule('/start-server', 'start_server', self.start_server, methods=['GET'])
        self.app.add_url_rule('/', 'device', self.device)

        # Register methods
        self.app.before_first_request(self.initialize)

    def initialize(self):
        # Any initialization can be done here
        pass

    def encode_image_to_base64(self, file_path):
        with open(file_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

    def handle_device_connection(self, conn, addr):
        print(f"Connected to {addr}")
        data = b""

        while True:
            packet = conn.recv(BUFFER_SIZE)
            if not packet:
                break
            data += packet

        zip_path = "received.zip"
        with open(zip_path, "wb") as f:
            f.write(data)

        extract_dir = "extracted_files"
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

            for file_name in zip_ref.namelist():
                file_path = os.path.join(extract_dir, file_name)

                if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                    image_data = self.encode_image_to_base64(file_path)
                    self.text_contents.append({"file_name": file_name, "content": image_data, "type": "image"})
                elif file_name.lower().endswith('.txt'):
                    with open(file_path, 'r') as f:
                        text_data = f.read()
                        self.text_contents.append({"file_name": file_name, "content": text_data, "type": "text"})
                else:
                    print(f"Unsupported file type: {file_name}")

        print(f"DATA appended {len(self.text_contents)}")
        conn.close()

    def start_main_device(self):
        self.server_running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('', PORT))
        server_socket.listen(NUM_DEVICES)

        print("Waiting for specific device connections...")
        threads = []
        for _ in range(NUM_DEVICES):
            try:
                conn, addr = server_socket.accept()
            except Exception as e:
                print(f"Exception occurred: {e}")

            thread = threading.Thread(target=self.handle_device_connection, args=(conn, addr))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

        server_socket.close()
        self.server_running = False
        print("Socket closed")

    def get_texts(self):
        return jsonify({"texts": self.text_contents}), 200

    def start_server(self):
        if not self.server_running:
            thread = threading.Thread(target=self.start_main_device)
            thread.start()
            return jsonify({"message": "Server is waiting for SPECIFIC device connections..."}), 200
        else:
            return jsonify({"message": "Server is already running."}), 200

    def device(self):
        return "THIS MAIN DEVICE"

if __name__ == '__main__':
    device = MainDevice()
    device.app.run(host='0.0.0.0', port=5001, debug=True)
