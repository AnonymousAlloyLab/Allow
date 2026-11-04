"""Independent Luna 2 fixtures using the isolated production worker and E5 encoder.

All inputs below are hand-authored toy Alloy models; no corpus records are read.
"""
import unittest
import hashlib

from allow_retrieval.corpus import worker, normalize_full
from allow_retrieval.embedding import load_encoder
from allow_retrieval.ranking import score


WEIGHTS = (0.55, 0.225, 0.225)
MODELS = {
    "query": "sig A {r:set A} pred p {some r}",
    "equivalent": "sig A {r:set A} pred q {some (r+r)}",
    "opposite": "sig A {r:set A} pred q {no r}",
    "wrong_context": "sig A {r:set A} sig B {} fact F {some A} pred p {some r}",
}


class LunaSemanticProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoder = load_encoder()
        cls.records = {}
        cls.outcomes = {}
        for name, source in MODELS.items():
            response = worker(source, target_slot=0, n=3)
            if response.get("status") != "FULL":
                raise AssertionError(f"{name}: worker status {response.get('status')}")
            record, outcomes, _ = normalize_full(response)
            cls.records[name] = record
            cls.outcomes[name] = outcomes
            cls.records[name]["vector"] = cls.encoder.encode_record(record).tolist()
            context_bytes = response["record"]["context"].encode()
            cls.records[name]["context_key"] = hashlib.sha256(context_bytes).hexdigest()
            cls.records[name]["context_bytes"] = context_bytes
            cls.records[name]["content"] = record

    def test_worker_pools_are_full_and_both_negative_queries_are_sat(self):
        for name in ("query", "equivalent", "opposite", "wrong_context"):
            self.assertEqual(self.outcomes[name]["positive"]["existence"], "SAT")
            self.assertEqual(self.outcomes[name]["negative"]["existence"], "SAT")
            self.assertEqual(self.outcomes[name]["positive"]["enumerated"], 3)
            self.assertEqual(self.outcomes[name]["negative"]["enumerated"], 3)
            self.assertEqual(len(self.records[name]["positives"]), 3)
            self.assertEqual(len(self.records[name]["negatives"]), 3)

    def test_frozen_weighted_scores_and_context_gate(self):
        query = self.records["query"]
        equivalent = score(query, self.records["equivalent"], WEIGHTS)
        opposite = score(query, self.records["opposite"], WEIGHTS)
        wrong_context = score(query, self.records["wrong_context"], WEIGHTS)
        self.assertGreater(equivalent["score"], opposite["score"])
        self.assertEqual(wrong_context["sharedPositive"], 0.0)
        self.assertEqual(wrong_context["sharedNegative"], 0.0)
        self.assertFalse(wrong_context["contextCompatible"])


if __name__ == "__main__":
    unittest.main()
