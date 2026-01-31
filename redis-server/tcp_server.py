import base64
import socket
import time
import threading
import random
import uuid
import hashlib
from urllib.parse import quote, unquote

class TCPServer:
    def __init__(self, host='localhost', port=6379):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow address reuse
        self.server_socket.bind((host, port))
        self.server_socket.listen(5) # Backlog of 5 connections
        print(f"Server listening on {host}:{port}")

    def handle_client(self, conn, addr):
        print(f"Connection from {addr}")
        prompt = "tcpserver@python$ "
        conn.send(f"Welcome to the TCP Server!\n{prompt}".encode('utf-8'))
        try:
            while True:
                data = conn.recv(1024).decode('utf-8').strip()
                if not data:
                    break # Connection closed
                if data.upper() == "PING":
                    response = "-> PONG\n"
                elif data.upper() == "ECHO":
                    response = f"-> {data[5:]}\n"  # Echo back the message after "ECHO "
                elif data.upper() == "TIME":
                    response = f"-> {time.ctime()}\n"
                elif data.upper() == "DATE":
                    response = f"-> {time.strftime('%Y-%m-%d')}\n"
                elif data.upper() == "RANDOM":
                    response = f"-> {random.randint(0, 100)}\n"
                elif data.upper() == "UUID":
                    response = f"-> {uuid.uuid4()}\n"
                elif data[:7].upper() == "REVERSE":
                    response = f"-> {data[8:][::-1]}\n"  # Reverse the message after "REVERSE "
                elif data[:3].upper() == "LEN":
                    response = f"-> {len(data[4:])}\n"  # Length of the message after "LEN "
                elif data[:5].upper() == "WORDS":
                    words = data[6:].split()
                    response = f"-> {len(words)}\n"  # Number of words in the message after "WORDS "
                elif data[:4].upper() == "HASH": 
                    hash_object = hashlib.sha256(data[5:].encode('utf-8'))
                    response = f"-> {hash_object.hexdigest()}\n"  # return a SHA-256 hash of the message
                elif data[:9].upper() == "BASE64ENC":
                    response = f"-> {base64.b64encode(data[10:].encode('utf-8')).decode('utf-8')}\n"
                elif data[:9].upper() == "BASE64DEC":
                    response = f"-> {base64.b64decode(data[10:]).decode('utf-8')}\n"
                elif data[:6].upper() == "URLENC": 
                    response = f"-> {quote(data[7:])}\n"
                elif data[:6].upper() == "URLDEC":
                    response = f"-> {unquote(data[7:])}\n"
                elif data.upper() == "HELP":
                    response = (
                        "-> Available commands:\n"
                        "   - PING\n"
                        "   - ECHO <message>\n"
                        "   - TIME\n"
                        "   - DATE\n"
                        "   - RANDOM\n"
                        "   - UUID\n"
                        "   - REVERSE <message>\n"
                        "   - LEN <message>\n"
                        "   - WORDS <message>\n"
                        "   - HASH <message>\n"
                        "   - BASE64ENC <message>\n"
                        "   - BASE64DEC <message>\n"
                        "   - URLENC <message>\n"
                        "   - URLDEC <message>\n"
                        "   - HELP\n"
                        "   - QUIT\n"
                    )
                elif data.upper() == "QUIT":
                    response = "-> Goodbye!\n"
                    conn.send(response.encode('utf-8'))
                    break
                else:
                    response = f"--ERR Unknown command: {data}\n"
                conn.send(f"{response}{prompt}".encode('utf-8'))
        except Exception as e:
            conn.send(f"-ERR Unexpected error: {str(e)}\n{prompt}".encode('utf-8'))
        finally:
            print(f"Closing connection from {addr}")
            conn.close()
    
    def run(self):
        try:
            while True:
                conn, addr = self.server_socket.accept()
                # Start a new thread for each client
                threading.Thread(target=self.handle_client, args=(conn, addr)).start()
        except KeyboardInterrupt:
            print("Shutting down server.")
        finally:
            self.server_socket.close()

if __name__ == "__main__":
    server = TCPServer()
    server.run()
