class DataStore:
    def __init__(self):
        self._data = {}

    def set(self, key, value):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)

    def delete(self, *keys):
        deleted_count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                deleted_count += 1
        return deleted_count

    def exists(self, *keys):
        return all(key in self._data for key in keys)
    
    def exists_count(self, *keys):
        return sum(1 for key in keys if key in self._data)

    def keys(self):
        return list(self._data.keys())

    def values(self):
        return list(self._data.values())

    def flushall(self):
        self._data.clear()
