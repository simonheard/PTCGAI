# config.py

import os
from dotenv import load_dotenv
load_dotenv()

# Load your OpenAI API key from the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set the OPENAI_API_KEY environment variable")

DECKS = {
    "Player1": """
Pokemon - 22
4 Blitzle VIV 53
1 Boltund SSH 76
3 Luxio FST 92
2 Luxray FST 93
1 Morpeko FST 109
1 Pikachu V VIV 43
4 Shinx FST 91
2 Yamper SSH 74
3 Zebstrika VIV 54
1 Zeraora FST 102
Trainer - 20
1 Boss's Orders RCL 154
2 Bug Catcher FST 226
1 Energy Recycler BST 124
4 Great Ball SSH 164
4 Hop SSH 165
2 Potion SSH 177
3 Shauna FST 240
1 Sonia RCL 167
2 Switch SSH 183
Energy - 18
18 Lightning Energy 155
""",

    "Player2": """
Pokemon - 21
3 Centiskorch FST 49
1 Cinderace V FST 43
3 Larvesta CRE 23
2 Ninetales FST 30
4 Sizzlipede FST 46
1 Turtonator SSH 29
2 Victini CPA 7
2 Volcarona CRE 24
3 Vulpix FST 29
Trainer - 21
2 Bug Catcher FST 226
2 Energy Retrieval SSH 160
4 Great Ball SSH 164
4 Hop SSH 165
2 Pokémon Catcher SSH 175
1 Potion SSH 177
3 Shauna FST 240
1 Sonia RCL 167
2 Switch SSH 183
Energy - 18
18 Fire Energy 153
""",
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
    "Player1": "You have 4 prize cards. You hand is: Shinx, Shinx, Blitzle, Great Ball, Great Ball, Shauna, Basic L Energy.",
    "Player2": "You have 4 prize cards. You hand is: Larvesta, Vulpix, Hop, Sizzlipede, Shauna, Shauna, Basic F Energy.",
}
