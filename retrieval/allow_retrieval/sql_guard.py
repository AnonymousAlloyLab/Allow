"""Fail-closed admission of exact PostgreSQL SQL bytes through the pinned grammar."""
from collections import OrderedDict, Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

from .sql_context_protocol import is_context_setting, is_public_setting

ROOT = Path(__file__).resolve().parents[2]
PROFILE = 'postgresql-16.15-grammar-v0.1'
COMMIT = 'f0595c3d839debdb140903621c1b44a4f4d86256'
MAX_SQL = 1048576
MAX_OUTPUT = 16777216
FORBIDDEN = {'DoStmt', 'CreateFunctionStmt', 'CallStmt',
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

@dataclass(frozen=True)
class NativeDecision:
    kind: str
    name: bytes
    body_span: tuple[int, int] | None


def _native_decision(sql, tokens, family_names, production_names):
    native = production_names & {'PrepareStmt', 'ExecuteStmt'}
    if not native:
        return None
    if len(native) != 1 or len(tokens) < 2:
        raise SQLGuardError('nested native statement')
    family = next(iter(native))
    keyword = 'PREPARE' if family == 'PrepareStmt' else 'EXECUTE'
    if family_names != [family] or tokens[0]['kind'] != keyword or tokens[0]['lexeme'].upper() != keyword:
        raise SQLGuardError('native statement is not sole top-level statement')
    name = tokens[1]['lexeme']
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', name, flags=re.ASCII):
        raise SQLGuardError('invalid native statement name')
    # The grammar reports empty statements separately only as missing families;
    # conservatively permit at most one final SQL semicolon.
    semicolons = [i for i, token in enumerate(tokens) if token['lexeme'] == ';']
    if semicolons and semicolons != [len(tokens) - 1]:
        raise SQLGuardError('multiple native statements')
    if keyword == 'EXECUTE':
        return NativeDecision('execute', name.lower().encode('ascii'), None)
    i = 2
    if i < len(tokens) and tokens[i]['lexeme'] == '(':
        depth = 0
        while i < len(tokens):
            lexeme = tokens[i]['lexeme']
            if lexeme == '(':
                depth += 1
            elif lexeme == ')':
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        if depth != 0:
            raise SQLGuardError('invalid native parameter declaration')
    if i >= len(tokens) or tokens[i]['kind'] != 'AS' or tokens[i]['lexeme'].upper() != 'AS':
        raise SQLGuardError('invalid native prepare body')
    i += 1
    if i >= len(tokens) or tokens[i]['lexeme'] == ';':
        raise SQLGuardError('empty native prepare body')
    start = tokens[i]['start']
    end = tokens[-1]['start'] if semicolons else len(sql)
    if not 0 <= start < end <= len(sql) or not sql[start:end].strip():
        raise SQLGuardError('invalid native prepare body span')
    return NativeDecision('prepare', name.lower().encode('ascii'), (start, end))


class SQLGuardError(ValueError):
    """SQL cannot be admitted; the message contains no SQL or credentials."""
    def __init__(self, message, *, category='policyDenied'):
        super().__init__(message)
        self.category = category

def _duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise SQLGuardError('duplicate parser field', category='parserFailure')
        out[k] = v
    return out

class ParserGate:
    """Every admission uses one sealed executable and immutable interpretation snapshot."""
    def __init__(self, *, source=None, lock_path=None):
        from .sql_image_config import ConfigSnapshot, workspace_root
        from .sql_image import SealedImage
        root = workspace_root()
        self._binary = Path(source) if source is not None else root/'.tools/sqlean/sqlean_pg_grammar'
        self._config = ConfigSnapshot.load(lock_path or root/'config/sqlean-parser-lock.json')
        self._image = SealedImage(self._binary, self._config)
        self._cache = OrderedDict()
        self._cache_bytes = 0
        self._reasons = Counter()

    @property
    def binary(self):
        """Diagnostic original source path; never resolved again for admission/execution."""
        return self._binary

    @property
    def digest(self):
        return self._config.binary_sha256

    @property
    def lhs(self):
        return self._config.production_lhs

    @property
    def info(self):
        with self._image.lock:
            status = self._image.status_locked(self._config)
            status['failure_counts'] = dict(self._reasons)
            status['cache_entries'] = len(self._cache)
            status['cache_sql_bytes'] = self._cache_bytes
            return status

    def close(self):
        with self._image.lock:
            self._image.close_locked()
            self._cache.clear()
            self._cache_bytes = 0
        self._image.finish_close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _identity(self):
        with self._image.lock:
            self._image.check_locked(self._config)

    def _cache_insert_locked(self, key, decision):
        if key not in self._cache:
            self._cache[key] = decision
            self._cache_bytes += len(key[2])
            while len(self._cache) > 256 or self._cache_bytes > 4194304:
                removed, _ = self._cache.popitem(last=False)
                self._cache_bytes -= len(removed[2])

    def validate(self, sql: bytes, *, cancel=None) -> NativeDecision | None:
        from .sql_image_config import ImageError
        if not isinstance(sql, bytes) or len(sql) > MAX_SQL or b'\x00' in sql:
            with self._image.lock:
                self._reasons['policyDenied'] += 1
            raise SQLGuardError('invalid SQL bytes')
        config = self._config
        key = (config.digest, config.generation, sql)
        try:
            source = sql.decode('utf-8', 'strict')
        except UnicodeError as error:
            with self._image.lock:
                self._reasons['policyDenied'] += 1
            raise SQLGuardError('parser admission failed') from error
        try:
            with self._image.lock:
                self._image.check_locked(config)
                self._image.check_cancel(cancel)
                if key in self._cache:
                    self._cache.move_to_end(key)
                    return self._cache[key]
            with self._image.reserve(config, cancel) as owner:
                raw = self._image.run(owner, sql, config, cancel)
                decision = self._classify(sql, source, raw, config)
                with self._image.lock:
                    self._image.ensure_live(config)
                    self._image.check_cancel(cancel)
                    self._cache_insert_locked(key, decision)
                    return decision
        except SQLGuardError as error:
            with self._image.lock:
                self._reasons[error.category] += 1
            raise
        except ImageError as error:
            with self._image.lock:
                self._reasons[error.category] += 1
                if error.category == 'infrastructureFailure' and self._image._state != 'ready':
                    self._cache.clear()
                    self._cache_bytes = 0
            raise SQLGuardError(str(error), category=error.category) from error
        except (UnicodeError, OSError, json.JSONDecodeError, RecursionError, TypeError, KeyError) as error:
            with self._image.lock:
                self._reasons['parserFailure'] += 1
            raise SQLGuardError('parser admission failed', category='parserFailure') from error

    def _classify(self, sql, source, raw, config):
        """Revision6 report/SQL policy checks, interpreted through the same frozen mapping."""
        if not raw.endswith(b'\n') or raw.count(b'\n') != 1:
            raise SQLGuardError('parser response framing', category='parserFailure')
        report = json.loads(raw.decode('utf-8', 'strict'), object_pairs_hook=_duplicates,
                            parse_constant=lambda _: (_ for _ in ()).throw(SQLGuardError('invalid JSON constant', category='parserFailure')))
        if not isinstance(report, dict) or any(report.get(k) != v for k,v in {
            'status':'grammar-accepted', 'evidence':'context-free-derivation', 'profile':config.profile,
            'postgresqlCommit':config.commit, 'sourcePreservation':'exact', 'sql':source}.items()):
            raise SQLGuardError('parser evidence mismatch')
        ids = report.get('productionIds')
        if not isinstance(ids, list) or any(type(i) is not int or i < 0 or i >= len(config.production_lhs) for i in ids):
            raise SQLGuardError('invalid productions', category='parserFailure')
        families = {config.production_lhs[i] for i in ids}
        if families & FORBIDDEN: raise SQLGuardError('forbidden statement')
        if (families & {'VariableSetStmt','VariableResetStmt'}
                and not SAFE_SET.fullmatch(source) and not is_context_setting(sql) and not is_public_setting(sql)):
            raise SQLGuardError('unreviewed setting')
        if 'CreateExtensionStmt' in families and not SAFE_EXTENSION.fullmatch(source):
            raise SQLGuardError('unreviewed extension')
        tokens = report.get('tokens')
        if not isinstance(tokens,list) or any(not isinstance(t,dict) or not isinstance(t.get('lexeme'),str) or not isinstance(t.get('kind'),str) for t in tokens):
            raise SQLGuardError('invalid tokens', category='parserFailure')
        previous_end = 0
        for t in tokens:
            start, end = t.get('start'), t.get('end')
            if (type(start) is not int or type(end) is not int or
                    not previous_end <= start < end <= len(sql) or
                    sql[start:end] != t['lexeme'].encode('utf-8')):
                raise SQLGuardError('invalid token span', category='parserFailure')
            previous_end = end
        reported_families = report.get('statementFamilies')
        if not isinstance(reported_families, list) or not all(isinstance(f, str) for f in reported_families):
            raise SQLGuardError('invalid statement families', category='parserFailure')
        decision = _native_decision(sql, tokens, reported_families, families)
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
        return decision
