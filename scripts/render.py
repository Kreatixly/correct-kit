#!/usr/bin/env python3
"""Fill {{PLACEHOLDER}} values in correct-kit templates.

    python scripts/render.py <values.json> <template> <output>

values.json maps placeholder names to strings. Multi-line values keep their own
indentation (write them already indented for their place in the YAML). Fails if
a placeholder in the template has no value, so nothing half-filled is written.
Standard library only.
"""
import json
import re
import sys


def main() -> int:
    values_path, template_path, out_path = sys.argv[1:4]
    values = json.load(open(values_path, encoding="utf-8"))
    text = open(template_path, encoding="utf-8").read()
    missing = sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", text)) - set(values))
    if missing:
        print(f"{template_path}: no value for {', '.join(missing)}", file=sys.stderr)
        return 1
    text = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: str(values[m.group(1)]), text)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
