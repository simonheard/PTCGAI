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
    last_player_index = None

    print("=== PTCG AI Simulation ===")
    print("Type 'end' at any prompt to stop the game.\n")

    while True:
        current_index = turn % 2
        current = players[current_index]
        opponent = players[(turn + 1) % 2]

        print(f"\n--- {current.name}'s turn ({current.order}) ---")

        # Draw Phase only when the player actually changes
        if current_index != last_player_index:
            draw_input = input("Draw a card (enter card name)> ").strip()
            if draw_input.lower() == "end":
                print("Game ended by user.")
                break
            logger.log(current.name, "USER_INPUT", f"Drew card: {draw_input}")
            current.pending_draw = draw_input
            last_player_index = current_index

        # 1) Build & log the prompt (includes deck, memory, last decisions,
        #    any pending_draw, pending_user_input, and opponent_public_info)
        prompt = current.build_prompt()
        logger.log(current.name, "PROMPT", prompt)

        # 2) Send to AI and get JSON, using the exact prompt we just logged
        try:
            data = current.take_turn(prompt)
        except Exception as e:
            error_msg = f"AI turn failed for {current.name}: {e}"
            print(f"ERROR during AI turn: {e}")
            logger.log(current.name, "ERROR", error_msg)
            break

        # 3) Log the raw JSON
        logger.log(current.name, "RESPONSE", json.dumps(data, indent=2))

        # 4) Coerce memory into a plain string, then replace it wholesale
        raw_mem = data.get("memory", "")
        if not isinstance(raw_mem, str):
            raw_mem = json.dumps(raw_mem)
        current.memory = raw_mem

        # 4.1) Append any optional extra notes the AI wants to memorize
        extra = data.get("to_memorize")
        if extra:
            if not isinstance(extra, str):
                extra = json.dumps(extra)
            current.memory += "\n" + extra

        # 4.2) Remember what you just decided, explicitly
        current.last_decisions = data.get("decisions", "")

        # 5) Show decisions
        print(f"Decisions:\n{current.last_decisions}")

        # 6) Handle any random‐event requests
        if "user_input_request" in data:
            req = data["user_input_request"]
            print(f"\n>> {current.name} requests input: {req}")
            user_in = input("Your response> ").strip()
            if user_in.lower() == "end":
                print("Game ended by user.")
                break
            logger.log(current.name, "USER_INPUT", f"{req} -> {user_in}")
            current.memory += f"\n[User input: {user_in}]"

        # 7) Free-form CLI note for next AI prompt (not memory)
        cont = input("\nPress Enter to continue, or type a note to include in AI prompt> ").strip()
        if cont.lower() == "end":
            print("Game ended by user.")
            break
        elif cont:
            logger.log(current.name, "USER_INPUT", f"[Pending note] {cont}")
            current.pending_user_input = cont

        # 8) Pass any public_info to opponent
        public = data.get("public_info")
        if public:
            opponent.opponent_public_info = public

        # 9) End‐Turn Confirmation
        if data.get("end_turn"):
            confirm = input("\nAI wants to end its turn. Confirm end turn? (yes/no)> ").strip().lower()
            if confirm == "yes":
                turn += 1
            else:
                correction = "Please continue your turn; I think you ended prematurely."
                logger.log(current.name, "USER_INPUT", f"[Correction] {correction}")
                current.pending_user_input = correction
        # if end_turn was false, we stay on the same player

if __name__ == "__main__":
    main()
