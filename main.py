# main.py

import openai
import sys
import json
from config import OPENAI_API_KEY, DECKS, ORDER, LOG_DIR, INITIAL_SETUPS
from logger import Logger
from player import Player

def main():
    openai.api_key = OPENAI_API_KEY
    logger = Logger(LOG_DIR)

    # Initialize players, passing in each one's own INITIAL_SETUP
    players = []
    for name, order in ORDER:
        deck = DECKS.get(name)
        if deck is None:
            print(f"ERROR: No deck found for {name} in config.DECKS")
            sys.exit(1)
        initial_setup = INITIAL_SETUPS.get(name)
        if initial_setup is None:
            print(f"ERROR: No initial setup found for {name} in config.INITIAL_SETUPS")
            sys.exit(1)
        players.append(Player(name, deck, order, initial_setup))

    turn = 0
    print("=== PTCG AI Simulation ===")
    print("Type 'end' at any prompt to stop the game.\n")

    while True:
        current = players[turn % 2]
        print(f"\n--- {current.name}'s turn ({current.order}) ---")

        # 1) Build & log the prompt (this now includes any pending_user_input)
        prompt = current.build_prompt()
        logger.log(current.name, "PROMPT", prompt)

        # 2) Send to AI and get JSON, using the exact prompt we just logged
        try:
            data = current.take_turn(prompt)
        except Exception as e:
            print("ERROR during AI turn:", e)
            break

        # 3) Log the raw JSON
        logger.log(current.name, "RESPONSE", json.dumps(data, indent=2))

        # 4) Update memory with the AI’s “remember”
        if not current.memory:
            current.memory = data["remember"]
        else:
            current.memory += "\n" + data["remember"]

        # 5) Show decisions
        print(f"Decisions:\n{data['decisions']}")

        # 6) Handle any random‐event requests
        if "user_input_request" in data:
            req = data["user_input_request"]
            print(f"\n>> {current.name} requests input: {req}")
            user_in = input("Your response> ").strip()
            if user_in.lower() == "end":
                print("Game ended by user.")
                break
            logger.log(current.name, "USER_INPUT", f"{req} -> {user_in}")
            # This *is* memory, because it's AI-requested resolution
            current.memory += f"\n[User input: {user_in}]"

        # 7) Free-form CLI note for next AI prompt (not memory)
        cont = input("\nPress Enter to continue, or type a note to include in AI prompt> ").strip()
        if cont.lower() == "end":
            print("Game ended by user.")
            break
        elif cont:
            # stash it to be appended to the very next build_prompt()
            logger.log(current.name, "USER_INPUT", f"[Pending note] {cont}")
            current.pending_user_input = cont

        # 8) Advance turn only if AI signaled end_turn=True
        if data.get("end_turn"):
            turn += 1

if __name__ == "__main__":
    main()
