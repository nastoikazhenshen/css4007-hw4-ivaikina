# HW4 — submission

**AI assistance:** <!-- what you used, and for what. "None" is an answer too. -->

used ChatGPT to understand the HW4 instructions, plan the decomposition, draft the tool schemas, and check my manual calculations for Q-09. I will implement and test the code separately and report actual run results.

## Part A — Plan on paper (Easy)

> Commit this whole part before any `.py` file exists.

### A1 — The steps

| # | Step | What goes in (types) | What comes out (types) | When it goes wrong | Tool, loop, or model? |
|---|---|---|---|---|---|
| 1 | Understand the question | question (`str`) | districts, year, metric (`dict`) | Wrong interpretation | Model |
| 2 | Find documents | search query (`str`) | matching documents (`list[dict]`) | Missing or irrelevant documents | `lookup` tool |
| 3 | Check sources | documents (`list[dict]`) | values, units and source IDs (`dict`) | Archived profile or missed correction | Model |
| 4 | Plan calculation | values and question (`dict`) | operation and arguments (`dict`) | Wrong formula or incompatible units | Model |
| 5 | Calculate | operation (`str`), `a` and `b` (`number`) | result or error (`dict`) | Division by zero or invalid input | `calculate` tool |
| 6 | Compare and format | calculated values (`number`), question (`str`) | answer, difference and unit (`dict`) | Wrong comparison or rounding | Model |
| 7 | Validate | answer and sources (`dict`) | valid answer or error (`dict`) | Missing source, unit or required field | Program/loop |

**How the steps connect:**

Question -> Understand -> Lookup -> Check sources -> Plan calculation -> Calculate -> Compare and format -> Validate -> Final answer.

If information is missing, the model can call lookup again. If the calculator returns an error, the model should correct the arguments or say it cannot answer. The Python loop passes tool results back to the model and has a round limit.

**What I am assuming:**

1. I use the 2025 census unless the question asks for another year.
2. Archived profiles do not replace current data. Correction notices take priority over original profiles.
3. I check units before calculations, do not treat missing values as zero, and keep full precision until the final rounding.
4. lookup reads local documents only; calculate performs arithmetic only.
5. The final answer includes the requested name or yes/no, numeric value and unit.
6. The most sensitive assumption is choosing the correct source values. A correct calculation cannot fix outdated or uncorrected data.

### A2 — The two tools

#### `lookup`

```json
{
  "type": "function",
  "name": "lookup",
  "description": "Search district documents and return matching sources.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "District name or information to find"
      }
    },
    "required": ["query"],
    "additionalProperties": false
  }
}
```

| Case | What the tool returns |
|---|---|
| success | `{"matches":[{"id":"NR-11","title":"Millbrook district profile (2025)","text":"..."}]}` |
| no matches | `{"matches":[]}` |
| invalid query | `{"error":"Invalid query"}` |

**Worst thing it could do with strange or dangerous input:**
A very long or malicious query could produce irrelevant or excessive output, or try to access files outside the corpus if I implemented it unsafely.

#### `calculate`

```json
{
  "type": "function",
  "name": "calculate",
  "description": "Perform arithmetic on two numbers.",
  "parameters": {
    "type": "object",
    "properties": {
      "operation": {
        "type": "string",
        "enum": ["add", "subtract", "multiply", "divide"]
      },
      "a": {"type": "number"},
      "b": {"type": "number"}
    },
    "required": ["operation", "a", "b"],
    "additionalProperties": false
  }
}
```

| Case | What the tool returns |
|---|---|
| success | `{"result":49.041655681518584}` |
| division by zero | `{"error":"Division by zero"}` |
| unsupported operation | `{"error":"Unsupported operation"}` |
| invalid numeric input | `{"error":"Invalid numeric input"}` |

**Worst thing it could do with strange or dangerous input:**
If I used eval(), an input could run unwanted code. I will use only four explicit arithmetic operations, validate numeric types, reject non-finite results and handle division by zero.

### A3 — Q-09 by hand

```json
[
  {
    "role": "assistant",
    "tool_call": {"name": "lookup", "arguments": {"query": "Brightwater population area 2025 correction"}}
  },
  {
    "role": "tool",
    "name": "lookup",
    "relevant_source_data": [
      {"id": "NR-05", "population_2025": 44675, "area_km2": 912.4},
      {"id": "NR-16", "corrected_area_km2": 921.4}
    ]
  },
  {
    "role": "assistant",
    "tool_call": {"name": "lookup", "arguments": {"query": "Millbrook population area 2025"}}
  },
  {
    "role": "tool",
    "name": "lookup",
    "relevant_source_data": [
      {"id": "NR-11", "population_2025": 37203, "area_km2": 758.6}
    ]
  },
  {
    "role": "assistant",
    "tool_call": {"name": "calculate", "arguments": {"operation": "divide", "a": 44675, "b": 921.4}}
  },
  {"role": "tool", "name": "calculate", "result": 48.48599956587801},
  {
    "role": "assistant",
    "tool_call": {"name": "calculate", "arguments": {"operation": "divide", "a": 37203, "b": 758.6}}
  },
  {"role": "tool", "name": "calculate", "result": 49.041655681518584},
  {
    "role": "assistant",
    "tool_call": {"name": "calculate", "arguments": {"operation": "subtract", "a": 49.041655681518584, "b": 48.48599956587801}}
  },
  {"role": "tool", "name": "calculate", "result": 0.5556561156405735},
  {
    "role": "assistant",
    "final_answer": {"answer": "Millbrook", "value": 0.6, "unit": "residents per km2"}
  }
]
```

**My arithmetic:**
Population density = population / area.
- Brightwater: 44675 / 921.4 = 48.48599956587801 residents/km2.
- Millbrook: 37203 / 758.6 = 49.041655681518584 residents/km2.
- Difference: 49.041655681518584 - 48.48599956587801 = 0.5556561156405735 residents/km2.
- Rounded to one decimal place: 0.6 residents/km2.

### A4 — Why I split it this way

>I split the task into separate steps to make it easier to find and fix errors. For example, in Q-09, using the original area instead of the corrected one would give a wrong result even if the calculation was correct.

>I chose separate lookup and calculation steps because they are easier to test and more reliable, although they require more tool calls.

---

## Part B — Build it and run it (Medium)

### What I changed from Part A while coding

>I changed `calculate` to accept one arithmetic expression instead of separate numbers and an operation. I used Python's `ast` module to evaluate expressions safely.

>I also improved the tool descriptions and system prompt to make the model check units, archived profiles and corrections before calculations.

>For S2, I used parallel requests to reduce execution time while keeping k = 5.

### B2 — Tests

```text
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0
collected 13 items

tests/test_tools.py::test_lookup_brightwater PASSED
tests/test_tools.py::test_lookup_ossbridge PASSED
tests/test_tools.py::test_lookup_similar_names PASSED
tests/test_tools.py::test_lookup_archived PASSED
tests/test_tools.py::test_lookup_typo PASSED
tests/test_tools.py::test_lookup_empty PASSED
tests/test_tools.py::test_calculate_multiplication PASSED
tests/test_tools.py::test_calculate_division PASSED
tests/test_tools.py::test_calculate_zero PASSED
tests/test_tools.py::test_calculate_import PASSED
tests/test_tools.py::test_calculate_attribute PASSED
tests/test_tools.py::test_calculate_power PASSED
tests/test_tools.py::test_calculate_invalid PASSED

13 passed in 0.13s
```

### B3 — The loop

- Round limit, and why: I used 8 rounds to prevent endless tool calls. 
- Where the logs are: All logs are saved in the `outputs/` folder as JSON files.
- Real Q-09 conversation compared with my A3 version, what is different: In A3, I planned separate lookups and three calculations. In the real run, the model made 2 lookup calls in round 1 and only 1 calculate call in round 2. It combined all calculations into one expression and got -0.555656, which means Millbrook has the higher density. The final answer was correct: `Millbrook | 0.6`. The run took 3 rounds.

### B4 — Three strategies

**What I kept the same:**

I used the same model (gpt-5.6-luna), 20 questions, answer format, rounding rules and reasoning_effort="none" for all strategies. S2 used k = 5 with parallel requests. Temperature was not set.

**My rule for a correct answer** (written before the first full run): The name must match exactly, and the number must match after rounding, with a tolerance of one unit in the last decimal place. Missing or invalid `ANSWER:` lines count as unanswered.


| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | 9 | 1 | 45880 | 797 | 1.63 | 34.35 | 0.010132 |
| 1 | S2 think and vote (k = 5) | 12 | 0 | 230700 | 7171 | 2.21 | 43.29 | 0.054745 |
| 1 | S3 tools | 19 | 0 | 128692 | 3015 | 5.16 | 107.49 | 0.029356 |
| 2 | S1 direct | 9 | 1 | 45880 | 1170 | 1.53 | 35.97 | 0.010580 |
| 2 | S2 think and vote (k = 5) | 13 | 0 | 230700 | 6962 | 2.20 | 51.32 | 0.054494 |
| 2 | S3 tools | 17 | 0 | 119458 | 2925 | 4.78 | 100.79 | 0.027402 |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | ✓ | ✓ | ✓ |
| Q-02 | ✗ | ✓ | ✓ |
| Q-03 | ✗ | ✓ | ✓ |
| Q-04 | ✓ | ✓ | ✓ |
| Q-05 | ✗ | ✗ | ✓ |
| Q-06 | ✓ | ✓ | ✓ |
| Q-07 | ✓ | ✓ | ✓ |
| Q-08 | ✗ | ✗ | ✓ |
| Q-09 | ✓ | ✓ | ✓ |
| Q-10 | ✓ | ✓ | ✓ |
| Q-11 | ✓ | ✗ | ✓ |
| Q-12 | ✗ | ✓ | ✓ |
| Q-13 | ✗ | ✗ | ✓ |
| Q-14 | ✗ | ✓ | ✓ |
| Q-15 | ✗ | ✗ | ✓ |
| Q-16 | ✓ | ✓ | ✓ |
| Q-17 | ✗ | ✗ | ✓ |
| Q-18 | ✓ | ✓ | ✓ |
| Q-19 | ✗ | ✗ | ✓ |
| Q-20 | ✗ | ✗ | ✗ |
---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| Q-01 | 3 | 3 | Ossbridge / 4.6 | Ossbridge / 4.6 |
| Q-03 | 3 | 6 | Lindenmoor / 5.3 | Lindenmoor / 5.3 |
| Q-09 | 3 | 3 | Millbrook / 0.6 | Millbrook / 0.6 |
| Q-17 | 4 | 3 | Ossbridge / 884 | Harrowfield / 884 |
| Q-20 | 4 | 4 | Harrowfield / 2103 | Harrowfield / 2103 |

>The vague description increased tool calls for Q-03 and changed the answer for Q-17. However, some questions stayed the same. I think clear tool descriptions help the model use tools more consistently, but they do not guarantee correct answers.

### C2 — Three mistakes explained

**S1 — Q-20:** The model answered `Harrowfield | 48660` instead of `Ashgrove | 2993`. It made a mistake comparing budgets per resident.

**S2 — Q-20:** All five answers were different, so voting selected an incorrect answer (`Harrowfield | 42755`). Voting cannot fix mistakes when there is no agreement.

**S3 — Q-20:** The calculator correctly returned `2103.414`, but the model did not compare all three districts before choosing Harrowfield instead of Ashgrove.

S3 usually needed 3 rounds, while Q-13 needed 6. More rounds increase token usage because previous messages are sent again.

### C3 — Which strategy I would use, and what would change it
I would choose S3 because it had the highest accuracy: 19/20 and 17/20. S1 was faster and cheaper but got only 9/20 in both runs. S2 improved to 12/20 and 13/20 but was more expensive than S3.

If I had a strict time limit or small budget, I would choose S1. For simple questions without calculations, S1 could also be enough. With a much larger document collection, I would keep S3 but improve lookup using an index or embeddings.

### C4 — How sure I can be

S1 stayed at 9/20, S2 changed by 1 answer and S3 changed by 2 answers. S3 was better than S2 by 7 answers in Run 1 and 4 in Run 2.

I think S3 is the best for this dataset, but 20 questions are not enough for a general conclusion. I would test around 100–200 more varied questions with repeated runs before trusting the ranking.

### Final questions

1. When the model sends `tool_calls`, no function has been executed yet. The model only requests a tool, and my Python loop runs it.

2. `arguments` arrives as a JSON string because it is part of the API response. I use `json.loads()` to convert it into a dictionary and validate it before calling the function.

3. My two tool definitions contain approximately 274 tokens, measured with `tiktoken` using `o200k_base`. The actual API overhead may differ slightly.

4. In Run 1, S2 cost $0.054745 and S1 cost $0.010132, so S2 was about 5.4 times more expensive. This is because S2 makes five calls per question.

5. Q-13 needed the most rounds in S3: 6 in Run 1 and 5 in Run 2. It compared population losses across three districts and required more lookups and calculations.

6. With 100,000 documents, I would use an index or embeddings instead of searching every document. This would make retrieval faster and more relevant.

7. My calculator uses `ast` and only allows basic arithmetic operations. It rejects unsafe expressions, but the model can still provide incorrect numbers or formulas.

8. Tools helped most with multi-step calculations and unit conversions. However, all three strategies failed Q-20 in both runs because comparing several districts correctly was still difficult.
