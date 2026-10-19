import json
from pathlib import Path

from strategies import run_tools


DATA_PATH = Path(__file__).parent / "data" / "questions.json"

with open(DATA_PATH, "r", encoding="utf-8") as file:
    questions = json.load(file)

question = next(
    item for item in questions
    if item["id"] == "Q-09"
)

result = run_tools(
    question["question"],
    question_id=question["id"],
    decimals=question["decimals"]
)

print("Question:", result["question"])
print("Answer:", result["answer"])
print("Rounds:", result["rounds"])
print("Input tokens:", result["input_tokens"])
print("Output tokens:", result["output_tokens"])
print("Total seconds:", round(result["total_seconds"], 2))
print("Unanswered:", result["unanswered"])
