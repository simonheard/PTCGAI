# player.py

import openai
import json

class Player:
    def __init__(self, name: str, deck: str, order: str, initial_setup: str):
        self.name = name
        self.deck = deck
        self.order = order  # "first" or "second"
        self.initial_setup = initial_setup

        # how many times to retry JSON parsing before giving up
        self.max_retries = 3

        # stash any free-form CLI note here until next build_prompt()
        self.pending_user_input = ""
        # remember your last decisions to feed back next turn
        self.last_decisions = ""

        # Initial “master” prompt: simulation context + initial setup + baked-in JSON instructions
        self.system_prompt = (
            "You are simulating a game of the Pokémon Trading Card Game (PTCG) via text. "
            "You have full knowledge of your deck and the game state, but you play entirely by text.\n\n"
            f"Initial game setup:\n{initial_setup}\n\n"
            f"Your deck of cards is:\n{deck}\n\n"
            f"You will play {order}.\n"
            "Follow the official PTCG rules precisely. Whenever a random event occurs "
            "(like drawing or shuffling), pause and prompt the user for the exact result.\n\n"
            "When you respond, output exactly ONE JSON object with these keys:\n"
            "  • \"memory\": \"<the updated memory>\"\n"
            "  • \"decisions\": \"<what you will do now>\"\n"
            "Always include:\n"
            "  • \"end_turn\": true or false; true if you are ending your turn, false to take another action\n\n"
            "Your \"memory\" field must at minimum summarize:\n"
            "  1. Your current hand (which cards you hold).\n"
            "  2. Your Active Pokémon and its stats (HP, attached Energies, any Conditions).\n"
            "  3. Your Benched Pokémon and their stats.\n"
            "  4. The specific action you are taking this turn.\n\n"
            "If you require the user to resolve a random event, also include:\n"
            "  • \"user_input_request\": \"<exactly what you need me to do>\"\n\n"
            "Now begin your move by selecting your Active Pokémon."
        )

        # Instruction for all subsequent turns
        self.turn_instruction = (
            "Decide what information is critical to the game state, then output exactly ONE JSON object with these keys:\n"
            "  • \"memory\": \"<the updated memory>\"\n"
            "  • \"decisions\": \"<what you will do now>\"\n"
            "Always include:\n"
            "  • \"end_turn\": true or false; true if you are ending your turn, false to take another action\n\n"
            "Your \"memory\" field must at minimum summarize:\n"
            "  1. Your current hand (whenever you use a card, you should remove it from your hand, as it is 'used').\n"
            "  2. Your Active Pokémon and its stats (HP, attached Energies, any Conditions).\n"
            "  3. Your Benched Pokémon and their stats.\n"
            "  4. The specific action you are taking this turn.\n\n"
            "If you require the user to resolve a random event, also include:\n"
            "  • \"user_input_request\": \"<exactly what you need me to do>\"\n\n"
            "Then continue with your move."
        )

        # Accumulated “memory” text
        self.memory = ""

    def build_prompt(self) -> str:
        """
        First turn uses system_prompt; afterwards turn_instruction + deck + memory.
        Then, if you stored last_decisions or pending_user_input, append them (and clear).
        """
        # always remind it of the authoritative deck
        deck_block = f"Your deck of cards is:\n{self.deck}\n\n"

        if not self.memory:
            prompt = self.system_prompt
        else:
            prompt = (
                self.turn_instruction
                + "\n\n"
                + deck_block
                + "Previously remembered:\n"
                + self.memory
            )

        # Remind yourself what you did last turn
        if self.last_decisions:
            prompt += f"\n\n[Last decisions: {self.last_decisions}]"
            # keep it only once—you could clear here if desired

        # Inject any pending user note directly into the prompt
        if self.pending_user_input:
            prompt += f"\n\n[User note: {self.pending_user_input}]"
            # clear it so it only applies once
            self.pending_user_input = ""

        return prompt

    def take_turn(self, prompt: str) -> dict:
        """
        Sends the given prompt (as a user message), parses the JSON
        response, and returns it. Retries up to self.max_retries times
        if parsing or key‐validation fails.
        """
        current_prompt = prompt
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": current_prompt}],
                temperature=0.7
            )

            content = resp.choices[0].message.content.strip()

            try:
                data = json.loads(content)
                if (
                    "memory" not in data or
                    "decisions" not in data or
                    "end_turn" not in data
                ):
                    raise KeyError("Missing required keys")
                return data

            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                if attempt < self.max_retries:
                    # append the retry reminder to the same prompt
                    current_prompt += (
                        "\n\n⚠️ Your previous response was invalid. "
                        "Please reply with exactly one JSON object containing keys "
                        "\"memory\", \"decisions\", and \"end_turn\", "
                        "and optionally \"user_input_request\"."
                    )
                    continue

                # give up after too many tries
                raise ValueError(
                    f"{self.name} failed to return valid JSON after "
                    f"{self.max_retries} attempts. Last error: {last_error}"
                )
