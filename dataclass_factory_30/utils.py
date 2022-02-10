def _singleton_repr(self):
    return f"{type(self).__name__}()"


class SingletonMeta(type):
    def __new__(mcs, *args, **kwargs):
        cls = super().__new__(mcs, *args, **kwargs)

        if "__repr__" not in vars(cls):
            cls.__repr__ = _singleton_repr

        instance = super().__call__(cls)
        cls._instance = instance
        return cls

    def __call__(cls):
        return cls._instance
