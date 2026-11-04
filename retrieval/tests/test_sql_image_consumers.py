"""Offline consumer status checks; no database or active daemon access."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from allow_retrieval.sql_guard import ParserGate
from allow_retrieval.sql_image_config import workspace_root
from allow_retrieval.sql_inventory import source_names

HERE=Path(__file__).resolve().parents[1]
ROOT=workspace_root()


class ConsumerIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate=ParserGate()
        consumer=HERE/'promotion-proposals/scripts/verify_sql_runtime.py'
        if not consumer.is_file():consumer=ROOT/'scripts/verify_sql_runtime.py'
        specification=importlib.util.spec_from_file_location('staged_runtime_identity',consumer)
        cls.module=importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):cls.gate.close()

    def fixture(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);loaded={}
        for relative in source_names():
            source=ROOT/relative
            target=root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
            loaded[relative]=hashlib.sha256(target.read_bytes()).hexdigest()
        return root,{'pid':12345,'started':1,'loaded_inputs':loaded,'parser':self.gate.info}

    def test_missing_disk_is_restart_audit_only(self):
        root,status=self.fixture()
        with patch.object(self.module,'ROOT',root):result=self.module.runtime_identity(status)
        self.assertEqual(result['status'],'PASS')
        self.assertIsNone(result['actual_parser_binary_sha256'])
        self.assertIsNone(result['disk_binary_matches_pin'])
        self.assertEqual(result['disk_binary_audit_error'],'FileNotFoundError')

    def test_disk_mismatch_keeps_live_identity(self):
        root,status=self.fixture();binary=root/'.tools/sqlean/sqlean_pg_grammar';binary.parent.mkdir(parents=True);binary.write_bytes(b'changed')
        with patch.object(self.module,'ROOT',root):result=self.module.runtime_identity(status)
        self.assertEqual(result['status'],'PASS')
        self.assertFalse(result['disk_binary_matches_pin'])
        self.assertIsNone(result['disk_binary_audit_error'])

    def test_live_snapshot_still_checked_if_disk_missing(self):
        root,status=self.fixture();status=copy.deepcopy(status);status['parser']['policy']='changed'
        with patch.object(self.module,'ROOT',root):result=self.module.runtime_identity(status)
        self.assertEqual(result['status'],'STALE_RUNTIME')
        self.assertIn('daemon_sealed_snapshot_mismatch',result['reasons'])
        self.assertNotIn('runtime_identity_input_unavailable',result['reasons'])
