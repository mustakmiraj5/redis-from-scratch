from .storage import DataStore
from .response import *

class CommandHandler:
    def __init__(self, storage: DataStore):
        self.storage = storage
        self.commands = {
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

    def execute(self, command, *args):
        cmd = self.commands.get(command.upper())
        if cmd:
            return cmd(*args)
        return error(f"Unknown command '{command}'")
    
    def ping(self, *args):
        if args:
            return bulk_string(args[0])
        return pong()
    
    def echo(self, *args):
        return simple_string(" ".join(args)) if args else simple_string("")
    
    def set(self, *args):
        if len(args) != 2:
            return error("SET command requires 2 arguments")
        key, value = args
        self.storage.set(key, value)
        return ok()
    
    def get(self, *args):
        if len(args) != 1:
            return error("GET command requires 1 argument")
        key = args[0]
        value = self.storage.get(key)
        return bulk_string(value)
    
    def delete(self, *args):
        if not args:
            return error("DEL command requires at least 1 argument")
        deleted_count = self.storage.delete(*args)
        return integer(deleted_count)
    
    def exists(self, *args):
        if not args:
            return error("EXISTS command requires at least 1 argument")
        exists_count = self.storage.exists_count(*args)
        return integer(exists_count)
    
    def keys(self, *args):
        keys = self.storage.keys()
        if not keys:
            return array([])
        items = [bulk_string(key) for key in keys]
        return array(items)
    
    def values(self, *args):
        values = self.storage.values()
        if not values:
            return array([])
        items = [bulk_string(value) for value in values]
        return array(items)
    
    def flushall(self, *args):
        self.storage.flushall()
        return ok()
    
    def info(self, *args):
        info = {
            "server": {
                "redis_version": "1.0.0-custom",
                "redis_mode": "standalone"
            },
            "stats": {
                "total_commands_processed": 0  # Would track this in server
            },
            "keyspace": {
                "db0": f"keys={len(self.storage.keys())},expires=0"
            }
        }
        sections = []
        for section, data in info.items():
            sections.append(f"#{section}")
            sections.extend(f"{k}:{v}" for k, v in data.items())
        return bulk_string("\n".join(sections))
