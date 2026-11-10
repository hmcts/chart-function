"""Update this consumer using the migration engine from a trusted library checkout."""

import argparse
import importlib.util
import json
import re
import subprocess
import tempfile
from pathlib import Path


def command(*args: str, cwd: Path) -> str:
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def library_version(chart: Path) -> str:
    # Helm parses Chart.yaml without adding a Python YAML dependency or pulling OCI packages.
    rows = command("helm", "dependency", "list", str(chart), cwd=chart.parent).splitlines()
    versions = [fields[1] for row in rows
                if len(fields := row.split()) >= 2 and fields[0] == "library"]
    if len(versions) != 1 or not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", versions[0]):
        raise ValueError("Expected exactly one library dependency with an exact stable version")
    return versions[0]


def migrate(consumer: Path, library: Path, base: str) -> dict:
    consumer = consumer.resolve()
    chart = consumer / "function"
    original = command("git", "show", f"{base}:function/Chart.yaml", cwd=consumer)
    with tempfile.TemporaryDirectory() as directory:
        baseline = Path(directory)
        (baseline / "Chart.yaml").write_text(original)
        previous = library_version(baseline)
    target = library_version(chart)
    result = {"base": previous, "target": target, "rewrites": {}}
    if previous == target:
        return result
    if tuple(map(int, previous.split("."))) >= tuple(map(int, target.split("."))):
        raise ValueError("Library downgrades require manual intervention")
    spec = importlib.util.spec_from_file_location(
        "template_migrations", library.resolve() / "scripts/template_migrations.py")
    if spec is None or spec.loader is None:
        raise ValueError("Cannot load shared library migration tooling")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    report = engine.history(library.resolve(), previous, target)
    sources = {entry["from"] for entry in report["changes"]}
    for path in sorted((chart / "templates").rglob("*")):
        if not path.is_file():
            continue
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise ValueError(f"Refusing a symlinked template: {path}")
        text = path.read_text()
        direct = {start for _, start, _ in engine.strings(text, {"include", "template"})}
        for action in engine.ACTION.finditer(text):
            body = action.group()
            if re.match(r"{{-?\s*/\*", body):
                continue
            for token in engine.TOKEN.finditer(body[2:-2]):
                literal = token.group()
                if not literal.startswith(('"', "`")):
                    continue
                name = json.loads(literal) if literal.startswith('"') else literal[1:-1]
                if name in sources and action.start() + 2 + token.start() not in direct:
                    raise ValueError(f"Indirect or overridden helper requires manual migration: {path}: {name}")
    result["rewrites"] = engine.rewrite(chart, [report])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", type=Path, default=Path.cwd())
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--base", required=True, help="Consumer commit before the dependency update")
    args = parser.parse_args()
    try:
        print(json.dumps(migrate(args.consumer, args.library, args.base), indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        detail = error.stderr if isinstance(error, subprocess.CalledProcessError) else str(error)
        parser.exit(1, f"Consumer migration failed: {detail}\n")


if __name__ == "__main__":
    main()
