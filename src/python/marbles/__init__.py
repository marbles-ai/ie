import os

PROJDIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
USE_DEVEL_PATH = os.path.exists(os.path.join(PROJDIR, 'src', 'python', 'marbles'))

