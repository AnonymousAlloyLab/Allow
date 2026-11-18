#!/usr/bin/env python3
"""Verify the packaged ACGN reference against local Git objects, offline."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acgn_repository", type=Path, help="local ACGN Git repository")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    reference = json.loads((root / "backend/src/main/resources/profiles/acgn-reference.json").read_text())
    contract = json.loads((root / "spec/saved-analysis-upgrade.json").read_text())["reference"]
    for key in ("project", "tag", "commit", "tree"):
        if reference[key] != contract[key]:
            raise ValueError(f"reference disagrees with contract: {key}")
    if reference["role"] != "canonicalization-reference":
        raise ValueError("unexpected reference role")

    def git(*arguments):
        return subprocess.run(
            ["git", "--no-replace-objects", "-C", str(args.acgn_repository), *arguments],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout

    tag = "refs/tags/" + reference["tag"]
    for expression, expected in ((tag + "^{tag}", reference["tagObject"]),
                                 (tag + "^{commit}", reference["commit"]),
                                 (tag + "^{tree}", reference["tree"])):
        actual = git("rev-parse", "--verify", expression).decode("ascii").strip()
        if actual != expected:
            raise ValueError(f"Git object mismatch: {expression}")
    jar = git("show", reference["commit"] + ":lib/alloy.jar")
    if hashlib.sha256(jar).hexdigest() != reference["taggedAlloyJarSha256"]:
        raise ValueError("tagged Alloy jar hash mismatch")
    print(f"Verified ACGN {reference['tag']} reference at {reference['commit']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ACGN reference verification failed: {error}", file=sys.stderr)
        sys.exit(1)
