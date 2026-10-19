import ast
import json
import math
import operator
import difflib
from pathlib import Path


DATA_PATH = Path(__file__).parent / "data" / "corpus.jsonl"

DISTRICTS = [
    "Ossbridge", "Ossford", "Tarnvale", "Kelmarsh",
    "Brightwater", "Stonecairn", "Harrowfield",
    "Lindenmoor", "Redfen", "Ashgrove",
    "Millbrook", "Coldharbour"
]


def load_documents():
    documents = []

    with open(DATA_PATH, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                documents.append(json.loads(line))

    return documents


def lookup(query):
    if not isinstance(query, str) or not query.strip():
        return {"error": "Invalid query"}

    if len(query) > 200:
        return {"error": "Query is too long"}

    try:
        documents = load_documents()
        words = query.lower().split()

        # Check district names in the query
        mentioned = [
            name for name in DISTRICTS
            if name.lower() in words
        ]

        if not mentioned:
            for word in words:
                suggestions = difflib.get_close_matches(
                    word, DISTRICTS, n=2, cutoff=0.75
                )
                if suggestions:
                    return {
                        "error": "Unknown district or spelling",
                        "suggestions": suggestions
                    }

        matches = []

        for document in documents:
            title = document["title"].lower()
            content = document["text"].lower()

            if "archived" in title:
                continue

            score = 0

            for word in words:
                if word in title:
                    score += 3
                elif word in content:
                    score += 1

            if score > 0:
                matches.append((score, document))

        matches.sort(key=lambda item: item[0], reverse=True)

        results = []

        for score, document in matches[:5]:
            results.append({
                "id": document["id"],
                "title": document["title"],
                "text": document["text"][:1000]
            })

        # Include correction if Brightwater is mentioned
        if "brightwater" in words:
            correction = next(
                (doc for doc in documents if doc["id"] == "NR-16"),
                None
            )

            if correction and not any(
                item["id"] == "NR-16" for item in results
            ):
                results.append({
                    "id": correction["id"],
                    "title": correction["title"],
                    "text": correction["text"][:1000]
                })

        if not results:
            return {"error": "No matching documents found"}

        return {"matches": results}

    except (OSError, ValueError, KeyError) as error:
        return {"error": str(error)}


OPERATIONS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv
}


def calculate(expression):
    if not isinstance(expression, str) or not expression.strip():
        return {"error": "Invalid expression"}

    if len(expression) > 150:
        return {"error": "Expression is too long"}

    try:
        tree = ast.parse(expression, mode="eval")

        def solve(node):
            if isinstance(node, ast.Expression):
                return solve(node.body)

            if isinstance(node, ast.Constant):
                if type(node.value) in (int, float):
                    if abs(node.value) > 1e15:
                        raise ValueError("Number is too large")
                    return node.value
                raise ValueError("Only numbers are allowed")

            if isinstance(node, ast.UnaryOp):
                value = solve(node.operand)
                if isinstance(node.op, ast.USub):
                    return -value
                if isinstance(node.op, ast.UAdd):
                    return value
                raise ValueError("Unsupported operation")

            if isinstance(node, ast.BinOp):
                operation = type(node.op)

                if operation not in OPERATIONS:
                    raise ValueError("Unsupported operation")

                left = solve(node.left)
                right = solve(node.right)

                if operation == ast.Div and right == 0:
                    raise ValueError("Division by zero")

                result = OPERATIONS[operation](left, right)

                if not math.isfinite(result) or abs(result) > 1e15:
                    raise ValueError("Result is too large")

                return result

            raise ValueError("Unsafe expression")

        result = solve(tree)
        return {"result": result}

    except (SyntaxError, ValueError, OverflowError,
            ZeroDivisionError, TypeError) as error:
        return {"error": str(error)}


if __name__ == "__main__":
    print("LOOKUP TEST:")
    print(json.dumps(
        lookup("Brightwater population area 2025 correction"),
        indent=2
    ))

    print("\nCALCULATE TEST:")
    print(calculate("44675 / 921.4"))
