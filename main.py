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

    # 1) Initialize players
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
        p = Player(name, deck, order, initial_setup)
        p.board_state = {}            # shared board info
        p.pending_new_turn = False    # track new-turn notice
        players.append(p)

    # mark Player1 as starting a new turn
    players[0].pending_new_turn = True

    turn = 0
    last_player_index = None

    print("=== PTCG AI Simulation ===")
    print("Type 'end' at any prompt to stop the game.\n")

    while True:
        current_index = turn % 2
        current = players[current_index]
        opponent = players[(turn + 1) % 2]

        print(f"\n--- {current.name}'s turn ({current.order}) ---")

        # 2) Draw Phase: only when we switch players
        if current_index != last_player_index:
            draw_input = input("Draw a card (enter card name)> ").strip()
            if draw_input.lower() == "end":
                print("Game ended by user.")
                break
            logger.log(current.name, "USER_INPUT", f"Drew card: {draw_input}")
            current.pending_draw = draw_input
            last_player_index = current_index

        # 3) Build & log the prompt
        prompt = current.build_prompt()
        logger.log(current.name, "PROMPT", prompt)

        # 4) Send to AI
        try:
            data = current.take_turn(prompt)
        except Exception as e:
            error_msg = f"AI turn failed for {current.name}: {e}"
            print(f"ERROR during AI turn: {e}")
            logger.log(current.name, "ERROR", error_msg)
            break

        # 5) Log the raw JSON
        logger.log(current.name, "RESPONSE", json.dumps(data, indent=2))

        # 6) Update private memory
        raw_mem = data.get("memory", "")
        current.memory = raw_mem if isinstance(raw_mem, str) else json.dumps(raw_mem)

        # 7) Optional extra notes
        extra = data.get("to_memorize")
        if extra:
            note = extra if isinstance(extra, str) else json.dumps(extra)
            current.memory += "\n" + note

        # 8) Record decisions
        current.last_decisions = data.get("decisions", "")

        print(f"Decisions:\n{current.last_decisions}")

        # 9) Handle any AI‐requested user input
        if "user_input_request" in data:
            req = data["user_input_request"]
            print(f"\n>> {current.name} requests input: {req}")
            user_in = input("Your response> ").strip()
            if user_in.lower() == "end":
                print("Game ended by user.")
                break
            logger.log(current.name, "USER_INPUT", f"{req} -> {user_in}")
            current.memory += f"\n[User input: {user_in}]"

        # 10) Free-form CLI note for next prompt
        cont = input("\nPress Enter to continue, or type a note to include in AI prompt> ").strip()
        if cont.lower() == "end":
            print("Game ended by user.")
            break
        elif cont:
            logger.log(current.name, "USER_INPUT", f"[Pending note] {cont}")
            current.pending_user_input = cont

        # 11) Update shared board_state for both players
        board = data.get("public_info")
        if board:
            for p in players:
                p.board_state = board

        # 12) End-Turn Confirmation
        if data.get("end_turn"):
            confirm = input("\nAI wants to end its turn. Confirm end turn? (yes/no)> ").strip().lower()
            if confirm == "yes":
                # next player's new turn
                turn += 1
                players[turn % 2].pending_new_turn = True
            else:
                correction = "Please continue your turn; I think you ended prematurely."
                logger.log(current.name, "USER_INPUT", f"[Correction] {correction}")
                current.pending_user_input = correction
        # if end_turn is false, we do not advance turn and will re-prompt the AI

if __name__ == "__main__":
    main()
