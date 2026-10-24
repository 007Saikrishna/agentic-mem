import os
from dotenv import load_dotenv
load_dotenv()

RULES_FILE = os.getenv("RULES_FILE", ".agent_rules.md")

def append_rule_to_file(rule_text: str):
    is_new = not os.path.exists(RULES_FILE)
    with open(RULES_FILE, "a", encoding="utf-8") as f:
        if is_new:
            f.write("# Agentic Project Rules\n\n")
        f.write(f"- {rule_text}\n")
    print(f"\n[+] Rule synced to {RULES_FILE}: {rule_text}")