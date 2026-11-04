"""Connection policy and explicit migration recovery through the canonical proxy."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid
from allow_retrieval.sql_connections import (
    ConnectionPolicyError,PROXY_DIRECTORY,validate_dsn,connect,configured_dsn,database_dsn)
from allow_retrieval.migration import apply_migrations

class ConnectionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.environment=patch.dict(os.environ,{},clear=True);self.environment.start()
        self.base=f'host={PROXY_DIRECTORY} port=54329 dbname=allow_retrieval user=allow_app password=fixture'
    def tearDown(self):self.environment.stop()
    def test_canonical_route_and_safe_startup(self):
        from psycopg.conninfo import conninfo_to_dict
        fields=conninfo_to_dict(validate_dsn(self.base))
        self.assertEqual(fields['host'],str(PROXY_DIRECTORY))
        self.assertEqual(fields['client_encoding'],'UTF8');self.assertEqual(fields['options'],'')
        self.assertEqual(fields['sslmode'],'disable')
    def test_bypass_and_ambient_routes_fail_closed(self):
        for altered in (self.base.replace(str(PROXY_DIRECTORY),'127.0.0.1'),
                        self.base.replace(str(PROXY_DIRECTORY),str(PROXY_DIRECTORY).replace('sql-proxy','postgres')),
                        self.base+' hostaddr=127.0.0.1',self.base+' service=other',
                        self.base+' host='+str(PROXY_DIRECTORY)+',/tmp',
                        self.base+" options='-c client_encoding=LATIN1'",
                        self.base+' client_encoding=LATIN1',self.base.replace('allow_app','allow_admin')):
            with self.assertRaises(ConnectionPolicyError):validate_dsn(altered)
        for key in ('ALLOW_RETRIEVAL_DSN','PGHOST','PGSERVICE','PGOPTIONS'):
            with patch.dict(os.environ,{key:'untrusted'}):
                with self.assertRaises(ConnectionPolicyError):validate_dsn(self.base)
    def test_database_variation_and_kwargs_are_bounded(self):
        from psycopg.conninfo import conninfo_to_dict
        temporary='allow_recovery_'+uuid.uuid4().hex
        routed=database_dsn(self.base,temporary)
        self.assertEqual(conninfo_to_dict(routed)['host'],str(PROXY_DIRECTORY))
        with self.assertRaises(ConnectionPolicyError):validate_dsn(routed)
        with self.assertRaises(ConnectionPolicyError):database_dsn(self.base,'unrelated_project')
        with self.assertRaises(ConnectionPolicyError):connect(self.base,host='/tmp')

class ExplicitMigrationTests(unittest.TestCase):
    def test_fresh_existing_and_partial_constraint_repair(self):
        from psycopg import sql
        from psycopg.rows import dict_row
        name='allow_sql_test_'+uuid.uuid4().hex
        admin=configured_dsn(admin=True,client='allow-tests')
        with connect(admin,admin=True,autocommit=True,client='allow-tests') as controls:
            controls.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            try:
                dsn=database_dsn(admin,name,admin=True,client='allow-tests')
                with connect(dsn,admin=True,allow_temporary=True,client='allow-tests',row_factory=dict_row) as c:
                    first=apply_migrations(c)
                    self.assertEqual(first['tables'],14)
                    self.assertGreater(first['constraints_added'],0)
                    second=apply_migrations(c)
                    self.assertEqual(second['constraints_added'],0)
                    c.execute('ALTER TABLE retrieval.membership DROP CONSTRAINT membership_own_query')
                    c.commit()
                    repaired=apply_migrations(c)
                    self.assertEqual(repaired['constraints_added'],1)
                    row=c.execute("SELECT count(*) AS n FROM pg_constraint WHERE connamespace='retrieval'::regnamespace AND conname IN ('run_query_member_identity','membership_own_query')").fetchone()
                    self.assertEqual(row['n'],2)
                    flags=c.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='retrieval.record'::regclass").fetchone()
                    self.assertTrue(flags['relrowsecurity']);self.assertTrue(flags['relforcerowsecurity'])
                    grant=c.execute("SELECT has_table_privilege('allow_app','retrieval.training_variant','DELETE') AS allowed").fetchone()
                    self.assertFalse(grant['allowed'])
                    import json
                    manifest=json.loads(Path('db/migrations/005_expected_catalog.json').read_text())['catalog']
                    for table,kind in (('training_variant','f'),('record','c')):
                        constraint=next(x for x in manifest['constraints'] if x['table_name']==table and x['type']==kind)
                        c.execute(f"ALTER TABLE retrieval.{table} DROP CONSTRAINT {constraint['name']}")
                        c.commit()
                        with self.assertRaisesRegex(ValueError,'schema_catalog_mismatch'):apply_migrations(c)
                        c.execute(f"ALTER TABLE retrieval.{table} ADD CONSTRAINT {constraint['name']} {constraint['definition']}")
                        c.commit()
                    c.execute('ALTER TABLE retrieval.artifact ALTER COLUMN locator TYPE varchar')
                    c.commit()
                    with self.assertRaisesRegex(ValueError,'schema_catalog_mismatch'):apply_migrations(c)
                    c.execute('ALTER TABLE retrieval.artifact ALTER COLUMN locator TYPE text')
                    c.commit()
                    self.assertEqual(apply_migrations(c)['constraints_added'],0)
            finally:
                controls.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))

if __name__=='__main__':unittest.main()
