import logging
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    from musicbar import menubar

    menubar.main()
