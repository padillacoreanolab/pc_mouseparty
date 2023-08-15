"""Top-level package for pc_mouseparty."""

__author__ = """Christopher Marais"""
__email__ = 'padillacoreanolab@gmail.com'
__version__ = '0.0.26'

import pkgutil

__all__ = []

for finder, name, ispkg in pkgutil.walk_packages(__path__):
    if ispkg:
        __all__.append(name)
        import_module = f'.{name}'
    else:
        import_module = f'.{name}'
        __all__.append(name.split('.')[0])

    try:
        globals()[name] = __import__(import_module, globals(), locals(), [], 0)
    except ModuleNotFoundError:
        pass
