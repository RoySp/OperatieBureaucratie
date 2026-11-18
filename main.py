"""Operatie Bureaucratie - De weg naar het juiste loket.

Start het spel met:  python main.py
"""
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from game.engine import main  # noqa: E402

if __name__ == "__main__":
    main()
