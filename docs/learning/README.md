# Call Me Maybe: the learning roadmap

[Beginner explanation](../../README.md) · [Interview explanation](../interview/README.md) · [Project subject](../../en.subject.pdf)

This roadmap covers the concepts needed to build this project's function-calling pipeline yourself. Study in the order below. Each stage has a small exercise and a checkpoint so that reading turns into something you can explain and implement.

You can solve the project without training a language model. The essential model knowledge is how text becomes tokens, how the SDK returns next-token scores, and how to constrain the next choice. Advanced neural-network mathematics can come later.

The current source is useful study material, but it contains incomplete grammar rules and validation. Use it to investigate design choices; do not assume every implementation detail is a correct pattern to copy.

## 1. Understand the task before writing code

Learn to turn a written assignment into explicit input, output, behavior, and failure requirements. Distinguish producing a function-call description from executing a function.

For “Find the square root of 16,” the call argument is `16`; the mathematical result `4` belongs to a later execution step. For “Reverse 'hello',” the argument remains `hello`.

Write down these project obligations in your own words:

- Load a changeable catalog of function definitions and a list of prompts.
- Use the LLM to choose the function; avoid keyword-based dispatch shortcuts.
- Constrain generation while tokens are selected.
- Produce the exact outer fields `prompt`, `name`, and `parameters`.
- Require all arguments and their correct types, with no extra arguments.
- Handle errors clearly and preserve the assignment's expected CLI contract.
- Verify behavior with the required model and report measured accuracy and speed.

**Exercise:** manually create expected call records for addition, greeting, reversal, square root, and replacement. For replacement, supply `source_string`, `regex`, and `replacement`. Explain what each slot means.

**Checkpoint:** you can identify an output that is valid JSON but asks for the wrong operation or supplies a computed result as an argument.

**Read:** [en.subject.pdf](../../en.subject.pdf), especially the mandatory part, usage, output rules, and README requirements.

## 2. Python values, containers, and control flow

Learn variables, assignments, indentation, expressions, comparisons, truth values, `if`, `for`, `while`, `break`, and `return`. Understand `str`, `int`, `float`, `bool`, and `None`, and the difference between a value and its textual representation.

Study lists for ordered collections, dictionaries for key/value lookup, sets for membership and deduplication, and `frozenset` for immutable sets. Learn dictionary insertion order, string slicing, `startswith`, `strip`, `replace`, `join`, and dictionary methods such as `items`, `keys`, and `setdefault`.

Your code uses comprehensions, generator expressions, lambdas, nested functions, and set operations. In particular, `A & B` means intersection, and `A | B` means union. Understand operator precedence before combining them in one expression.

**Exercise:** create a dictionary with two function names as keys. Look up one function. Build a list of its parameter names. Compute the set of missing parameters from a supplied argument dictionary.

```python
required = {"source_string", "regex", "replacement"}
received = {"source_string"}
missing = required - received
assert missing == {"regex", "replacement"}
```

**Checkpoint:** explain why `list(initial_ids)` protects the caller's original list from appends, while assigning `ids = initial_ids` would share the same list.

**Project anchors:** [loader.py](../../src/loader.py), [vocab.py](../../src/vocab.py), and `_remaining_keys` in [constraints.py](../../src/constraints.py).

## 3. Functions, objects, and module boundaries

Learn function parameters, return values, default arguments, local scope, closures, and higher-order functions. `ids_where(predicate)` accepts a function as data; the predicate decides whether one token passes a check.

Learn classes, instances, methods, `self`, `__init__`, instance attributes, inheritance, `@staticmethod`, and `@classmethod`. Understand mutable per-instance state: two prompts should not accidentally share the same constraint progress.

Study packages, `__init__.py`, `__main__.py`, relative imports, absolute imports, and `if __name__ == "__main__"`. Learn what a leading underscore communicates and why reaching into another class's internal fields increases coupling.

**Exercise:** create a small counter object with `advance()` and `is_complete()`. Make two instances and prove advancing one does not advance the other. Then implement a predicate that accepts token strings beginning with `fn_`.

**Checkpoint:** explain the difference between `JsonIO.load_prompts(...)`, `constraint.advance(...)`, and a standalone `_selection_prompt(...)` function.

**Project anchors:** all source modules, especially [caller.py](../../src/caller.py) and [__main__.py](../../src/__main__.py).

## 4. Type hints and static analysis

Learn annotations such as `list[int]`, `dict[str, ParameterSpec]`, `str | Path`, `str | None`, `Any`, and callable types. Distinguish type hints checked by a tool from runtime checks enforced when the program executes.

Learn forward references, `from __future__ import annotations`, and `TYPE_CHECKING`. Several modules avoid runtime imports needed only by the type checker. Understand why this helps with circular dependencies and optional heavy imports.

Study how mypy reports incompatible values, missing annotations, overly broad return types, and unused ignores. A `# type: ignore` suppresses a particular report; it does not fix the underlying behavior.

**Exercise:** annotate a function accepting a token predicate as `Callable[[str], bool]` and returning `set[int]`. Give it the wrong kind of predicate and inspect the type-checker feedback.

**Checkpoint:** explain why `dict[str, Any]` does not guarantee that `a` and `b` are present or numeric, and why `TYPE_MAP` does nothing until code actually uses it.

**Read:** [mypy type-hint guide](https://mypy.readthedocs.io/en/stable/cheat_sheet_py3.html). **Project anchors:** [models.py](../../src/models.py), [vocab.py](../../src/vocab.py), and the `TYPE_CHECKING` blocks.

## 5. Files, paths, JSON, and exceptions

Learn relative versus absolute paths, UTF-8 encoding, `Path`, `open`, context managers, and creating parent directories. Understand how the working directory affects `data/input/...`.

Learn `json.load` versus `json.loads`, and `json.dump` versus `json.dumps`. File-oriented functions read/write streams; string-oriented functions consume/produce text. Parsing converts JSON text into Python values; serialization performs the reverse.

Study `try`, `except`, `raise`, custom exception classes, exception chaining, `OSError`, `FileNotFoundError`, `JSONDecodeError`, and text decoding failures. Distinguish expected bad input from a programming bug. Learn stderr, exit codes, and logging.

**Exercise:** write a tiny JSON reader and test a valid file, missing file, malformed file, and a directory supplied where a file is expected. Ensure the file is closed in every path. Explain which failures your exception handlers catch.

**Checkpoint:** trace `JsonIOErorr` from `_read_json` through `main`, and explain why some read failures currently bypass it.

**Read:** [Python JSON documentation](https://docs.python.org/3/library/json.html). **Project anchor:** [loader.py](../../src/loader.py).

## 6. Runtime schemas and Pydantic

Learn `BaseModel`, required fields, defaults, nested models, `Field`, field validators, `ValidationError`, `TypeAdapter`, and `model_dump`. Study strict versus coercing validation and explicit policies for extra fields.

Separate validating the shape of a function definition from validating a call against that definition. A `FunctionCall` with an arbitrary argument dictionary does not automatically gain the rules in some other `FunctionDefinition` instance.

Study runtime schema validation: check name membership, exact argument keys, supported types, integer versus number semantics, and numeric finiteness. Understand Python's Boolean/integer relationship so a Boolean is not accidentally accepted as an ordinary numeric argument. Decide your integer policy explicitly, including whether a JSON value such as `2.0` should count as integer-valued under the project's contract.

**Exercise:** validate prompts so that `""` and `"   "` fail but `" greet John "` retains its original spaces. Build a separate validator that rejects `{"a":2}` when `a` and `b` are required, and rejects an unexpected `c`.

**Checkpoint:** explain why parsing JSON, validating its schema, and checking its meaning require different checks.

**Read:** [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) and [TypeAdapter](https://docs.pydantic.dev/latest/concepts/type_adapter/). **Project anchors:** [models.py](../../src/models.py) and [loader.py](../../src/loader.py).

## 7. Language models and the public SDK boundary

Learn inference, context, next-token prediction, autoregressive generation, token IDs, vocabulary size, and logits. A logit is an unnormalized score, not itself a probability. Appending the chosen token changes the context for the next prediction.

Understand greedy selection, sampling, temperature, and softmax conceptually. You need to know why argmax can select from logits directly; deriving or training a transformer is not a prerequisite for this assignment.

Learn to verify an API contract: method names, argument types, return shapes, errors, and supported model IDs. The reviewed code assumes a flat logits vector and an `encode` return value supporting `.squeeze(0).tolist()`. The subject's illustrative signatures differ in places. Resolve those assumptions through the supplied SDK's public documentation when you study it yourself.

**Exercise:** use a fake model returning a list of five scores. Feed it a growing list of IDs and print which ID wins at each step. Explain what changes when a token is appended.

**Checkpoint:** explain `encode`, logits generation, and `decode` without confusing model parameters (learned weights) with function parameters (argument slots).

**Project anchors:** [generator.py](../../src/generator.py), [caller.py](../../src/caller.py), and the subject's SDK section. The excluded SDK was not inspected when preparing this roadmap.

## 8. Tokenization, Unicode, and token surfaces

Learn the difference between characters, Unicode code points, encoded bytes, tokens, and token IDs. Study the purpose of subword tokenization and byte-pair encoding at a conceptual level. Tokens may include leading spaces, multiple punctuation characters, fragments of words, or parts of an encoded character.

Understand encode/decode round trips, special tokens, end-of-sequence behavior, and why concatenating guessed token surfaces may disagree with a real decoder. A robust constraint needs a representation aligned with the tokenizer's actual decoded output, including any byte-level behavior.

The current `surface` method only replaces `Ġ` and `Ċ`. That is a useful clue about token conventions, not a complete tokenizer specification. Also inspect how an implementation handles added tokens, empty surfaces, and token IDs not present in a vocabulary mapping.

**Exercise:** create a toy vocabulary containing `{`, `"`, `a`, `":`, `2`, `}`, and `{"a`. Trace the same JSON using different token splits. Show why a checker that assumes one token equals one character is too restrictive.

**Checkpoint:** explain why a token must be checked in full before it can be called legal, even when its first character fits.

**Read:** the [tokenizer API reference](https://huggingface.co/docs/tokenizers/en/api/tokenizer) for concepts and terminology. Reading about tokenization does not change the subject's restriction on directly using model/tokenizer frameworks in the solution. **Project anchor:** [vocab.py](../../src/vocab.py).

## 9. NumPy arrays and masked selection

Learn one-dimensional array shapes, index alignment, dtypes, Boolean arrays, Boolean indexing, `np.zeros`, `np.array`, `np.argmax`, negative infinity, and NaN handling.

The score at index `i` must correspond to token ID `i`. If the SDK returns a batch or sequence dimension, that must be handled explicitly rather than assuming `len(logits)` is the vocabulary size.

**Exercise:** mask this invented score vector so only IDs 1 and 3 remain legal:

```python
import numpy as np

scores = np.array([8.0, 2.0, 9.0, 5.0], dtype=np.float32)
mask = np.array([False, True, False, True])
scores[~mask] = -np.inf
assert int(np.argmax(scores)) == 3
```

Then consider an empty legal set, legal IDs outside the array, all legal scores equal to negative infinity, and NaN scores. A robust implementation needs explicit handling before declaring a chosen token valid.

**Checkpoint:** explain why “the legal set is nonempty” does not prove “there is a usable legal entry in this score vector.”

**Read:** [NumPy argmax](https://numpy.org/doc/stable/reference/generated/numpy.argmax.html). **Project anchor:** [generator.py](../../src/generator.py).

## 10. Tries, stacks, and prefix matching

Learn tree nodes, edges, root nodes, terminal markers, shared prefixes, and depth-first traversal. A stack allows traversal without recursive function calls.

A trie answers whether a sequence is a prefix of any allowed name and whether it is already a complete name. Those are different questions. A node can be terminal and still have children.

**Exercise:** build a trie for `fn_add`, `fn_add_numbers`, and `fn_greet`. Trace each character in `fn_add`. Explain why a terminal marker there must not make the longer function unreachable for every tokenization.

Test tokens that end before a terminal node, at a terminal node, and past a terminal node. Try an empty catalog and names longer than 32 characters. Decide how completion should work when a valid name is also a prefix of another.

**Checkpoint:** identify why `surface.startswith(remaining_name)` can admit extra characters and why final membership checking is still valuable.

**Project anchor:** `NameConstraint` and `_TrieNode` in [constraints.py](../../src/constraints.py).

## 11. Formal languages and finite-state machines

Learn states, transitions, start states, accepting states, dead ends, and invariants. An invariant is a property that must remain true after every transition. For constrained decoding, an essential invariant is that the generated prefix still has at least one valid completion.

Separate syntax state from schema state. Knowing that a closing brace is syntactically possible does not mean all required fields are present. Track completed values, remaining fields, and whether a comma has just been consumed.

For a fixed flat schema, explicit states are manageable. Supporting arbitrary nested JSON requires additional memory, such as a stack, to track nesting. Do not silently broaden the assignment's schema support without designing its grammar.

**Exercise:** draw a transition table for a one-field object `{"a":2}`. Then add a required `b`. Mark every state where `}` is allowed and explain why. Add an empty schema that should permit `{}` without allowing a nonexistent key.

**Checkpoint:** explain why marking `a` emitted when its key closes is different from marking `a`'s value complete.

**Project anchor:** `JsonConstraint` in [constraints.py](../../src/constraints.py).

## 12. JSON lexical grammar: numbers, strings, and booleans

This stage needs careful practice. Broad “looks like a number” token groups are insufficient.

For numbers, study sign placement, zero rules, integer digits, decimal points, fractional digits, exponents, and accepting positions. A useful grammar summary is:

```text
number = optional minus
         (zero OR nonzero digit followed by digits)
         optional (decimal point followed by one or more digits)
         optional (e/E, optional sign, one or more digits)
```

For strings, learn opening/closing quotes, ordinary characters, escape sequences, escaped quotes, backslashes, Unicode escape digits, and forbidden unescaped control characters. A quote following a backslash does not necessarily end a string. Schema keys are JSON strings too and need correct escaping.

For booleans, track progress through exactly lowercase `true` or `false`. Allowing arbitrary substrings or uppercase alternatives does not enforce those literals.

| Input fragment | Expected lesson |
| --- | --- |
| `-12.5e+2` | Valid JSON number; the plus is allowed within the exponent. |
| `+2` | Invalid leading plus. |
| `01` | Invalid leading zero in a multi-digit integer part. |
| `1.` | Incomplete fraction. |
| `1e` | Incomplete exponent. |
| `f` | Prefix of a Boolean, not a complete Boolean. |
| `True` | Python spelling, not JSON Boolean spelling. |
| `"a\\b"` | A JSON string containing an escaped backslash. |
| `"\x"` | Invalid JSON escape. |

**Exercise:** implement a small incremental validator for one JSON number, then for one Boolean. Feed it one character at a time and report whether the prefix is invalid, valid but incomplete, or complete. Later feed multi-character tokens through the same transition logic.

**Checkpoint:** reject closing a value after `-`, `1e`, or `f`, while allowing the prefix to continue correctly. Explain why schema validity for an integer needs a separate policy beyond general number syntax.

**Read:** [RFC 8259](https://www.rfc-editor.org/rfc/rfc8259). **Project anchors:** `digit_like`, `string_safe`, and `bool_tokens` in [vocab.py](../../src/vocab.py), plus the value states in [constraints.py](../../src/constraints.py).

## 13. Combine grammar with token generation

Learn to separate a pure transition function from committing a selected token. To decide legality, simulate the entire candidate token against a copy or immutable representation of state. Accept it only if every part can be consumed and a valid continuation remains. Commit the same transition after selection.

Study interface design: the generator needs operations resembling `legal_tokens`, `advance`, and `is_complete`, but should not need to know each grammar's internal fields. A typing protocol is one possible later improvement.

Handle completion and failure explicitly. Reaching a token limit is not success unless the grammar is complete. A grammar dead end, unusable logits, invalid SDK output, and malformed decoded text need clear error paths. Final schema validation should run before a record is accepted.

**Exercise:** build a fake model that always ranks an invalid token highest and a valid token second. Verify that masking picks the valid one. Then provide a model that never finishes a string and verify the step limit causes a controlled failure.

**Checkpoint:** explain why catching `json.loads` errors after free-form generation would not, by itself, meet the requirement to constrain generation.

**Project anchors:** [generator.py](../../src/generator.py) and [constraints.py](../../src/constraints.py).

## 14. Prompt design and argument extraction

Learn instruction construction, function descriptions, parameter descriptions, schema presentation, and separating selection from extraction. Understand ambiguity, missing information, model hallucination, and the difference between a structurally valid value and a faithful value.

The current selection prompt lists names, parameter names, and function descriptions. Its argument prompt lists the selected name and parameter types. Investigate whether including relevant descriptions improves extraction, and measure changes rather than assuming they help.

Study how user text is delimited in a prompt. Requests may contain quotes, code-like text, or instructions conflicting with the task. Structural constraints limit output form; they do not automatically resolve misleading semantic instructions.

**Exercise:** write selection and argument prompts for a new function catalog. Include two similarly named functions with different descriptions. Explain how the model chooses based on its scores while constraints enforce catalog membership.

**Checkpoint:** explain why hardcoding “if prompt contains sum, use addition” fails the assignment even if it works on the eleven examples.

**Project anchor:** [caller.py](../../src/caller.py).

## 15. Regular expressions and multiple layers of escaping

The replacement tool introduces a separate topic: regular expressions. Learn character classes, repetition, anchors, literal escaping, matching, and substitution. You need enough understanding to know whether extracted `regex` and `replacement` values represent the request.

Keep three possible text layers separate: a Python source literal, JSON text, and the actual regex string. A pattern containing a backslash may need an escaped backslash when represented in JSON. A correct JSON serializer can handle that representation when given the actual string value.

**Exercise:** for “Replace numbers in 'Hello 34' with NUMBERS,” identify all three arguments. One suitable JSON representation is:

```json
{
  "source_string": "Hello 34",
  "regex": "[0-9]+",
  "replacement": "NUMBERS"
}
```

The output describes a substitution; the current application does not perform it. A learning exercise or evaluation harness can separately test the pattern on a known sample.

**Checkpoint:** explain why supplying only `source_string` is incomplete even though the object parses as JSON.

**Read:** [Python regular expressions](https://docs.python.org/3/library/re.html). **Project anchors:** the replacement entry in [function definitions](../../data/input/functions_definition.json) and the matching prompts in [test inputs](../../data/input/function_calling_tests.json).

## 16. Testing, debugging, and evidence

Learn unit tests, integration tests, end-to-end tests, fixtures, fake dependencies, regression tests, boundary cases, assertions, and debugging with `pdb`. Learn property-based testing as a technique: check invariants across many generated inputs and token segmentations.

For constraints, the key property is that each admitted token leaves a valid prefix and each accepting state produces valid, schema-compliant data. For generation, a fake SDK makes token scores predictable and lets you test error paths cheaply.

Use separate measurements:

| Measurement | Question it answers |
| --- | --- |
| Coverage | Did every input produce the required result record? |
| JSON validity | Can every generated record/object be parsed? |
| Schema validity | Are exact keys and correct argument types present? |
| Function accuracy | Is the selected function correct? |
| Argument accuracy | Are the supplied values faithful to the request? |
| Overall accuracy | Are both function and arguments correct, counting failures? |
| Runtime | How long did the defined workload take on specified hardware? |

**Exercise:** build a test matrix covering empty schemas, shared name prefixes, long names, negative numbers, exponent numbers, booleans, escaped strings, multi-character tokens, invalid input files, duplicate definitions, unsupported types, and token-limit exhaustion.

**Checkpoint:** explain why an existing result file is neither a trustworthy expected-output fixture nor a current benchmark without checking its content and provenance. In this repo it has three missing-argument records and one visibly wrong reversal argument.

**Read:** [Python unittest](https://docs.python.org/3/library/unittest.html). **Project anchors:** every error boundary and constraint transition.

## 17. Performance and complexity

Learn Big-O notation, linear scans, set lookup, trie traversal, caching, profiling, and time measurement. Distinguish model inference cost from your own filtering cost and startup cost from steady processing.

`ids_where` visits the whole vocabulary each time. A Boolean mask and `argmax` also touch a vocabulary-sized array. The name filter additionally compares reachable name suffixes. Two generation passes per prompt multiply the work; larger contexts can affect inference cost depending on the SDK.

Learn memoization and precomputed indexes only after you can prove they preserve grammar behavior. Cache keys must contain every part of state affecting legality, including remaining fields or value progress when relevant.

**Exercise:** time repeated vocabulary scans with a synthetic vocabulary of increasing size. Measure filtering separately from fake-model scoring. Identify which results can safely be cached.

**Checkpoint:** explain why “at most 512 logits calls per prompt” is a bound derived from two 256-step loops, not proof that the program meets the five-minute target.

**Project anchors:** [vocab.py](../../src/vocab.py) and [generator.py](../../src/generator.py).

## 18. Packaging, CLI, style, and submission

Learn virtual environments, direct and transitive dependencies, dependency resolution, lockfiles, platform markers, package wheels, editable local dependencies, and build backends. You do not need to memorize every package in `uv.lock`; you need to understand why it records many more packages than the three direct dependencies in `pyproject.toml`.

Learn `argparse`, CLI flag spelling, defaults, help messages, logging levels, and exit statuses. Study Makefile targets and tab-indented recipes, `.gitignore` patterns, flake8, mypy, and PEP 257 docstrings.

The subject requires Makefile targets `install`, `run`, `debug`, `clean`, and `lint`; `lint-strict` is optional. The Makefile is currently empty. Its mandatory lint commands are:

```sh
flake8 .
mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports \
  --disallow-untyped-defs --check-untyped-defs
```

These are requirements to implement and verify, not checks reported as passing. The current project does not declare flake8 or mypy as development dependencies. Cleanup targets should remove known generated artifacts without deleting source or input data.

**Exercise:** sketch the five required Makefile targets, document the configured execution command, and compare every CLI flag against the subject. Explain why `venv` in `.gitignore` does not cover a folder named `.venv`.

**Checkpoint:** describe how a fresh checkout is expected to work with the provided SDK folder and `uv sync`, and why a root README needs accurate setup steps and measured claims.

**Read:** [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/), [GNU Make overview](https://www.gnu.org/software/make/manual/html_node/Overview), [flake8](https://flake8.pycqa.org/en/latest/), and [PEP 257](https://peps.python.org/pep-0257/).

## Build it again in small milestones

Use this order when you are ready to implement your own version:

| Milestone | Deliverable | Evidence that it works |
| --- | --- | --- |
| 1 | Written input/output contract and hand-written examples | You can distinguish call arguments from execution results. |
| 2 | Input models and JSON I/O | Valid files load; malformed inputs produce useful errors. |
| 3 | Exact runtime call validator | Missing, extra, and mistyped arguments are rejected. |
| 4 | Verified public SDK adapter and token representation | Shapes, ID alignment, and encode/decode assumptions are established. |
| 5 | Name constraint | Tests cover prefix names, long names, and alternate token splits. |
| 6 | Primitive value grammars | Numbers, booleans, strings, and escapes pass positive/negative tests. |
| 7 | Object grammar tied to a schema | Completion requires every required value; empty schemas work. |
| 8 | Masked generation with a fake model | Invalid high scores are blocked; dead ends and limits fail clearly. |
| 9 | Two-stage caller and batch CLI | Outputs preserve prompt order and failures follow a deliberate policy. |
| 10 | Required-model evaluation | Report coverage, validity, semantic accuracy, and timed workload. |
| 11 | Submission files and documentation | Required commands, checks, and explanation match actual behavior. |

Do not treat the current code's defects as fixed merely because a better design is described here. Each milestone needs its own evidence.

## Final self-check

You are ready to defend your solution when you can answer these questions with a small example:

1. What does this program produce, and where would tool execution happen later?
2. How do text, tokens, token IDs, logits, masks, and decoded output connect?
3. How does a trie keep function names within the catalog while preserving valid longer names?
4. What does a state machine need to remember to enforce required fields and value grammar?
5. How do you validate a token spanning multiple syntax positions?
6. When is a JSON prefix incomplete, invalid, or complete?
7. Why do valid JSON, valid schema, and correct meaning differ?
8. What happens on an empty legal set, unusable logits, or a token limit?
9. Which failures are caught at each application boundary?
10. What evidence supports your accuracy and runtime claims?
11. How would you adapt to unseen function names, parameter names, and prompts?
12. Can you modify one rule, add a meaningful regression test, and explain the consequences?

AI assisted with writing this roadmap after reviewing the permitted repository files and probing selected constraint behaviors. It is a study plan, not proof of mastery or a claim that the listed improvements are already implemented.
