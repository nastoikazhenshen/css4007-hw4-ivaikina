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

<!-- what changed in your plan, and why. "None" is an answer too. -->

### B2 — Tests

```text
<!-- pytest output -->
```

### B3 — The loop

- Round limit, and why:
- Where the logs are:
- Real Q-09 conversation compared with my A3 version, what is different:

### B4 — Three strategies

**What I kept the same:**

<!-- model, temperature, k, prompts, answer format, anything else -->

**My rule for a correct answer** (written before the first full run):

| Run | Strategy | Correct /20 | Unanswered | Input tokens | Output tokens | Median seconds per question | Total seconds | Cost ($) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | S1 direct | | | | | | | |
| 1 | S2 think and vote (k = ) | | | | | | | |
| 1 | S3 tools | | | | | | | |
| 2 | S1 direct | | | | | | | |
| 2 | S2 think and vote (k = ) | | | | | | | |
| 2 | S3 tools | | | | | | | |

**Per question (run 1):**

| Question | S1 | S2 | S3 |
|---|:---:|:---:|:---:|
| Q-01 | | | |
| Q-02 | | | |
| Q-03 | | | |
| Q-04 | | | |
| Q-05 | | | |
| Q-06 | | | |
| Q-07 | | | |
| Q-08 | | | |
| Q-09 | | | |
| Q-10 | | | |
| Q-11 | | | |
| Q-12 | | | |
| Q-13 | | | |
| Q-14 | | | |
| Q-15 | | | |
| Q-16 | | | |
| Q-17 | | | |
| Q-18 | | | |
| Q-19 | | | |
| Q-20 | | | |

---

## Part C — Explain and choose (Hard)

### C1 — Does the tool description matter?

| Question | Calls (your description) | Calls (vague) | Answer (yours) | Answer (vague) |
|---|---:|---:|---|---|
| | | | | |

### C2 — Three mistakes explained

### C3 — Which strategy I would use, and what would change it

### C4 — How sure I can be

### Final questions

1.
2.
3.
4.
5.
6.
7.
8.
