import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from openai import OpenAI

from tools import lookup, calculate


load_dotenv()

MODEL = "gpt-5.6-luna"
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
CORPUS_PATH = BASE_DIR / "data" / "corpus.jsonl"

OUTPUT_DIR.mkdir(exist_ok=True)

MAX_ROUNDS = 8


# Common instructions for all three strategies
COMMON_PROMPT = """
You answer questions about the Nine Rivers Region.

Use only the provided documents or tool results.
Do not use external information or guess missing values.

Check the year, district names and units carefully.
Use current profiles instead of archived profiles.
Correction notices take priority over original profiles.

Important unit conversions:
1 cubic metre = 1000 litres.
1 megalitre = 1000 cubic metres = 1000000 litres.
1 million tenge = 1000000 tenge.

For annual household water use per resident per day:
divide annual water in litres by population and 365.

Keep full precision during calculations.
Round only the final numerical answer to the requested
number of decimal places.

End with exactly one line:
ANSWER: <name or yes/no> | <number>

If you cannot answer, end with:
ANSWER: UNKNOWN | UNKNOWN
"""


# Instructions specifically for the tool strategy
SYSTEM_PROMPT = COMMON_PROMPT + """
Use lookup to find the required information.
Use calculate for all arithmetic.

Follow these steps:
1. Identify the districts, years and metrics.
2. Find the relevant documents using lookup.
3. Check source values and correction notices.
4. Check units and convert them if necessary.
5. Use calculate to perform the arithmetic.
6. Compare the values and format the final answer.

"When comparing A - B, a positive result means A is higher. "
"A negative result means B is higher. "
"Always check the sign before choosing the final name."
"""


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": (
                "Search the Nine Rivers district documents for facts. "
                "Use exact district names and relevant keywords. "
                "Check document IDs, census years and correction notices. "
                "Ignore archived profiles when current data is requested. "
                "Return relevant text with document IDs and titles. "
                "Pay attention to the original units of each value. "
                "Do not assume that all districts use the same units."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search phrase"
                    }
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Safely evaluate arithmetic expressions using +, -, *, / "
                "and parentheses. Use this tool for numerical calculations. "
                "Before calling, check that all values use compatible units. "
                "For water calculations: 1 cubic metre = 1000 litres, "
                "1 megalitre = 1000000 litres. "
                "For annual per-resident-per-day values, divide by "
                "population and 365 days. "
                "Keep full precision and round only the final answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression"
                    }
                },
                "required": ["expression"],
                "additionalProperties": False
            }
        }
    }
]


def execute_tool(name, arguments):
    if name == "lookup":
        if set(arguments) != {"query"}:
            return {"error": "Expected query"}

        return lookup(arguments["query"])

    if name == "calculate":
        if set(arguments) != {"expression"}:
            return {"error": "Expected expression"}

        return calculate(arguments["expression"])

    return {"error": "Unknown tool"}


def make_question_prompt(question, decimals):
    return (
        f"{question}\n\n"
        f"Round the final numerical answer to "
        f"{decimals} decimal places."
    )


def get_answer(text):
    if not text:
        return None

    matches = re.findall(
        r"ANSWER:\s*([^|\n]+)\|\s*"
        r"([-+]?\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE
    )

    if not matches:
        return None

    name, number = matches[-1]

    try:
        return {
            "name": name.strip(),
            "value": float(number)
        }
    except ValueError:
        return None


def load_corpus():
    documents = []

    with open(CORPUS_PATH, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                documents.append(json.loads(line))

    return "\n\n".join(
        f"{doc['id']} - {doc['title']}\n{doc['text']}"
        for doc in documents
    )


CORPUS = load_corpus()


# S1 - Direct
def run_direct(question, question_id, decimals, think=False):
    system_prompt = (
        COMMON_PROMPT
        + "\nUse the documents below to answer the question.\n\n"
        + CORPUS
    )

    if think:
        system_prompt += (
            "\nWork through the relevant evidence and "
            "calculations before giving the final answer."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": make_question_prompt(question, decimals)
        }
    ]

    start_time = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        reasoning_effort="none"
    )

    duration = time.perf_counter() - start_time
    answer = response.choices[0].message.content
    parsed = get_answer(answer)

    input_tokens = 0
    output_tokens = 0

    if response.usage:
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

    return {
        "question_id": question_id,
        "answer": answer,
        "parsed": parsed,
        "unanswered": parsed is None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_seconds": duration
    }


# S2 - Think and Vote

from concurrent.futures import ThreadPoolExecutor


def run_vote(question, question_id, decimals, k=5):
    start_time = time.perf_counter()

    # Run the five samples at the same time
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(
                run_direct,
                question,
                question_id,
                decimals,
                True
            )
            for i in range(k)
        ]

        samples = [future.result() for future in futures]

    total_input = sum(
        sample["input_tokens"] for sample in samples
    )

    total_output = sum(
        sample["output_tokens"] for sample in samples
    )

    votes = []

    for sample in samples:
        parsed = sample["parsed"]

        if parsed is not None:
            votes.append((
                parsed["name"].lower(),
                round(parsed["value"], decimals)
            ))

    winner = None

    if votes:
        counts = Counter(votes)
        winner, count = counts.most_common(1)[0]

    duration = time.perf_counter() - start_time

    if winner is None:
        answer = None
    else:
        answer = (
            f"ANSWER: {winner[0]} | "
            f"{winner[1]:.{decimals}f}"
        )

    return {
        "question_id": question_id,
        "answer": answer,
        "parsed": get_answer(answer),
        "unanswered": winner is None,
        "samples": samples,
        "k": k,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "total_seconds": duration
    }



# S3 - Tools
def run_tools(question, question_id="Q-09", decimals=1):
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": make_question_prompt(question, decimals)
        }
    ]

    log = []
    input_tokens = 0
    output_tokens = 0

    start_time = time.perf_counter()
    final_answer = None

    for round_number in range(1, MAX_ROUNDS + 1):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            reasoning_effort="none"
        )

        if response.usage:
            input_tokens += response.usage.prompt_tokens
            output_tokens += response.usage.completion_tokens

        message = response.choices[0].message

        # Keep the model message with all tool calls
        messages.append(
            message.model_dump(exclude_none=True)
        )

        round_log = {
            "round": round_number,
            "tool_calls": []
        }

        if not message.tool_calls:
            final_answer = message.content
            log.append(round_log)
            break

        for call in message.tool_calls:
            tool_start = time.perf_counter()

            try:
                arguments = json.loads(call.function.arguments)

                if not isinstance(arguments, dict):
                    result = {
                        "error": "Arguments must be a JSON object"
                    }
                else:
                    result = execute_tool(
                        call.function.name,
                        arguments
                    )

            except json.JSONDecodeError:
                result = {
                    "error": "Invalid JSON arguments"
                }

            except Exception as error:
                result = {
                    "error": str(error)
                }

            duration = time.perf_counter() - tool_start

            round_log["tool_calls"].append({
                "id": call.id,
                "name": call.function.name,
                "arguments": call.function.arguments,
                "result": result,
                "seconds": duration
            })

            # Send a result for every tool call
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result)
            })

        log.append(round_log)

    total_time = time.perf_counter() - start_time
    parsed = get_answer(final_answer)

    unanswered = parsed is None

    result = {
        "question_id": question_id,
        "question": question,
        "decimals": decimals,
        "answer": final_answer,
        "parsed": parsed,
        "unanswered": unanswered,
        "rounds": len(log),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_seconds": total_time,
        "log": log,
        "messages": messages
    }

    # Save a separate log for every run
    log_path = OUTPUT_DIR / (
        f"{question_id}_tools_{time.time_ns()}.json"
    )

    with open(log_path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )

    return result
