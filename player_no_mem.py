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

        # state for prompt building
        self.pending_draw = ""
        self.pending_user_input = ""
        self.pending_new_turn = False
        self.last_decisions = ""
        self.opponent_public_info = ""
        self.board_state = {}

        # **capped memory**: list of last 5 entries
        self.memory_entries = []

        # prompt templates
        self.system_prompt = (
            "You are simulating a game of the Pokémon Trading Card Game (PTCG) via text. "
            f"You are acting as {self.name}, not as a judge—you play like a real player.\n\n"
            f"Initial game setup:\n{initial_setup}\n\n"
            "# Decklist (for reference; you must only use cards from your hand):\n"
            f"{deck}\n\n"
            f"You will play {order} as {self.name}.\n\n"
            "When you respond, output exactly ONE JSON object with these keys:\n"
            "  • \"memory\": \"<what you should remember now>\"\n"
            "  • \"decisions\": \"<what you will do now>\"\n"
            "  • \"public_info\": \"<public game state for Player1 and Player2>\"\n"
            "  • \"end_turn\": true or false\n"
            "Optionally include:\n"
            "  • \"to_memorize\": \"<extra detail>\"\n"
            "  • \"user_input_request\": \"<what you need me to do>\"\n\n"
            "Now begin your move."
        )

        self.turn_instruction = (
            "Continue simulating as " + self.name + ", not a judge.\n\n"
            "When you respond, output exactly one JSON object with keys:\n"
            "  • \"memory\"\n"
            "  • \"decisions\"\n"
            "  • \"public_info\"\n"
            "  • \"end_turn\"\n"
            "Optionally:\n"
            "  • \"to_memorize\"\n"
            "  • \"user_input_request\"\n\n"
            "Then continue."
        )

        self.first_prompt = True

    def add_memory(self, entry: str):
        """Append a memory entry and keep only the last 5."""
        text = entry if isinstance(entry, str) else json.dumps(entry)
        self.memory_entries.append(text.strip())
        # cap to last 5
        self.memory_entries = self.memory_entries[-5:]

    def build_prompt(self) -> str:
        parts = []

        # 1) new-turn header
        if self.pending_new_turn:
            parts.append("[New Turn]")
            self.pending_new_turn = False

        # 2) choose system vs. turn
        if self.first_prompt:
            parts.append(self.system_prompt)
            self.first_prompt = False
        else:
            parts.append(self.turn_instruction)

        # 3) board state
        if self.board_state:
            parts.append(f"[Board state: {json.dumps(self.board_state)}]")

        # 4) drawn card
        if self.pending_draw:
            parts.append(f"[Drawn card: {self.pending_draw}]")
            self.pending_draw = ""

        # 5) recent memory (last 5)
        if self.memory_entries:
            mem_block = "\n".join(self.memory_entries)
            parts.append("Previously remembered:\n" + mem_block)

        # 6) last decisions
        if self.last_decisions:
            parts.append(f"[Last decisions: {self.last_decisions}]")

        # 7) opponent public info
        if self.opponent_public_info:
            parts.append(f"[Public info: {self.opponent_public_info}]")
            self.opponent_public_info = ""

        # 8) user notes / corrections
        if self.pending_user_input:
            parts.append(f"[User note: {self.pending_user_input}]")
            self.pending_user_input = ""

        return "\n\n".join(parts)

    def take_turn(self, prompt: str) -> dict:
        def strip_fences(s: str) -> str:
            if s.startswith("```"):
                lines = s.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                return "\n".join(lines)
            return s

        current_prompt = prompt
        last_error = None
        last_content = None

        for attempt in range(1, self.max_retries+1):
            resp = openai.chat.completions.create(
                model="o3-mini",
                messages=[{"role":"user","content":current_prompt}],
                temperature=1
            )
            raw = resp.choices[0].message.content
            clean = strip_fences(raw.strip())
            last_content = raw

            try:
                data = json.loads(clean)
                if not all(k in data for k in ("memory","decisions","public_info","end_turn")):
                    raise KeyError("Missing required keys")
                return data

            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                if attempt < self.max_retries:
                    current_prompt += (
                        "\n\n⚠️ Invalid response. Reply with keys "
                        "\"memory\", \"decisions\", \"public_info\", \"end_turn\"."
                    )
                    continue

                raise ValueError(
                    f"{self.name} failed after {self.max_retries} attempts. "
                    f"Error: {last_error}. Last content: {last_content!r}"
                )
