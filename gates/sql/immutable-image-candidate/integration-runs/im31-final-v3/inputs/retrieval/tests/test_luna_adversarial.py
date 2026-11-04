"""Frozen Luna 1 adversarial checks against production retrieval functions."""
import math
import unittest

import numpy as np

from allow_retrieval.embedding import compose
from allow_retrieval.ranking import cosine, overlap, parse_vector, score


def vec(*indices):
    value = [0.0] * 3072
    for index in indices:
        value[index] = 1.0
    return value


def record(vector, *, positives=(), negatives=(), context_key="ctx", context_bytes=b"ctx"):
    return {
        "vector": vector,
        "context_key": context_key,
        "context_bytes": context_bytes,
        "content": {"positives": list(positives), "negatives": list(negatives)},
    }


class LunaAdversarialTests(unittest.TestCase):
 def test_distance_direction_ranks_near_above_orthogonal_and_opposite(self):
    query = record(vec(0, 768))
    candidates = [record(vec(0, 768)), record(vec(1, 768)), record([-1.0 if i == 0 else 1.0 if i == 768 else 0.0 for i in range(3072)])]
    similarities = [score(query, candidate, (1, 0, 0))["canonicalSimilarity"] for candidate in candidates]
    np.testing.assert_allclose(similarities, [1.0, 0.75, 0.5])
    # Full 3072 cosine includes the shared predicate coordinate. A purely
    # orthogonal context-block vector would therefore not be cosine 0.
    self.assertGreater(similarities[0], similarities[1])
    self.assertGreater(similarities[1], similarities[2])


 def test_overlap_deduplicates_and_normalizes_by_larger_unique_pool(self):
    self.assertEqual(overlap(["a", "a", "b"], ["a"], True), 0.5)
    self.assertEqual(overlap(["a", "a", "b"], ["a", "b", "c", "d"], True), 0.5)
    self.assertEqual(overlap([], ["a"], True), 0.0)


 def test_digest_collision_does_not_replace_exact_canonical_bytes(self):
    left = {"digest": "forced-collision", "canonical_bytes": "sig=A;field=empty"}
    right = {"digest": "forced-collision", "canonical_bytes": "sig=A;field=A->A"}
    self.assertEqual(overlap([left], [right], True), 0.0)


 def test_polarity_pools_are_compared_only_with_same_polarity(self):
    query = record(vec(0, 768), positives=["p1", "p2"], negatives=["n1"])
    candidate = record(vec(0, 768), positives=["n1"], negatives=["p1", "p2"])
    result = score(query, candidate, (0, 0.5, 0.5))
    self.assertEqual(result["sharedPositive"], 0.0)
    self.assertEqual(result["sharedNegative"], 0.0)
    self.assertEqual(result["score"], 0.0)


 def test_same_instance_in_different_context_gets_no_overlap(self):
    query = record(vec(0, 768), positives=["instance-1"])
    candidate = record(vec(0, 768), positives=["instance-1"], context_key="other", context_bytes=b"other")
    result = score(query, candidate)
    self.assertEqual(result["sharedPositive"], 0.0)
    self.assertIs(result["contextCompatible"], False)
    self.assertEqual(result["compatibility"], "INCOMPATIBLE_CONTEXT")


 def test_vector_dimension_nonfinite_zero_and_database_order_are_checked(self):
    valid = "[" + ",".join(["1"] * 3072) + "]"
    self.assertEqual(len(parse_vector(valid)), 3072)
    with self.assertRaisesRegex(ValueError, "stored_vector_invalid"):
        parse_vector("[" + ",".join(["1"] * 3071) + "]")
    with self.assertRaisesRegex(ValueError, "stored_vector_invalid"):
        parse_vector("[" + ",".join(["NaN"] + ["1"] * 3071) + "]")
    with self.assertRaisesRegex(ValueError, "invalid_vector"):
        cosine([0.0, 0.0], [1.0, 0.0])
    with self.assertRaisesRegex(ValueError, "invalid_vector"):
        cosine([math.nan, 0.0], [1.0, 0.0])


 def test_embedding_composition_preserves_declared_block_order_and_rejects_zero(self):
    blocks = np.zeros((4, 768), dtype=np.float32)
    for block in range(4):
        blocks[block, 0] = 1
        blocks[block, block + 1] = block + 1
    output = compose(blocks)
    # Each block is independently normalized before concatenation, with a
    # distinct pattern retained at its declared sequential range.
    self.assertEqual(output.shape, (3072,))
    self.assertAlmostEqual(float(np.linalg.norm(output)), 1.0, delta=1e-5)
    self.assertEqual(np.flatnonzero(output).tolist(), [0, 1, 768, 770, 1536, 1539, 2304, 2308])
    reordered = compose(blocks[[0, 2, 1, 3]])
    self.assertFalse(np.array_equal(output, reordered))
    with self.assertRaisesRegex(ValueError, "nonfinite_or_zero_vector"):
        compose(np.zeros((4, 768), dtype=np.float32))
    bad = blocks.copy()
    bad[2, 7] = np.nan
    with self.assertRaisesRegex(ValueError, "nonfinite_or_zero_vector"):
        compose(bad)


 def test_invalid_weights_rejected(self):
    for weights in [(-0.01, 0.505, 0.505), (0.5, 0.5, 0.5), (0.5, math.nan, 0.5)]:
        with self.subTest(weights=weights), self.assertRaisesRegex(ValueError, "invalid_weights"):
            score(record(vec(0, 768)), record(vec(0, 768)), weights)


 def test_valid_weights_keep_score_bounded(self):
    for weights in [(0.55, 0.225, 0.225), (0, 0, 1), (0.45, 0.4125, 0.1375)]:
        with self.subTest(weights=weights):
            result = score(record(vec(0, 768), positives=["p"], negatives=["n"]),
                           record(vec(0, 768), positives=["p"], negatives=["n"]), weights)
            self.assertAlmostEqual(result["score"], 1.0)
            self.assertGreaterEqual(result["score"], 0.0)
            self.assertLessEqual(result["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
