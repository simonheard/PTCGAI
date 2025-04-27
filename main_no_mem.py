# main_no_mem.py

import openai
import sys
import json
from config import OPENAI_API_KEY, DECKS, ORDER, LOG_DIR, INITIAL_SETUPS
from logger import Logger
from player_no_mem import Player

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
        players.append(p)

    # Mark that Player1 is starting
    players[0].pending_new_turn = True

    turn = 0
    last_player = None

    print("=== PTCG AI Simulation (No Memory; Limited History) ===")
    print("Type 'end' at any prompt to stop the game.\n")

    while True:
        idx = turn % 2
        current = players[idx]
        opponent = players[(turn + 1) % 2]

        print(f"\n--- {current.name}'s turn ({current.order}) ---")

        # 2) Draw + public info update on actual turn change
        if idx != last_player:
            draw = input("Draw a card (enter card name)> ").strip()
            if draw.lower()=="end":
                print("Game ended by user."); break
            logger.log(current.name, "USER_INPUT", f"Drew card: {draw}")
            current.pending_draw = draw

            pub = input("Enter updated public info as JSON> ").strip()
            if pub.lower()=="end":
                print("Game ended by user."); break
            try:
                board = json.loads(pub)
            except json.JSONDecodeError:
                board = pub
            logger.log(current.name, "USER_INPUT", f"Updated public_info: {pub}")
            for p in players:
                p.board_state = board

            last_player = idx

        # 3) Build our next user message
        user_msg = current.build_prompt()

        # 4) Log a HISTORY summary (roles of last 5 messages)
        hist = current.history[-11:]  # includes system + 10 last
        roles = [m["role"] for m in hist]
        logger.log(current.name, "HISTORY", ",".join(roles))

        # 5) Send user_msg to AI
        logger.log(current.name, "PROMPT", user_msg)
        try:
            data = current.take_turn(user_msg)
        except Exception as e:
            print(f"ERROR during AI turn: {e}")
            logger.log(current.name, "ERROR", str(e))
            break

        # 6) Log raw JSON
        logger.log(current.name, "RESPONSE", json.dumps(data, indent=2))

        # 7) Record the AI’s decisions
        current.last_decisions = data["decisions"]
        print(f"Decisions:\n{current.last_decisions}")

        # 8) User resolves any requests
        if "user_input_request" in data:
            req = data["user_input_request"]
            print(f"\n>> {current.name} requests input: {req}")
            res = input("Your response> ").strip()
            if res.lower()=="end":
                print("Game ended by user."); break
            logger.log(current.name, "USER_INPUT", f"{req} -> {res}")
            current.pending_user_input = res

        # 9) Free-form note
        note = input("\nPress Enter to continue, or type a note> ").strip()
        if note.lower()=="end":
            print("Game ended by user."); break
        if note:
            logger.log(current.name, "USER_INPUT", f"[Note] {note}")
            if current.pending_user_input:
                current.pending_user_input += "\n" + note
            else:
                current.pending_user_input = note

        # 10) Accept any updated public_info from AI
        if "public_info" in data:
            for p in players:
                p.board_state = data["public_info"]

        # 11) Confirm end_turn
        if data.get("end_turn"):
            c = input("\nAI wants to end turn. Confirm? (yes/no)> ").strip().lower()
            if c=="yes":
                turn += 1
                players[turn%2].pending_new_turn = True
            else:
                corr = "Please continue your turn; I think you ended prematurely."
                logger.log(current.name, "USER_INPUT", f"[Correction] {corr}")
                if current.pending_user_input:
                    current.pending_user_input += "\n" + corr
                else:
                    current.pending_user_input = corr

if __name__ == "__main__":
    main()
