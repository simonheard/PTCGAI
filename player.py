import openai
import json

class Player:
    def __init__(self, name: str, deck: str, order: str):
        self.name = name
        self.deck = deck
        self.order = order  # "first" or "second"
        # Initial “master” prompt
        self.system_prompt = (
            f"You will be playing PTCG with an opponent. Your deck of cards is:\n{deck}\n\n"
            f"You will play {order}.\n"
            "Please strictly follow the official PTCG rules. Whenever you have a random situation "
            "(like drawing a card), pause and prompt the user for the result.\n"
            "Now you may begin your move."
        )
        # After first turn, we’ll switch to this instruction
        self.turn_instruction = (
            "Decide what information is critical to the game state. "
            "When you respond, output exactly ONE JSON object with these keys:\n"
            "  • \"remember\": \"<what you should remember>\"\n"
            "  • \"decisions\": \"<what you will do now>\"\n"
            "If you require the user to resolve a random event, also include:\n"
            "  • \"user_input_request\": \"<exactly what you need me to do>\"\n\n"
            "Now continue with your move."
        )
        self.memory = ""  # accumulated “remember” string

    def build_prompt(self) -> str:
        if not self.memory:
            return self.system_prompt
        return f"{self.turn_instruction}\n\nPreviously remembered:\n{self.memory}"

    def take_turn(self) -> dict:
        """
        Sends the current prompt, parses the JSON response, returns it.
        """
        prompt = self.build_prompt()
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7
        )
        content = resp.choices[0].message["content"].strip()
        # Parse JSON out of the assistant’s reply
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"{self.name} returned invalid JSON:\n{content}")
        # Must have at least remember & decisions
        if "remember" not in data or "decisions" not in data:
            raise KeyError(f"{self.name} JSON missing required keys:\n{content}")
        return data
