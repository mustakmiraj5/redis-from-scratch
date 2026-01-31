import socket
import time
import threading

class TCPServer:
    def __init__(self, host='localhost', port=6379):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow address reuse
        self.server_socket.bind((host, port))
        self.server_socket.listen(5) # Backlog of 5 connections
        print(f"Server listening on {host}:{port}")

    def handle_client(self, conn, addr):
        print(f"Connection from {addr}")
        conn.send(b"Welcome to the TCP Server!\n")
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
                elif data.upper() == "HELP":
                    response = "-> Available commands: PING, ECHO <message>, TIME, DATE, HELP, QUIT\n"
                elif data.upper() == "QUIT":
                    response = "-> Goodbye!\n"
                    conn.send(response.encode('utf-8'))
                    break
                else:
                    response = f"--ERR Unknown command: {data}\n"
                conn.send(response.encode('utf-8'))
        except Exception as e:
            conn.send(f"-ERR Unexpected error: {str(e)}\n".encode('utf-8'))
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
