def pytest_make_parametrize_id(config, val, argname):
    try:
        return val.__name__
    except AttributeError:
        try:
            return val._name
        except AttributeError:
            return None
