from flask import Flask, jsonify
import threading
import socket
import os
import zipfile
import base64

PORT = 5000
BUFFER_SIZE = 4096
NUM_DEVICES = 4

app = Flask(__name__)
server_running = False
text_contents = []

def encode_image_to_base64(file_path):
    with open(file_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

def handle_device_connection(conn, addr):
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
                image_data = encode_image_to_base64(file_path)
                text_contents.append({"file_name": file_name, "content": image_data, "type": "image"})
            elif file_name.lower().endswith('.txt'):
                with open(file_path, 'r') as f:
                    text_data = f.read()
                    text_contents.append({"file_name": file_name, "content": text_data, "type": "text"})
            else:
                print(f"Unsupported file type: {file_name}")

    print(f"DATA appended {len(text_contents)}")
    conn.close()

def start_main_device():
    global server_running
    server_running = True
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', PORT))
    server_socket.listen(NUM_DEVICES)

    print("Waiting for device connections...")
    threads = []
    for _ in range(NUM_DEVICES):
        try:
            conn, addr = server_socket.accept()
        except Exception as e:
            print(f"Exception occurred: {e}")

        thread = threading.Thread(target=handle_device_connection, args=(conn, addr))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

    server_socket.close()
    server_running = False
    print("Socket closed")

@app.route('/get-texts', methods=['GET'])
def get_texts():
    return jsonify({"texts": text_contents}), 200

@app.route('/start-server', methods=['GET'])
def start_server():
    global server_running
    if not server_running:
        thread = threading.Thread(target=start_main_device)
        thread.start()
        return jsonify({"message": "Server is waiting for device connections..."}), 200
    else:
        return jsonify({"message": "Server is already running."}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)