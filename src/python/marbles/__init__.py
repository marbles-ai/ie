import os

_projdir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
USE_DEVEL_PATH = os.path.exists(os.path.join(_projdir, 'src', 'python', 'marbles'))
