import openai
import sys
from config import OPENAI_API_KEY, DECKS, ORDER, LOG_DIR
from logger import Logger
from player import Player

def main():
    openai.api_key = OPENAI_API_KEY
    logger = Logger(LOG_DIR)

    # Initialize players
    players = []
    for name, order in ORDER:
        deck = DECKS.get(name)
        if deck is None:
            print(f"ERROR: No deck found for {name} in config.DECKS")
            sys.exit(1)
        players.append(Player(name, deck, order))

    turn = 0
    print("=== PTCG AI Simulation ===")
    print("Type 'end' at any prompt to stop the game.\n")

    while True:
        current = players[turn % 2]
        print(f"\n--- {current.name}'s turn ({current.order}) ---")

        # 1) send prompt, log it
        prompt = current.build_prompt()
        logger.log(current.name, "PROMPT", prompt)

        # 2) get JSON response
        try:
            data = current.take_turn()
        except Exception as e:
            print("ERROR during AI turn:", e)
            break

        # 3) log raw JSON
        logger.log(current.name, "RESPONSE", json.dumps(data, indent=2))

        # 4) update memory
        current.memory = (
            data["remember"] if not current.memory
            else current.memory + "\n" + data["remember"]
        )

        # 5) show decisions
        print(f"Decisions:\n{data['decisions']}")

        # 6) if AI asked for user input, handle it
        if "user_input_request" in data:
            req = data["user_input_request"]
            print(f"\n>> {current.name} requests input: {req}")
            user_in = input("Your response> ").strip()
            if user_in.lower() == "end":
                print("Game ended by user.")
                break
            logger.log(current.name, "USER_INPUT", req + "\n-> " + user_in)
            # feed that back into memory so next turn includes it
            current.memory += f"\n[User input: {user_in}]"

        # 7) check if user wants to quit
        cont = input("\nPress Enter to continue, or type 'end' to stop> ").strip()
        if cont.lower() == "end":
            print("Game ended by user.")
            break

        turn += 1

if __name__ == "__main__":
    main()
