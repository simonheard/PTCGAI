# config.py

import os
from dotenv import load_dotenv
load_dotenv()

# Load your OpenAI API key from the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

# Replace the strings below with your actual deck lists
DECKS = {
    "Player1": "<YOUR DECK LIST FOR PLAYER 1 HERE>",
    "Player2": "<YOUR DECK LIST FOR PLAYER 2 HERE>",
}

# Define play order: ("PlayerName", "first" or "second")
ORDER = [
    ("Player1", "first"),
    ("Player2", "second"),
]

# Where logs will be written
LOG_DIR = "logs"

# Per-player initial setups: what each player knows at game start.
# Player1 and Player2 each get only their own hand, prizes, active/bench, etc.
INITIAL_SETUPS = {
    "Player1": "<YOUR INITIAL SETUP FOR PLAYER 1 HERE>",
    "Player2": "<YOUR INITIAL SETUP FOR PLAYER 2 HERE>",
}
