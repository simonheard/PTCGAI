# player.py

import openai
import json

class Player:
    def __init__(self, name: str, deck: str, order: str, initial_setup: str):
        self.name = name
        self.deck = deck
        self.order = order
        self.initial_setup = initial_setup

        self.max_retries = 3

        # dynamic state for prompt-building
        self.pending_draw = ""
        self.pending_user_input = ""
        self.pending_new_turn = False
        self.last_decisions = ""
        self.opponent_public_info = ""
        self.board_state = {}

        # private memory
        self.memory = ""

        self.system_prompt = (
            "You are simulating a game of the Pokémon Trading Card Game (PTCG) via text. "
            f"You are acting as {self.name}, not as a judge—you play like a real player.\n\n"
            f"Initial game setup:\n{initial_setup}\n\n"
            "# Decklist (for your reference; you must only use cards from your hand):\n"
            f"{deck}\n\n"
            f"You will play {order} as {self.name}.\n\n"
            "When you respond, output exactly ONE JSON object with these keys:\n"
            "  • \"memory\": \"<the updated private memory>\"\n"
            "  • \"decisions\": \"<what you will do now>\"\n"
            "  • \"public_info\": \"<public game state for Player1 and Player2: each player's Active Pokémon & stats, Benched Pokémon & stats, and prize cards remaining>\"\n"
            "  • \"end_turn\": true or false; true if you are ending your turn, false to take another action\n"
            "Optionally include:\n"
            "  • \"to_memorize\": \"<any extra details you think are important to remember>\"\n"
            "  • \"user_input_request\": \"<exactly what you need me to do>\"\n\n"
            "Your \"memory\" field must at minimum summarize:\n"
            "  1. Your current hand (which cards you hold), removing any cards you used.\n"
            "  2. Your Active Pokémon and its stats (HP, attached Energies, any Conditions).\n"
            "  3. Your Benched Pokémon and their stats.\n"
            "  4. The specific action you are taking this turn.\n\n"
            "You must only play cards that are currently in your hand—do not reference or use any other cards.\n\n"
            "Now begin your move by selecting your Active Pokémon."
        )

        self.turn_instruction = (
            "Continue simulating as " + self.name + ", not a judge.\n\n"
            "Decide what information is critical to the game state, then output exactly ONE JSON object with these keys:\n"
            "  • \"memory\": \"<the updated private memory>\"\n"
            "  • \"decisions\": \"<what you will do now>\"\n"
            "  • \"public_info\": \"<public game state for Player1 and Player2: each player's Active Pokémon & stats, Benched Pokémon & stats, and prize cards remaining>\"\n"
            "  • \"end_turn\": true or false; true if you are ending your turn, false to take another action\n"
            "Optionally include:\n"
            "  • \"to_memorize\": \"<any extra details you think are important to remember>\"\n"
            "  • \"user_input_request\": \"<exactly what you need me to do>\"\n\n"
            "Your \"memory\" field must at minimum summarize:\n"
            "  1. Your current hand (removing cards you used).\n"
            "  2. Your Active Pokémon and its stats (HP, attached Energies, any Conditions).\n"
            "  3. Your Benched Pokémon and their stats.\n"
            "  4. The specific action you are taking this turn.\n\n"
            "You must only play cards that are currently in your hand—do not reference or use any other cards.\n\n"
            "Then continue with your move."
        )

    def build_prompt(self) -> str:
        # 1) New-turn header
        header = ""
        if self.pending_new_turn:
            header = "[New Turn]\n\n"
            self.pending_new_turn = False

        # 2) Base prompt
        deck_block = f"# Decklist (for reference):\n{self.deck}\n\n"
        if not self.memory:
            base = self.system_prompt
        else:
            base = (
                f"{self.turn_instruction}\n\n"
                f"{deck_block}"
                f"Previously remembered:\n{self.memory}"
            )
        prompt = header + base

        # 3) Shared board state
        if self.board_state:
            prompt += f"\n\n[Board state: {json.dumps(self.board_state)}]"

        # 4) Drawn card
        if self.pending_draw:
            prompt += f"\n\n[Drawn card: {self.pending_draw}]"
            self.pending_draw = ""

        # 5) Last decisions
        if self.last_decisions:
            prompt += f"\n\n[Last decisions: {self.last_decisions}]"

        # 6) Opponent’s public info
        if self.opponent_public_info:
            prompt += f"\n\n[Public info: {self.opponent_public_info}]"
            self.opponent_public_info = ""

        # 7) All pending user notes + corrections
        if self.pending_user_input:
            prompt += f"\n\n[User note: {self.pending_user_input}]"
            self.pending_user_input = ""

        return prompt

    def take_turn(self, prompt: str) -> dict:
        def strip_fences(s: str) -> str:
            if s.startswith("```"):
                lines = s.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                return "\n".join(lines)
            return s

        last_error = None
        last_content = None
        current_prompt = prompt

        for attempt in range(1, self.max_retries + 1):
            resp = openai.chat.completions.create(
                model="o3-mini",
                messages=[{"role": "user", "content": current_prompt}],
                temperature=1
            )
            raw = resp.choices[0].message.content
            clean = strip_fences(raw.strip())
            last_content = raw

            try:
                data = json.loads(clean)
                if not all(k in data for k in ("memory","decisions","end_turn","public_info")):
                    raise KeyError("Missing one of (memory, decisions, end_turn, public_info)")
                return data

            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                if attempt < self.max_retries:
                    current_prompt += (
                        "\n\n⚠️ Your previous response was invalid. "
                        "Please reply with exactly one JSON object containing keys "
                        "\"memory\", \"decisions\", \"end_turn\", and \"public_info\", "
                        "and optionally \"to_memorize\", \"user_input_request\"."
                    )
                    continue

                raise ValueError(
                    f"{self.name} failed to return valid JSON after {self.max_retries} attempts. "
                    f"Last error: {last_error}. Last raw response: {last_content!r}"
                )
