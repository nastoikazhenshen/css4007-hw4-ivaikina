import json
from pathlib import Path

import strategies
from strategies import run_tools


base = Path(__file__).parent
output = base / "outputs"
output.mkdir(exist_ok=True)

question_ids = ["Q-01", "Q-03", "Q-09", "Q-17", "Q-20"]

with open(base / "data" / "questions.json", encoding="utf-8") as file:
    questions = json.load(file)

original_description = strategies.TOOLS[0]["function"]["description"]

results = []

try:
    for question in questions:
        if question["id"] not in question_ids:
            continue

        for version in ["original", "vague"]:
            if version == "vague":
                strategies.TOOLS[0]["function"]["description"] = "Looks things up."
            else:
                strategies.TOOLS[0]["function"]["description"] = original_description

            result = run_tools(
                question["question"],
                question["id"],
                question["decimals"]
            )

            calls = sum(
                len(item["tool_calls"])
                for item in result["log"]
            )

            results.append({
                "question": question["id"],
                "version": version,
                "calls": calls,
                "answer": result["answer"],
                "log": result["log"]
            })

            print(
                question["id"],
                version,
                "calls:", calls,
                "answer:", result["parsed"]
            )
finally:
    strategies.TOOLS[0]["function"]["description"] = original_description

with open(output / "c1_results.json", "w", encoding="utf-8") as file:
    json.dump(results, file, indent=2, ensure_ascii=False)
