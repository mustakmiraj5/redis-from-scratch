# Redis Basics
## Building a simple redis from scratch in python

A lightweight TCP server built in Python that mimics basic Redis-like command handling. The server listens for client connections, processes commands, and returns responses — all using raw sockets and multi-threading.

---

## How It Works

The server is built around a single class `TCPServer` in `redis-server/tcp_server.py` with two core responsibilities:

1. **Server Setup (`__init__`)** — Creates a TCP socket, binds it to `localhost:6379` (the default Redis port), and starts listening for incoming connections with a backlog of 5.

2. **Client Handling (`handle_client`)** — Each client that connects is spawned into its own thread. The server sends a welcome message followed by a terminal-style prompt (`tcpserver@python$`). It then enters a loop, reading commands from the client, processing them, and sending back responses until the client sends `QUIT` or disconnects.

3. **Server Loop (`run`)** — Continuously accepts new connections and dispatches each one to a new thread via `threading.Thread`, allowing multiple clients to be served simultaneously.

---

## Setup & Running

**Prerequisites:** Python 3.x

**Start the server:**
```bash
python redis-server/tcp_server.py
```
The server will start listening on `localhost:6379`.

**Connect a client** (using `nc` or any TCP client):
```bash
nc localhost 6379
```

You will see:
```
Welcome to the TCP Server!
tcpserver@python$
```

---

## Available Commands

| Command | Description | Example |
|---|---|---|
| `PING` | Connectivity check, returns `PONG` | `PING` |
| `ECHO <message>` | Echoes the message back | `ECHO Hello` |
| `TIME` | Returns the current date and time | `TIME` |
| `DATE` | Returns the current date (`YYYY-MM-DD`) | `DATE` |
| `RANDOM` | Returns a random number between 0 and 100 | `RANDOM` |
| `UUID` | Generates and returns a new UUID | `UUID` |
| `REVERSE <message>` | Reverses the given message | `REVERSE hello` |
| `LEN <message>` | Returns the length of the message | `LEN hello` |
| `WORDS <message>` | Counts the number of words in the message | `WORDS hello world` |
| `HASH <message>` | Returns the SHA-256 hash of the message | `HASH hello` |
| `BASE64ENC <message>` | Encodes the message in Base64 | `BASE64ENC hello` |
| `BASE64DEC <message>` | Decodes a Base64 encoded message | `BASE64DEC aGVsbG8=` |
| `URLENC <message>` | URL-encodes the message | `URLENC hello world` |
| `URLDEC <message>` | Decodes a URL-encoded message | `URLDEC hello%20world` |
| `HELP` | Lists all available commands | `HELP` |
| `QUIT` | Closes the connection | `QUIT` |

---

## Example Session

```
Welcome to the TCP Server!
tcpserver@python$ PING
-> PONG
tcpserver@python$ ECHO Hello World
-> Hello World
tcpserver@python$ REVERSE redis
-> sider
tcpserver@python$ HASH hello
-> 2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824
tcpserver@python$ HELP
-> Available commands:
   - PING
   - ECHO <message>
   - TIME
   - DATE
   - RANDOM
   - UUID
   - REVERSE <message>
   - LEN <message>
   - WORDS <message>
   - HASH <message>
   - BASE64ENC <message>
   - BASE64DEC <message>
   - URLENC <message>
   - URLDEC <message>
   - HELP
   - QUIT
tcpserver@python$ QUIT
-> Goodbye!
```

---

## Project Structure

```
redis-basics/
├── README.md                  # Project documentation
└── redis-server/
    └── tcp_server.py          # TCP server implementation
```
