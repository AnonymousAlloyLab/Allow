"""Fail-closed admission of exact PostgreSQL SQL bytes through the pinned grammar."""
from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROFILE = 'postgresql-16.15-grammar-v0.1'
COMMIT = 'f0595c3d839debdb140903621c1b44a4f4d86256'
MAX_SQL = 1048576
MAX_OUTPUT = 16777216
FORBIDDEN = {'DoStmt', 'CreateFunctionStmt', 'PrepareStmt', 'ExecuteStmt', 'CallStmt',
             'LoadStmt', 'DeallocateStmt', 'AlterSystemStmt', 'AlterRoleSetStmt', 'AlterDatabaseSetStmt', 'DiscardStmt'}
# These exact standalone statements are needed by the owned bootstrap and pg_dump.
SAFE_SET = re.compile(r'''(?ix)\A\s*(?:
 SET\s+(?:statement_timeout|lock_timeout|idle_in_transaction_session_timeout|transaction_timeout)\s*=\s*0 |
 SET\s+client_encoding\s*=\s*'UTF8' |
 SET\s+standard_conforming_strings\s*=\s*(?:on|'on') |
 SET\s+DATESTYLE\s*=\s*ISO |
 SET\s+INTERVALSTYLE\s*=\s*POSTGRES |
 SET\s+extra_float_digits\s+(?:TO|=)\s*3 |
 SET\s+synchronize_seqscans\s+TO\s+off |
 SET\s+TRANSACTION\s+ISOLATION\s+LEVEL\s+REPEATABLE\s+READ,\s*READ\s+ONLY |
 SET\s+check_function_bodies\s*=\s*false |
 SET\s+xmloption\s*=\s*content |
 SET\s+client_min_messages\s*=\s*warning |
 SET\s+row_security\s*=\s*off |
 SET\s+default_tablespace\s*=\s*'' |
 SET\s+default_table_access_method\s*=\s*heap |
 SET\s+(?:LOCAL\s+)?ROLE\s+allow_owner | RESET\s+ROLE
 )\s*;?\s*\Z''')
SAFE_CONFIG = re.compile(r"(?is)\A\s*SELECT\s+(?:pg_catalog\.)?set_config\s*\(\s*'(?:allow\.tenant|allow\.project|allow\.purpose|search_path)'\s*,\s*(?:\$[1-9][0-9]*|'' )\s*,\s*(?:true|false)\s*\)\s*;?\s*\Z".replace("'' ", "''"))
SAFE_EXTENSION = re.compile(r'(?is)\A\s*CREATE\s+EXTENSION\s+(?:IF\s+NOT\s+EXISTS\s+)?vector(?:\s+WITH\s+SCHEMA\s+public)?\s*;?\s*\Z')
SAFE_DUMP_CONFIG = re.compile(r"(?is)\A\s*SELECT\s+set_config\(name,\s*'view(?:, foreign-table)?',\s*false\)\s+FROM\s+pg_settings\s+WHERE\s+name\s*=\s*'restrict_nonsystem_relation_kind'\s*;?\s*\Z")

class SQLGuardError(ValueError):
    """SQL cannot be admitted; the message contains no SQL or credentials."""

def _duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise SQLGuardError('duplicate parser field')
        out[k] = v
    return out

def _sha(path):
    with path.open('rb') as f:
        h = hashlib.sha256()
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
        return h.hexdigest()

class ParserGate:
    def __init__(self):
        self.binary = ROOT/'.tools/sqlean/sqlean_pg_grammar'
        try:
            lock = json.loads((ROOT/'config/sqlean-parser-lock.json').read_text(), object_pairs_hook=_duplicates)
            if lock['profile'] != PROFILE or lock['postgresql_commit'] != COMMIT: raise SQLGuardError('parser profile mismatch')
            self.digest = lock['binary_sha256']
            self.lhs = lock['production_lhs']
            if not isinstance(self.lhs, list) or not all(isinstance(x,str) for x in self.lhs): raise SQLGuardError('invalid production mapping')
            self._identity()
        except (OSError, KeyError, ValueError, TypeError) as e:
            raise SQLGuardError('parser identity unavailable') from e
        self._cache = OrderedDict()
        self._cache_bytes = 0
        self._lock = threading.Lock()
        self._slots = threading.BoundedSemaphore(2)

    @property
    def info(self):
        return {'profile': PROFILE, 'binary_sha256': self.digest, 'policy': 'sql-routing-v1'}

    def _identity(self):
        if _sha(self.binary) != self.digest: raise SQLGuardError('parser identity mismatch')

    def validate(self, sql: bytes) -> None:
        if not isinstance(sql, bytes) or len(sql) > MAX_SQL or b'\x00' in sql:
            raise SQLGuardError('invalid SQL bytes')
        try:
            source = sql.decode('utf-8', 'strict')
            self._identity()
            with self._lock:
                if sql in self._cache:
                    self._cache.move_to_end(sql)
                    return
            with self._slots:
                self._identity()
                try:
                    with tempfile.TemporaryFile(mode='w+b', dir='/dev/shm') as out:
                        try:
                            proc = subprocess.run(['prlimit','--as=1073741824','--cpu=6','--core=0','--fsize=16777216','--',str(self.binary),'--max-transitions','1000000'], input=sql, stdout=out, stderr=subprocess.DEVNULL, timeout=5, check=False, env={'LEAN_NUM_THREADS':'1','PATH':'/usr/bin:/bin'})
                        except (subprocess.TimeoutExpired, OSError) as e:
                            raise SQLGuardError('parser unavailable') from e
                        if proc.returncode != 0: raise SQLGuardError('parser rejected')
                        size = out.tell()
                        if size > MAX_OUTPUT: raise SQLGuardError('parser output too large')
                        out.seek(0)
                        raw = out.read(MAX_OUTPUT+1)
                except OSError as e:
                    raise SQLGuardError('parser output unavailable') from e
                if not raw.endswith(b'\n') or raw.count(b'\n') != 1:
                    raise SQLGuardError('parser response framing')
                report = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=_duplicates,
                                    parse_constant=lambda _: (_ for _ in ()).throw(SQLGuardError('invalid JSON constant')))
                if not isinstance(report, dict) or any(report.get(k) != v for k,v in {
                    'status':'grammar-accepted', 'evidence':'context-free-derivation', 'profile':PROFILE,
                    'postgresqlCommit':COMMIT, 'sourcePreservation':'exact', 'sql':source}.items()):
                    raise SQLGuardError('parser evidence mismatch')
                ids = report.get('productionIds')
                if not isinstance(ids, list) or any(type(i) is not int or i < 0 or i >= len(self.lhs) for i in ids):
                    raise SQLGuardError('invalid productions')
                families = {self.lhs[i] for i in ids}
                if families & FORBIDDEN: raise SQLGuardError('forbidden statement')
                if families & {'VariableSetStmt','VariableResetStmt'} and not SAFE_SET.fullmatch(source):
                    raise SQLGuardError('unreviewed setting')
                if 'CreateExtensionStmt' in families and not SAFE_EXTENSION.fullmatch(source):
                    raise SQLGuardError('unreviewed extension')
                tokens = report.get('tokens')
                if not isinstance(tokens,list) or any(not isinstance(t,dict) or not isinstance(t.get('lexeme'),str) or not isinstance(t.get('kind'),str) for t in tokens):
                    raise SQLGuardError('invalid tokens')
                # Examine identifier tokens, not string/comment contents. Unicode escaped
                # identifiers are denied because their resolved name needs decoding.
                for t in tokens:
                    lex, kind = t['lexeme'], t['kind']
                    if kind == 'IDENT':
                        if lex.lower().startswith('u&"'): raise SQLGuardError('unicode identifier')
                        if lex.strip('"').lower() == 'set_config' and not (
                                SAFE_CONFIG.fullmatch(source) or SAFE_DUMP_CONFIG.fullmatch(source)):
                            raise SQLGuardError('unreviewed set_config')
                if 'TransactionStmt' in families and any(t['lexeme'].upper() in {'PREPARED', 'PREPARE'} and t['kind'] != 'SCONST' for t in tokens):
                    raise SQLGuardError('prepared transaction forbidden')
                if 'CopyStmt' in families and any(t['lexeme'].lower() == 'program' and t['kind'] != 'SCONST' for t in tokens):
                    raise SQLGuardError('copy program forbidden')
            self._identity()
            with self._lock:
                if sql not in self._cache:
                    self._cache[sql] = None
                    self._cache_bytes += len(sql)
                    while len(self._cache) > 256 or self._cache_bytes > 4194304:
                        key, _ = self._cache.popitem(last=False)
                        self._cache_bytes -= len(key)
        except (UnicodeError, OSError, json.JSONDecodeError, RecursionError, TypeError, KeyError) as e:
            raise SQLGuardError('parser admission failed') from e
