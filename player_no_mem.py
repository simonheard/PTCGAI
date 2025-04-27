# player_no_mem.py

import openai, json

class Player:
    def __init__(self, name, deck, order, initial_setup):
        self.name = name
        self.deck = deck
        self.order = order
        self.initial_setup = initial_setup

        self.max_retries = 3

        # dynamic state
        self.history = []
        self.pending_draw = ""
        self.pending_user_input = ""
        self.pending_new_turn = False
        self.last_decisions = ""
        self.board_state = {}

        # seed system message
        self.system_prompt = (
            "You are simulating the Pokémon TCG as text. "
            f"You act as {self.name}, not a judge.\n"
            f"Initial setup: {initial_setup}\n"
            "# Decklist (only play cards in your hand):\n{deck}\n\n"
            "Respond with JSON keys:\n"
            " • \"decisions\": what you do now\n"
            " • \"public_info\": updated board for Player1/Player2\n"
            " • \"end_turn\": true/false\n"
            "Optionally:\n"
            " • \"user_input_request\"\n"
            " • \"to_memorize\"\n\n"
            "Begin."
        )
        self.history.append({"role":"system","content":self.system_prompt})
        self.first = True

    def build_prompt(self):
        pieces = []
        if self.pending_new_turn:
            pieces.append("[New Turn]")
            self.pending_new_turn = False

        if self.first:
            # no extra instruction
            self.first = False
        else:
            pieces.append("Continue as " + self.name + ".\n")

        if self.board_state:
            pieces.append(f"[Board state: {json.dumps(self.board_state)}]")

        if self.pending_draw:
            pieces.append(f"[Drawn card: {self.pending_draw}]")
            self.pending_draw = ""

        if self.last_decisions:
            pieces.append(f"[Last decisions: {self.last_decisions}]")

        if self.pending_user_input:
            pieces.append(f"[User note: {self.pending_user_input}]")
            self.pending_user_input = ""

        user_msg = "\n\n".join(pieces).strip()
        # push to history
        self.history.append({"role":"user","content":user_msg})
        return user_msg

    def take_turn(self, user_msg):
        # trim to system + last 10 messages
        hist = self.history[-11:]
        last_error = None
        last_content = None

        for attempt in range(1, self.max_retries+1):
            resp = openai.chat.completions.create(
                model="o3-mini",
                messages=hist,
                temperature=1
            )
            raw = resp.choices[0].message.content
            last_content = raw
            # strip fences
            clean = raw
            if clean.startswith("```"):
                lines = clean.splitlines()
                if lines[0].startswith("```"): lines=lines[1:]
                if lines[-1].startswith("```"): lines=lines[:-1]
                clean = "\n".join(lines)

            try:
                data = json.loads(clean)
                # must have keys
                if not all(k in data for k in ("decisions","public_info","end_turn")):
                    raise KeyError("Missing keys")
                # record assistant in history
                self.history.append({"role":"assistant","content":raw})
                return data

            except (json.JSONDecodeError, KeyError) as e:
                last_error = e
                if attempt < self.max_retries:
                    hist.append({"role":"user","content":
                        "⚠️ Invalid JSON. Reply with keys: decisions, public_info, end_turn."
                    })
                    continue

                raise ValueError(
                    f"{self.name} failed after {self.max_retries} tries: {last_error}. "
                    f"Last content: {last_content!r}"
                )
