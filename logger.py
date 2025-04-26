import os

class Logger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log(self, player_name: str, message_type: str, content: str):
        """
        Append a block to player_name.log.
        message_type: e.g. "PROMPT", "RESPONSE", or "USER_INPUT"
        """
        fname = os.path.join(self.log_dir, f"{player_name}.log")
        with open(fname, "a", encoding="utf-8") as f:
            f.write(f"=== {player_name} {message_type} ===\n")
            f.write(content.strip() + "\n\n")
