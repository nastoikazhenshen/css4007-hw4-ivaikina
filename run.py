import argparse
import json
import statistics
from pathlib import Path

from strategies import (
    run_direct,
    run_vote,
    run_tools,
    get_answer
)


BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "questions.json"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

INPUT_PRICE = 0.20
CACHED_PRICE = 0.02
OUTPUT_PRICE = 1.20


def load_questions():
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_cost(input_tokens, output_tokens, cached_tokens=0):
    normal_tokens = input_tokens - cached_tokens

    cost = (
        normal_tokens * INPUT_PRICE
        + cached_tokens * CACHED_PRICE
        + output_tokens * OUTPUT_PRICE
    ) / 1_000_000

    return round(cost, 8)


def check_answer(result, question):
    parsed = get_answer(result.get("answer"))

    if parsed is None:
        return False

    expected_name = question["answer"].strip().lower()
    actual_name = parsed["name"].strip().lower()

    decimals = question["decimals"]
    tolerance = 10 ** (-decimals)

    expected_value = round(question["value"], decimals)
    actual_value = round(parsed["value"], decimals)

    name_correct = actual_name == expected_name

    value_correct = (
        abs(actual_value - expected_value)
        <= tolerance + 1e-9
    )

    return name_correct and value_correct


def save_json(filename, data):
    path = OUTPUT_DIR / filename

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


def load_json(filename):
    path = OUTPUT_DIR / filename

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def result_filename(run_number, strategy, question_id):
    return f"run{run_number}_{strategy}_{question_id}.json"


def run_experiment(questions, run_number):
    all_results = []

    for index, question in enumerate(questions, start=1):
        question_id = question["id"]
        question_text = question["question"]
        decimals = question["decimals"]

        print(
            f"\n[{index}/{len(questions)}] {question_id}",
            flush=True
        )

        for strategy in ["S1", "S2", "S3"]:
            filename = result_filename(
                run_number, strategy, question_id
            )

            # Do not repeat completed API requests
            if (OUTPUT_DIR / filename).exists():
                print(f"  {strategy}: loading saved result")
                result = load_json(filename)

            else:
                print(f"  Running {strategy}...", flush=True)

                if strategy == "S1":
                    result = run_direct(
                        question_text,
                        question_id,
                        decimals
                    )

                elif strategy == "S2":
                    result = run_vote(
                        question_text,
                        question_id,
                        decimals,
                        k=5
                    )

                else:
                    result = run_tools(
                        question_text,
                        question_id=question_id,
                        decimals=decimals
                    )

                result["strategy"] = strategy
                result["run"] = run_number
                result["correct"] = check_answer(
                    result, question
                )

                # Save immediately after each strategy
                save_json(filename, result)

            # Recheck saved results without changing answers
            result["correct"] = check_answer(
                result, question
            )

            result["unanswered"] = (
                get_answer(result.get("answer")) is None
            )

            result["cost_usd"] = calculate_cost(
                result["input_tokens"],
                result["output_tokens"],
                result.get("cached_tokens", 0)
            )

            all_results.append(result)

            print(
                f"  {strategy}: "
                f"correct={result['correct']}, "
                f"time={result['total_seconds']:.2f}s, "
                f"cost=${result['cost_usd']:.6f}",
                flush=True
            )

    return all_results


def make_summary(results):
    summary = []

    for strategy in ["S1", "S2", "S3"]:
        items = [
            item for item in results
            if item["strategy"] == strategy
        ]

        if not items:
            continue

        total_input = sum(
            item["input_tokens"] for item in items
        )

        total_output = sum(
            item["output_tokens"] for item in items
        )

        total_cached = sum(
            item.get("cached_tokens", 0)
            for item in items
        )

        times = [
            item["total_seconds"] for item in items
        ]

        summary.append({
            "strategy": strategy,
            "correct": sum(
                item["correct"] for item in items
            ),
            "total": len(items),
            "unanswered": sum(
                item["unanswered"] for item in items
            ),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "cached_tokens": total_cached,
            "median_seconds": round(
                statistics.median(times), 2
            ),
            "total_seconds": round(sum(times), 2),
            "cost_usd": calculate_cost(
                total_input,
                total_output,
                total_cached
            )
        })

    return summary


def save_summary(results, run_number, question_count):
    suffix = f"run{run_number}_{question_count}questions"

    summary = make_summary(results)

    save_json(f"{suffix}_results.json", results)
    save_json(f"{suffix}_summary.json", summary)

    print("\nSUMMARY")

    for item in summary:
        print(
            f"{item['strategy']}: "
            f"{item['correct']}/{item['total']}, "
            f"Unanswered: {item['unanswered']}, "
            f"Input: {item['input_tokens']}, "
            f"Output: {item['output_tokens']}, "
            f"Median: {item['median_seconds']}s, "
            f"Total: {item['total_seconds']}s, "
            f"Cost: ${item['cost_usd']:.6f}"
        )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit", type=int, default=3
    )

    parser.add_argument(
        "--run", type=int, default=1
    )

    parser.add_argument(
        "--summary-only",
        action="store_true"
    )

    args = parser.parse_args()

    questions = load_questions()

    if args.limit < 1 or args.limit > len(questions):
        parser.error("Invalid question limit")

    selected = questions[:args.limit]

    print("Questions:", len(selected))
    print("Run:", args.run)

    if args.summary_only:
        results = []

        for question in selected:
            for strategy in ["S1", "S2", "S3"]:
                filename = result_filename(
                    args.run,
                    strategy,
                    question["id"]
                )

                if not (OUTPUT_DIR / filename).exists():
                    parser.error(
                        f"Missing saved result: {filename}"
                    )

                result = load_json(filename)

                result["correct"] = check_answer(
                    result, question
                )

                result["unanswered"] = (
                    get_answer(result.get("answer")) is None
                )

                results.append(result)

    else:
        results = run_experiment(
            selected,
            args.run
        )

    save_summary(
        results,
        args.run,
        len(selected)
    )


if __name__ == "__main__":
    main()

