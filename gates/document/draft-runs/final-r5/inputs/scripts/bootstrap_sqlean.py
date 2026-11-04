#!/usr/bin/env python3
"""Build only the pinned PostgreSQL grammar source closure in the workspace."""
import hashlib
import json
import os
import sys
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('/home/augustus/SQLeanParser')
DEST = ROOT / '.tools/sqlean'
LOCK = ROOT / 'config/sqlean-parser-lock.json'
NOTICE = 'fixtures/postgresql_grammar/source/COPYRIGHT'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources(base):
    files = [base/'PostgresGrammarMain.lean', base/'SQLean/PostgresGrammar.lean', base/'lean-toolchain']
    files += sorted((base/'SQLean/PostgresGrammar').rglob('*.lean'))
    return {str(p.relative_to(base)): digest(p) for p in files}

def mapping(base):
    symbols = (base/'SQLean/PostgresGrammar/Generated/Symbols.lean').read_text().split('def nonterminals',1)[1].split(']',1)[0]
    names = {int(n):name for name,n in re.findall(r'\("([^"]+)",\s*(\d+)\)', symbols)}
    result = []
    for p in sorted((base/'SQLean/PostgresGrammar/Generated').glob('Productions*.lean')):
        for n in re.findall(r'^\s*⟨(\d+),\s*\[', p.read_text(), re.M):
            result.append(names[int(n)])
    if not result or 'DoStmt' not in result: raise RuntimeError('invalid production inventory')
    return result

def main():
    source_hashes = sources(REFERENCE)
    existing = json.loads(LOCK.read_text()) if LOCK.exists() else None
    if existing and source_hashes != existing['sources']:
        raise RuntimeError('reference source differs from pinned snapshot')
    notice_hash = digest(REFERENCE/NOTICE)
    if existing and existing.get('postgresql_copyright_sha256', notice_hash) != notice_hash:
        raise RuntimeError('PostgreSQL copyright notice differs from pinned snapshot')
    DEST.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REFERENCE/NOTICE, DEST/'POSTGRESQL-COPYRIGHT')
    for rel in source_hashes:
        target = DEST/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REFERENCE/rel, target)
    (DEST/'lakefile.toml').write_text('name = "sqlean_snapshot"\n[[lean_lib]]\nname = "SQLean"\n[[lean_exe]]\nname = "sqlean_pg_grammar"\nroot = "PostgresGrammarMain"\n')
    subprocess.run(['lake','build','sqlean_pg_grammar'], cwd=DEST, check=True)
    # Lean's executable defaults to 1 GiB per thread, so the runtime must be
    # configured before its task manager starts. The grammar sources are unchanged.
    wrapper = DEST/'runtime-stack.c'
    wrapper.write_text('extern void *lean_internal_set_thread_stack_size(unsigned long);\n__attribute__((constructor)) static void set_stack(void) { lean_internal_set_thread_stack_size(16ul * 1024 * 1024); }\n')
    lean_version = subprocess.check_output(['lean','--version'], cwd=DEST, text=True).strip()
    if not lean_version.startswith('Lean (version 4.34.0,'): raise RuntimeError('unexpected Lean toolchain')
    clang = Path(subprocess.check_output(['lean','--print-prefix'], cwd=DEST, text=True).strip())/'bin/clang'
    clang_version = subprocess.check_output([str(clang), '--version'], cwd=DEST, text=True).splitlines()[0]
    obj = DEST/'runtime-stack.o'
    binary = DEST/'sqlean_pg_grammar'
    candidate = DEST/'sqlean_pg_grammar.candidate'
    subprocess.run([str(clang), '-c', str(wrapper), '-o', str(obj)], cwd=DEST, check=True)
    subprocess.run([str(clang), '-o', str(candidate), str(obj), '@'+str(DEST/'.lake/build/bin/sqlean_pg_grammar.rsp')], cwd=DEST, check=True)
    meta = {'profile':'postgresql-16.15-grammar-v0.1','postgresql_commit':'f0595c3d839debdb140903621c1b44a4f4d86256','toolchain':'leanprover/lean4:v4.34.0','lean_version':lean_version,'clang_version':clang_version,'postgresql_copyright_sha256':notice_hash,'sources':source_hashes,'runtime_stack_wrapper_sha256':digest(wrapper),'runtime_stack_bytes':16777216,'binary_sha256':digest(candidate),'production_lhs':mapping(DEST),'license_notice':'No root LICENSE/NOTICE found in supplied reference checkout; local user-authorized use only; redistribution rights unresolved.'}
    if existing and meta != existing and '--refresh-lock' not in sys.argv:
        candidate.unlink()
        raise RuntimeError('rebuilt binary or metadata differs from lock')
    os.replace(candidate, binary)
    LOCK.write_text(json.dumps(meta,indent=2)+'\n')
    print('Pinned parser ready:', meta['binary_sha256'])
if __name__ == '__main__': main()
