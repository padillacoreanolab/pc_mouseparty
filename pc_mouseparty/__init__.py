"""Top-level package for pc_mouseparty."""

__author__ = """Christopher Marais"""
__email__ = 'padillacoreanolab@gmail.com'
__version__ = '0.0.21'

# import os
# import glob

# modules = []
# for root, dirs, files in os.walk(os.path.dirname(__file__)):
#     for file in files:
#         if file.endswith('.py'):
#             modules.append(os.path.join(root, file))

# __all__ = [os.path.basename(f)[:-3] for f in modules if os.path.isfile(f) and not f.endswith('__init__.py')]

# for module in __all__:
#     exec(f"from .{module} import *")

import os
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