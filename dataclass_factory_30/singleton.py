class SingletonMeta(type):
    def __new__(mcs, *args, **kwargs):
        cls = super().__new__(mcs, *args, **kwargs)
        instance = super().__call__(cls)
        cls._instance = instance
        return cls

    def __call__(cls):
        return cls._instance
