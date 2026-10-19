import json
from pathlib import Path

folder = Path("outputs")

for run in [1, 2]:
    for question in range(1, 21):
        name = f"run{run}_S3_Q-{question:02d}.json"
        path = folder / name

        if not path.exists():
            continue

        data = json.loads(path.read_text(encoding="utf-8"))

        print(
            name,
            "rounds:", data["rounds"],
            "correct:", data.get("correct")
        )
