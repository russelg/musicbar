import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

if __name__ == "__main__":
    from musicbar import menubar

    menubar.main()
