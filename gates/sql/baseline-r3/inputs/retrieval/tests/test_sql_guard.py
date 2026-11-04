import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from allow_retrieval.sql_guard import ParserGate, SQLGuardError

class RealParserGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = ParserGate()

    def test_normal_and_literals(self):
        for sql in (b'SELECT 1', b"SELECT 'DO $$; set_config; COPY PROGRAM'", b'SELECT $1::text',
                    b"SELECT set_config('allow.tenant',$1,true)", b'CREATE EXTENSION IF NOT EXISTS vector;'):
            with self.subTest(sql=sql): self.gate.validate(sql)

    def test_nested_opaque_and_protocol_state(self):
        for sql in (b'EXPLAIN EXECUTE x', b'DO $$ BEGIN END $$', b'PREPARE x AS SELECT 1',
                    b"PREPARE TRANSACTION 'x'", b"COMMIT PREPARED 'x'", b'DEALLOCATE ALL',
                    b'CALL foo()', b"LOAD 'x'", b"COPY t TO PROGRAM 'cat'", b'CREATE EXTENSION hstore'):
            with self.subTest(sql=sql), self.assertRaises(SQLGuardError): self.gate.validate(sql)

    def test_pinned_dump_restore_templates(self):
        statements = [b'CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;',
                      b'SET DATESTYLE = ISO', b'SET INTERVALSTYLE = POSTGRES',
                      b'SET extra_float_digits TO 3', b'SET synchronize_seqscans TO off',
                      b'SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY',
                      b"SET standard_conforming_strings = 'on';",
                      b"SELECT set_config('allow.purpose',$1,true)"]
        template = "SELECT set_config(name, '{}', false) FROM pg_settings WHERE name = '{}'"
        for value in ('view', 'view, foreign-table'):
            statements.append(template.format(value, 'restrict_nonsystem_relation_kind').encode())
        for sql in statements:
            with self.subTest(sql=sql): self.gate.validate(sql)
        for sql in [b'CREATE EXTENSION vector WITH SCHEMA other;',
                    template.format('LATIN1', 'client_encoding').encode(),
                    template.format('off', 'standard_conforming_strings').encode(),
                    statements[0] + b' SELECT 1;']:
            with self.subTest(sql=sql), self.assertRaises(SQLGuardError): self.gate.validate(sql)

    def test_modes_and_pipeline(self):
        for sql in (b'SET client_encoding TO LATIN1', b'SELECT 1; SET standard_conforming_strings=off',
                    b"SELECT set_config('client_encoding','LATIN1',false)",
                    b'''SELECT U&"set_config"('client_encoding','LATIN1',false)''',
                    b"SELECT set_config($1,$2,true)"):
            with self.subTest(sql=sql), self.assertRaises(SQLGuardError): self.gate.validate(sql)
        self.gate.validate(b"SET client_encoding = 'UTF8';")
        self.gate.validate(b'SET standard_conforming_strings = on;')

    def test_malformed_and_binary_tamper_after_cache(self):
        for sql in (b'\xff', b'SELECT 1\0', b'x' * 1048577, b'SELECT FROM FROM'):
            with self.subTest(length=len(sql)), self.assertRaises(SQLGuardError): self.gate.validate(sql)
        gate = ParserGate()
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory)/'parser'
            shutil.copy2(gate.binary, binary)
            gate.binary = binary
            gate.validate(b'SELECT 1')
            with binary.open('ab') as f: f.write(b'tamper')
            with self.assertRaises(SQLGuardError): gate.validate(b'SELECT 1')

if __name__ == '__main__': unittest.main()
