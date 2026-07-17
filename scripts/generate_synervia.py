"""Generate the fixed Synervia product baseline from the local template."""

import argparse
from pathlib import Path

from fastapi_gen.generator import generate_project, post_generation_tasks
from fastapi_gen.product_profiles import get_synervia_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("product"),
        help="Parent directory for the generated synervia project (default: product)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config = get_synervia_config()
    project_path = generate_project(config, output_dir)
    post_generation_tasks(project_path, config)


if __name__ == "__main__":
    main()
