# Redis Basics

## Building a simple Redis from scratch in Python

A lightweight Redis-like server built from scratch using Python's raw sockets. This project demonstrates how Redis works under the hood — TCP networking, an event loop, RESP protocol encoding, command routing, and in-memory key-value storage.

---

## Overall Mindmap

```
                            ┌──────────────┐
                            │   main.py    │
                            │  (Entry)     │
                            └──────┬───────┘
                                   │
                                   │ creates & starts
                                   ▼
                          ┌─────────────────┐
                          │  RedisServer    │
                          │  (server.py)    │
                          └────┬───────┬────┘
                               │       │
                 ┌─────────────┘       └──────────────┐
                 ▼                                     ▼
        ┌─────────────────┐                   ┌────────────────┐
        │  Event Loop     │                   │  Socket Layer  │
        │  (select.select)│                   │  (TCP/IP)      │
        └────────┬────────┘                   └────────────────┘
                 │
                 │ dispatches commands
                 ▼
        ┌─────────────────┐
        │ CommandHandler  │
        │ (command.py)    │
        └───┬─────────┬───┘
            │         │
            ▼         ▼
  ┌──────────────┐  ┌──────────────────┐
  │  DataStore   │  │  Response        │
  │ (storage.py) │  │  (response.py)   │
  │              │  │                  │
  │ In-memory    │  │ RESP Protocol    │
  │ dict { }     │  │ encoding         │
  └──────────────┘  └──────────────────┘

Flow:
  Client ──TCP──▶ Server ──select()──▶ _accept / _handle
       ──▶ _process_buffer ──▶ _process_command
       ──▶ CommandHandler.execute() ──▶ DataStore (read/write)
       ──▶ Response (format) ──▶ send back to Client
```

---

## Project Structure & File Responsibilities

```
redis-basics/
├── main.py                    # Entry point — creates and starts the server
└── redis_server/              # Core server package
    ├── __init__.py            # Package initializer — exports RedisServer
    ├── server.py              # TCP server, event loop, client management
    ├── command.py             # Command routing and business logic
    ├── response.py            # RESP protocol response formatters
    └── storage.py             # In-memory key-value data store
```

| File | Responsibility |
|---|---|
| `main.py` | Application entry point. Creates a `RedisServer` instance and starts it. Handles `Ctrl+C` for graceful shutdown. |
| `__init__.py` | Makes `redis_server/` a Python package. Re-exports `RedisServer` so callers can do `from redis_server import RedisServer`. |
| `server.py` | The heart of the application. Opens a TCP socket, runs a non-blocking event loop using `select`, accepts clients, reads data, buffers input, and dispatches parsed commands to the `CommandHandler`. |
| `command.py` | Command routing layer. Maps command names (PING, SET, GET, etc.) to handler methods. Each method validates arguments, interacts with `DataStore`, and returns a RESP-formatted response. |
| `response.py` | Pure formatting functions. Encodes Python values into the Redis Serialization Protocol (RESP) — simple strings, bulk strings, integers, arrays, and errors. |
| `storage.py` | The data layer. A thin wrapper around a Python `dict` providing Redis-like operations: `set`, `get`, `delete`, `exists`, `keys`, `values`, `flushall`. |

---

## Line-by-Line Code Explanation

### 1. `main.py` — Entry Point

```python
from redis_server import RedisServer          # Import RedisServer from the package
```
> Imports the `RedisServer` class. Thanks to `__init__.py`, we import directly from the package name.

```python
def main():
    server = RedisServer()                    # Create server instance (defaults: localhost:6379)
    try:
        server.start()                        # Start listening and enter the event loop
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()                         # Gracefully close all connections and the socket
```
> `try/except KeyboardInterrupt` ensures that pressing `Ctrl+C` triggers a clean shutdown instead of a crash.

```python
if __name__ == "__main__":
    main()                                    # Only run when executed directly, not when imported
```
> The standard Python idiom to make a file both importable and executable.

---

### 2. `redis_server/__init__.py` — Package Initializer

```python
from .server import RedisServer               # Relative import from server.py in the same package

__all__ = ['RedisServer']                     # Controls what `from redis_server import *` exports
```
> `__all__` is a list that explicitly declares the public API of the package. Without it, `import *` would pull in everything.

---

### 3. `redis_server/server.py` — TCP Server & Event Loop

#### Constructor

```python
import socket                                 # Python's low-level networking interface
import select                                 # I/O multiplexing — monitors multiple sockets at once
from .storage import DataStore                # Import the in-memory data store
from .command import CommandHandler           # Import the command routing layer
```

```python
class RedisServer:
    def __init__(self, host='localhost', port=6379):
        self.host = host                      # Bind address (localhost = local only)
        self.port = port                      # Port 6379 is the default Redis port
        self.running = False                  # Flag to control the event loop
        self.server_socket = socket.socket(   # Create a TCP socket
            socket.AF_INET,                   #   AF_INET = IPv4 addressing
            socket.SOCK_STREAM               #   SOCK_STREAM = TCP (reliable, ordered)
        )
        self.clients = {}                     # Dict mapping client sockets → their metadata
        self.storage = DataStore()            # Create the in-memory key-value store
        self.command_handler = CommandHandler(self.storage)  # Wire up command handler to storage
```

#### Starting the Server

```python
    def start(self):
        self.server_socket.setsockopt(        # Set socket options
            socket.SOL_SOCKET,                #   SOL_SOCKET = socket-level option
            socket.SO_REUSEADDR, 1            #   SO_REUSEADDR = allow reuse of address after restart
        )
        self.server_socket.bind((self.host, self.port))  # Bind socket to host:port
        self.server_socket.listen()           # Start listening for connections
        self.server_socket.setblocking(False) # Make socket non-blocking (won't freeze on accept/recv)
        self.running = True

        print(f"Redis server started on {self.host}:{self.port}")
        self._event_loop()                    # Enter the main loop
```
> `SO_REUSEADDR` is important — without it, restarting the server quickly after stopping would fail with "Address already in use".
> `setblocking(False)` makes every socket operation return immediately instead of waiting, which is required for the `select`-based event loop.

#### The Event Loop

```python
    def _event_loop(self):
        while self.running:
            try:
                read, _, _ = select.select(   # Wait for any socket to become readable
                    [self.server_socket] + list(self.clients.keys()),  # Watch: server + all clients
                    [],                       # We're not watching for writable sockets
                    [],                       # We're not watching for error conditions
                    1                         # Timeout: 1 second (allows checking self.running)
                )

                for sock in read:             # Iterate over sockets that have data
                    if sock is self.server_socket:
                        self._accept_client() # Server socket readable = new connection incoming
                    else:
                        self._handle_client(sock)  # Client socket readable = data from client
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in event loop: {e}")
```
> `select.select()` is the core I/O multiplexing call. It blocks (up to the timeout) until at least one socket in the watch list has data to read. This is how the server handles multiple clients **without threads** — it checks all sockets in a single loop.

#### Accepting a Client

```python
    def _accept_client(self):
        try:
            client, addr = self.server_socket.accept()  # Accept the pending connection
        except BlockingIOError:               # Race condition: connection withdrew before accept
            return
        client.setblocking(False)             # Make client socket non-blocking too
        self.clients[client] = {              # Store client metadata
            'addr': addr,                     #   Address tuple (ip, port)
            'buffer': b''                     #   Byte buffer for incomplete data
        }
        client.send(b"+WELCOME to Redis Server\r\n")  # Send a RESP-formatted welcome
```
> Each client gets its own entry in `self.clients` with a **buffer**. Since TCP is a stream protocol, a single `recv()` might return half a command or multiple commands. The buffer accumulates bytes until a complete command (ending with `\r\n`) is found.

#### Handling Client Data

```python
    def _handle_client(self, client):
        try:
            data = client.recv(4096)          # Read up to 4096 bytes from the client
            if not data:                      # Empty data = client closed connection
                self._disconnect_client(client)
                return
            self.clients[client]['buffer'] += data     # Append to the client's buffer
            self._process_buffer(client)               # Try to extract complete commands
        except ConnectionResetError:          # Client crashed / forcefully disconnected
            self._disconnect_client(client)
```

#### Processing the Buffer

```python
    def _process_buffer(self, client):
        buffer = self.clients[client]["buffer"]

        while b"\r\n" in buffer:              # Loop while there are complete commands
            command, buffer = buffer.split(b"\r\n", 1)  # Split at first \r\n
            if command:                       # Ignore empty lines
                response = self._process_command(command.decode().strip())
                client.send(response)         # Send response back to client
        self.clients[client]["buffer"] = buffer  # Save any remaining incomplete data
```
> This handles the **message framing** problem. TCP delivers a continuous stream of bytes, so we need to split it into individual commands using `\r\n` as the delimiter.

#### Parsing & Dispatching a Command

```python
    def _process_command(self, command_line):
        parts = command_line.strip().split()  # Split "SET key value" → ["SET", "key", "value"]
        if not parts:
            return select.error("Empty command")
        command_name = parts[0].upper()       # First word is the command (case-insensitive)
        args = parts[1:]                      # Remaining words are arguments
        return self.command_handler.execute(command_name, *args)  # Route to handler
```

#### Cleanup

```python
    def _disconnect_client(self, client):
        client.close()                        # Close the TCP connection
        self.clients.pop(client, None)        # Remove from the clients dict

    def stop(self):
        self.running = False                  # Signal the event loop to stop
        for client in list(self.clients.keys()):
            self._disconnect_client(client)   # Close all client connections
        if self.server_socket:
            self.server_socket.close()        # Close the server socket
```

---

### 4. `redis_server/command.py` — Command Router & Logic

#### Setup

```python
from .storage import DataStore
from .response import *                       # Import all RESP formatting functions

class CommandHandler:
    def __init__(self, storage: DataStore):
        self.storage = storage                # Reference to the shared data store
        self.commands = {                     # Command dispatch table: name → method
            "PING": self.ping,
            "ECHO": self.echo,
            "SET": self.set,
            "GET": self.get,
            "DEL": self.delete,
            "EXISTS": self.exists,
            "KEYS": self.keys,
            "VALUES": self.values,
            "FLUSHALL": self.flushall,
            "INFO": self.info,
        }
```
> The **command dispatch table** maps command strings to methods. This pattern avoids long if/elif chains and makes adding new commands trivial — just add a new entry and method.

#### Execute (Router)

```python
    def execute(self, command, *args):
        cmd = self.commands.get(command.upper())  # Look up the command method
        if cmd:
            return cmd(*args)                 # Call the method with the arguments
        return error(f"Unknown command '{command}'")  # Return RESP error if not found
```

#### Command Methods

```python
    def ping(self, *args):
        if args:
            return bulk_string(args[0])       # PING with arg → echo the arg back
        return pong()                         # PING alone → PONG

    def echo(self, *args):
        return simple_string(" ".join(args)) if args else simple_string("")

    def set(self, *args):
        if len(args) < 2:
            return error("wrong number of arguments for 'set' command")
        self.storage.set(args[0], " ".join(args[1:]))  # key = args[0], value = rest joined
        return ok()                           # Redis SET always returns OK

    def get(self, *args):
        if len(args) != 1:
            return error("GET command requires 1 argument")
        value = self.storage.get(args[0])     # Look up key in store
        return bulk_string(value)             # Returns the value, or null if key doesn't exist

    def delete(self, *args):
        if not args:
            return error("DEL command requires at least 1 argument")
        deleted_count = self.storage.delete(*args)  # Delete one or more keys
        return integer(deleted_count)         # Return how many were actually deleted

    def exists(self, *args):
        if not args:
            return error("EXISTS command requires at least 1 argument")
        exists_count = self.storage.exists_count(*args)  # Count how many keys exist
        return integer(exists_count)

    def keys(self, *args):
        keys = self.storage.keys()            # Get all keys from the store
        if not keys:
            return array([])                  # Empty array if no keys
        items = [bulk_string(key) for key in keys]  # Format each key as a bulk string
        return array(items)                   # Wrap in RESP array

    def values(self, *args):
        values = self.storage.values()
        if not values:
            return array([])
        items = [bulk_string(value) for value in values]
        return array(items)

    def flushall(self, *args):
        self.storage.flushall()               # Clear all data
        return ok()

    def info(self, *args):
        info = {                              # Build server info sections
            "server": {
                "redis_version": "1.0.0-custom",
                "redis_mode": "standalone"
            },
            "stats": {
                "total_commands_processed": 0
            },
            "keyspace": {
                "db0": f"keys={len(self.storage.keys())},expires=0"
            }
        }
        sections = []
        for section, data in info.items():
            sections.append(f"#{section}")            # Section header like #server
            sections.extend(f"{k}:{v}" for k, v in data.items())  # key:value pairs
        return bulk_string("\n".join(sections))
```

---

### 5. `redis_server/response.py` — RESP Protocol Encoding

```python
def ok():
    return b"+OK\r\n"                         # Simple string: success acknowledgment
```
> RESP Simple Strings start with `+` followed by the string and `\r\n`.

```python
def pong():
    return b"+PONG\r\n"                       # Simple string: PING response
```

```python
def null_bulk_string():
    return b"$-1\r\n"                         # Null bulk string: represents "key not found"
```
> `$-1` is RESP's way of saying "null" — used when a GET finds no value.

```python
def simple_string(value):
    return f"+{value}\r\n".encode()           # Encode a Python string as RESP simple string
```

```python
def bulk_string(value):
    if value is None:
        return null_bulk_string()             # None → null response
    return f"${len(value)}\r\n{value}\r\n".encode()  # $<length>\r\n<data>\r\n
```
> Bulk strings include the byte length before the content. This allows the parser to know exactly how many bytes to read, even if the content contains `\r\n`.

```python
def error(message):
    return f"-ERR {message}\r\n".encode()     # RESP errors start with -ERR
```

```python
def integer(value):
    return f":{value}\r\n".encode()           # RESP integers start with :
```

```python
def array(items):
    if not items:
        return b"*0\r\n"                      # Empty array
    result = [f"*{len(items)}\r\n".encode()]  # Array header: *<count>\r\n
    result.extend(items)                      # Append each pre-encoded item
    return b"".join(result)                   # Join all bytes
```
> RESP Arrays start with `*<count>` followed by each element. Elements are already encoded (as bulk strings, integers, etc.), so we just concatenate them.

---

### 6. `redis_server/storage.py` — In-Memory Data Store

```python
class DataStore:
    def __init__(self):
        self._data = {}                       # Private dict holding all key-value pairs
```
> The underscore prefix `_data` is a Python convention meaning "private — don't access directly from outside".

```python
    def set(self, key, value):
        self._data[key] = value               # Insert or overwrite a key

    def get(self, key):
        return self._data.get(key)            # Return value or None if key doesn't exist

    def delete(self, *keys):
        deleted_count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]           # Remove key if it exists
                deleted_count += 1
        return deleted_count                  # Return number of keys actually deleted

    def exists(self, *keys):
        return all(key in self._data for key in keys)  # True only if ALL keys exist

    def exists_count(self, *keys):
        return sum(1 for key in keys if key in self._data)  # Count how many keys exist

    def keys(self):
        return list(self._data.keys())        # Return all keys as a list

    def values(self):
        return list(self._data.values())      # Return all values as a list

    def flushall(self):
        self._data.clear()                    # Remove everything
```

---

## Available Commands

| Command | Arguments | Description | Example |
|---|---|---|---|
| `PING` | `[message]` | Connectivity check. Returns `PONG` or echoes the message. | `PING` / `PING hello` |
| `ECHO` | `<message>` | Returns the message back to the client. | `ECHO Hello World` |
| `SET` | `<key> <value>` | Stores a key-value pair in memory. | `SET name Redis` |
| `GET` | `<key>` | Retrieves the value for a key. Returns null if not found. | `GET name` |
| `DEL` | `<key> [key...]` | Deletes one or more keys. Returns the count of deleted keys. | `DEL name` |
| `EXISTS` | `<key> [key...]` | Returns how many of the given keys exist. | `EXISTS name` |
| `KEYS` | none | Returns all keys in the store. | `KEYS` |
| `VALUES` | none | Returns all values in the store. | `VALUES` |
| `FLUSHALL` | none | Deletes all keys and values. | `FLUSHALL` |
| `INFO` | none | Returns server information (version, mode, keyspace stats). | `INFO` |

---

## Setup & Running

**Prerequisites:** Python 3.x

**Start the server:**
```bash
python main.py
```

**Connect a client** (using `nc`, `telnet`, or `redis-cli`):
```bash
# Using netcat
nc localhost 6379

# Using redis-cli (if installed)
redis-cli
```

**Example session:**
```
+WELCOME to Redis Server
SET name Redis
+OK
GET name
$5
Redis
PING
+PONG
DEL name
:1
GET name
$-1
```

---

## Key Terminology & Concepts

### Networking

| Term | What It Means |
|---|---|
| **TCP (Transmission Control Protocol)** | A reliable, ordered protocol for sending data between two machines. Unlike UDP, TCP guarantees delivery and order. |
| **Socket** | An endpoint for network communication. Think of it as a "phone line" between two programs. `socket.socket()` creates one. |
| **AF_INET** | Address Family for IPv4. Tells the socket to use IPv4 addresses like `127.0.0.1`. |
| **SOCK_STREAM** | Socket type for TCP. Provides a reliable byte stream (as opposed to `SOCK_DGRAM` for UDP datagrams). |
| **bind()** | Associates a socket with a specific IP address and port number. |
| **listen()** | Puts the socket into server mode, ready to accept incoming connections. The backlog parameter sets how many pending connections can queue up. |
| **accept()** | Blocks (or returns immediately if non-blocking) until a client connects. Returns a new socket for that specific client and the client's address. |
| **recv(n)** | Reads up to `n` bytes from a connected socket. Returns empty bytes `b""` when the client disconnects. |
| **SO_REUSEADDR** | A socket option that allows the server to restart and bind to the same port immediately, without waiting for the OS to release it (which can take minutes). |

### I/O Multiplexing

| Term | What It Means |
|---|---|
| **select()** | A system call that monitors multiple sockets simultaneously. It tells you which sockets are ready to read/write, avoiding the need for one thread per client. |
| **Non-blocking I/O** | When `setblocking(False)` is set, socket operations return immediately instead of waiting. If no data is available, they raise `BlockingIOError` instead of freezing. |
| **Event Loop** | A loop that repeatedly checks for events (new connections, incoming data) and dispatches them to handlers. This is the same pattern used by Node.js, nginx, and Redis itself. |
| **I/O Multiplexing** | The technique of handling multiple I/O channels (sockets) in a single thread using `select`, `poll`, or `epoll`. More efficient than spawning a thread per client. |

### Redis Concepts

| Term | What It Means |
|---|---|
| **RESP (Redis Serialization Protocol)** | The wire protocol Redis uses to communicate. Simple text-based format with type prefixes: `+` (simple string), `-` (error), `:` (integer), `$` (bulk string), `*` (array). |
| **Key-Value Store** | A database that stores data as pairs of keys and values — like a Python dictionary. Redis is fundamentally a key-value store. |
| **In-Memory Storage** | Data is stored in RAM, not on disk. Extremely fast but lost when the server stops. Real Redis adds persistence options (RDB, AOF). |
| **Command Dispatch Table** | A dictionary mapping command names to handler functions. Avoids long if/elif chains and makes the system extensible. |
| **Null Bulk String (`$-1`)** | RESP's way of representing "no value" / null. Returned when you GET a key that doesn't exist. |
| **FLUSHALL** | Deletes every key in the database. A destructive command used for resetting state. |

### Python Concepts

| Term | What It Means |
|---|---|
| **`__init__.py`** | Makes a directory a Python package. Code here runs when the package is first imported. Used to re-export classes for a cleaner API. |
| **`__all__`** | A list that controls what gets exported when someone does `from package import *`. A way to define the public API. |
| **`__name__ == "__main__"`** | A guard that ensures code only runs when the file is executed directly (`python file.py`), not when it's imported by another file. |
| **`*args`** | Collects extra positional arguments into a tuple. Allows functions to accept a variable number of arguments. |
| **Relative Import (`from .module`)** | The dot `.` means "from the same package". `from .storage import DataStore` imports from `storage.py` in the same directory. |
| **Message Framing** | The problem of figuring out where one message ends and the next begins in a continuous TCP byte stream. Solved here by splitting on `\r\n`. |
| **Buffer** | A temporary storage area for accumulating incoming bytes until a complete message is received. Needed because TCP may deliver partial data. |

### Design Patterns

| Pattern | Where It's Used |
|---|---|
| **Separation of Concerns** | Each file has one job: `server.py` handles networking, `command.py` handles logic, `response.py` handles formatting, `storage.py` handles data. |
| **Command Pattern** | Commands are stored as objects (methods) in a dispatch table and executed dynamically based on input. |
| **Encapsulation** | `DataStore` wraps a raw `dict` with a controlled interface (`set`, `get`, `delete`). Internal state (`_data`) is kept private. |
| **Graceful Shutdown** | `Ctrl+C` triggers `KeyboardInterrupt`, which calls `stop()` to close all connections and the server socket cleanly instead of crashing. |
