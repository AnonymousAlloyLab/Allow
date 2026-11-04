#!/usr/bin/env python3
"""Build and test the local G1 workbench without publishing or ingesting data."""
from pathlib import Path
import os
import shutil
import subprocess
from bootstrap import checkstyle, maven

ROOT = Path(__file__).resolve().parents[1]

def checked(command, cwd):
    """Run one explicit argument-array build step, stopping on the first failure."""
    subprocess.run(command, cwd=cwd, check=True)

def main():
    """Verify all authored code and assemble React assets into the Spring classpath."""
    os.environ['ALLOW_CHECKSTYLE_JAR'] = str(checkstyle())
    checked(['npm', 'ci', '--no-audit', '--no-fund'], ROOT / 'frontend')
    checked(['node', 'scripts/check-code-style.mjs'], ROOT)
    checked(['node', 'scripts/test-code-style.mjs'], ROOT)
    checked(['npm', 'test'], ROOT / 'frontend')
    checked(['npm', 'run', 'build'], ROOT / 'frontend')
    checked([str(maven()), '-B', 'verify'], ROOT / 'backend')
    target = ROOT / 'backend/target/classes/static'
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ROOT / 'frontend/dist', target)
    print('Local build and tests passed. Run: python3 scripts/run_local.py --show-url')

if __name__ == '__main__':
    main()
