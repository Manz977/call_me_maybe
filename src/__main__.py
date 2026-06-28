import argparse
import logging
import sys

from .caller import FunctionCaller
from .generator import ControlledGenerationError, Generator
from .loader import JsonIO, JsonIOErorr
from .models import FunctionCall
from .vocab import Vocabulary

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run constrained function-call generation.")
    parser.add_argument(
        "--functions-definition",
        default="data/input/functions_definition.json",
        metavar="PATH",
    )
    parser.add_argument(
        "--input",
        default="data/input/function_calling_tests.json",
        metavar="PATH",
    )
    parser.add_argument(
        "--output",
        default="data/output/function_calling_results.json",
        metavar="PATH",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-0.6B",
        metavar="HF_MODEL_ID",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    try:
        funcs = JsonIO.load_function_definitions(args.functions_definition)
        prompts = JsonIO.load_prompts(args.input)
    except JsonIOErorr as exc:
        print(f"Error loading input files: {exc}", file=sys.stderr)
        sys.exit(1)

    log.info("Loaded %d function(s) and %d prompt(s).", len(funcs), len(prompts))

    try:
        from llm_sdk import Small_LLM_Model  # type: ignore[import-untyped]
        model = Small_LLM_Model(args.model)
        vocab = Vocabulary(model.get_path_to_vocab_file())
    except Exception as exc:
        print(f"Error initialising model: {exc}", file=sys.stderr)
        sys.exit(1)

    functions_by_name = {fn.name: fn for fn in funcs}
    generator = Generator(model, vocab)
    caller = FunctionCaller(generator, vocab, functions_by_name)

    records: list[FunctionCall] = []
    for prompt in prompts:
        try:
            record = caller.process(prompt)
            records.append(record)
            log.info("OK  %r -> %s(%s)", prompt, record.name, record.parameters)
        except ControlledGenerationError as exc:
            log.warning("Skipping prompt %r: %s", prompt, exc)

    try:
        JsonIO.write_results(args.output, records)
    except JsonIOErorr as exc:
        print(f"Error writing output: {exc}", file=sys.stderr)
        sys.exit(1)

    log.info("Wrote %d result(s) to %s.", len(records), args.output)


if __name__ == "__main__":
    main()
