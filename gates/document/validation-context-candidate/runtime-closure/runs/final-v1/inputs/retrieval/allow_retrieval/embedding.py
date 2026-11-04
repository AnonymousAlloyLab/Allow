"""Offline pinned E5 encoder for trusted anonymous projection output.

This module is not an admission parser. Only the checked upstream worker may
construct its generic JSON values; never expose encode_record to raw API input.
"""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import numpy as np

REVISION = 'f52bf8ec8c7124536f0efb74aca902b2995e5bcd'
MODEL_SHA256 = '157f97ef1957d34f52efa26f8031371bf9043acc45460cec7ebe94631ac0e96b'
RECIPE = 'allow-e5-hierarchy-v1-query-480-8192-32-membermean'
COMPONENTS = ('context', 'predicate', 'positives', 'negatives')


def normalize(x):
    """Normalize finite nonzero last-axis vectors; reject absent evidence."""
    x = np.asarray(x, dtype=np.float32)
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    if not np.isfinite(x).all() or not np.isfinite(norm).all() or np.any(norm <= 1e-12):
        raise ValueError('nonfinite_or_zero_vector')
    return x / norm


def serialize(value):
    """Serialize trusted upstream anonymous structures deterministically."""
    if not isinstance(value, (list, dict)):
        raise ValueError('structural_json_required')
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def compose(blocks, log_scales=None):
    """Adapt and pack the ordered four normalized blocks into 3072 dimensions."""
    blocks = np.asarray(blocks, dtype=np.float32)
    if blocks.shape != (4, 768):
        raise ValueError('expected_four_768_blocks')
    blocks = normalize(blocks)
    if log_scales is not None:
        log_scales = np.asarray(log_scales, dtype=np.float32)
        if log_scales.shape != blocks.shape or not np.isfinite(log_scales).all():
            raise ValueError('invalid_adapter')
        with np.errstate(over='ignore', invalid='ignore', under='ignore'):
            diagonal = np.exp(log_scales)
        if not np.isfinite(diagonal).all() or np.any(diagonal <= 0):
            raise ValueError('invalid_adapter_scales')
        blocks = normalize(blocks * diagonal)
    result = (blocks.reshape(3072) / 2).astype(np.float32)
    if not np.isfinite(result).all() or abs(float(np.linalg.norm(result)) - 1) > 1e-5:
        raise ValueError('invalid_embedding')
    return result


class Encoder:
    def __init__(self, model_dir=".tools/retrieval/models", tokenizer=None, session=None, adapter_path=None):
        self.model_dir = Path(model_dir)
        if tokenizer is None or session is None:
            import onnxruntime as ort
            from tokenizers import Tokenizer
            lock = json.loads((self.model_dir / 'model-lock.json').read_text())
            expected_lock = json.loads((Path(__file__).resolve().parents[1]/'model-lock.json').read_text())
            if lock != expected_lock:
                raise ValueError('unapproved_model_lock')
            for name, expected in lock['files'].items():
                if hashlib.sha256((self.model_dir / name).read_bytes()).hexdigest() != expected:
                    raise ValueError('model_file_hash_mismatch:' + name)
            if lock['revision'] != REVISION or lock['files']['model.onnx'] != MODEL_SHA256:
                raise ValueError('unapproved_model')
            tokenizer = Tokenizer.from_file(str(self.model_dir / 'tokenizer.json'))
            options = ort.SessionOptions()
            options.intra_op_num_threads = 4
            session = ort.InferenceSession(str(self.model_dir / 'model.onnx'), sess_options=options,
                                           providers=['CPUExecutionProvider'])
        self.tokenizer, self.session = tokenizer, session
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.coverage = []
        lock_path = self.model_dir / 'model-lock.json'
        fingerprint = lock_path.read_bytes() if lock_path.exists() else b'injected-test-model'
        runtime = {name:importlib.metadata.version(name) for name in ('numpy','onnxruntime','tokenizers')}
        fingerprint += json.dumps(runtime,sort_keys=True).encode()
        self.log_scales = None
        if adapter_path is not None:
            self.log_scales = np.load(adapter_path, allow_pickle=False)
            compose(np.ones((4,768)), self.log_scales)
        self.model_id = self.model_id_for(self.log_scales, fingerprint)

    @staticmethod
    def model_id_for(log_scales=None, fingerprint=b''):
        """Bind inference recipe, pinned artifact/runtime bytes and adapter identity."""
        adapter = b'identity' if log_scales is None else np.asarray(log_scales,dtype='<f4').tobytes()
        return RECIPE + '-' + hashlib.sha256(fingerprint + adapter).hexdigest()

    def _tokens(self, text):
        """Tokenize completely, without padding, special tokens or truncation."""
        return self.tokenizer.encode(text, add_special_tokens=False).ids

    def _member(self, value, marker, content=None):
        """Encode every admitted content token once and mean-pool normalized chunks."""
        content = self._tokens(serialize(value)) if content is None else content
        if len(content) > 8192:
            raise ValueError('component_token_budget')
        prefix = self._tokens('query: ' + marker + ' ')
        chunks = [content[i:i + 480] for i in range(0, len(content), 480)] or [[]]
        if len(chunks) > 32:
            raise ValueError('component_chunk_budget')
        vectors = []
        for chunk in chunks:
            # E5 is BERT; special token IDs are obtained from the pinned tokenizer.
            ids = [self.tokenizer.token_to_id('[CLS]')] + prefix + chunk + [self.tokenizer.token_to_id('[SEP]')]
            if None in ids or len(ids) > 512:
                raise ValueError('special_or_prefix_budget')
            batch = np.array([ids], dtype=np.int64)
            feeds = {'input_ids': batch, 'attention_mask': np.ones_like(batch), 'token_type_ids': np.zeros_like(batch)}
            names = {x.name for x in self.session.get_inputs()}
            hidden = self.session.run(None, {k: v for k, v in feeds.items() if k in names})[0]
            if hidden.shape != (1, len(ids), 768):
                raise ValueError('unexpected_encoder_shape')
            vectors.append(normalize(hidden[0].mean(axis=0)))
        self.coverage.append({'tokens': len(content), 'covered_tokens': sum(map(len, chunks)), 'chunks': len(chunks)})
        return normalize(np.mean(vectors, axis=0)), len(content), len(chunks)

    def encode_blocks(self, record):
        """Encode an already-admitted structural projection after full budget preflight."""
        if set(record) != set(COMPONENTS):
            raise ValueError('exact_structural_components_required')
        self.coverage = []
        plans = []
        # Preflight every component before any costly model invocation.
        for component in COMPONENTS:
            values = record[component] if component in ('positives', 'negatives') else [record[component]]
            if not isinstance(values, list) or not values or (component in ('positives', 'negatives') and not 3 <= len(values) <= 5):
                raise ValueError('full_pool_required')
            serialized = [serialize(v) for v in values]
            if len(set(serialized)) != len(values):
                raise ValueError('duplicate_pool_member')
            members = [(value, self._tokens(serialize(value))) for value in sorted(values,key=serialize)]
            tokens = sum(len(content) for _,content in members)
            chunks = sum(max(1,(len(content)+479)//480) for _,content in members)
            prefix = self._tokens('query: ' + component + ' ')
            if tokens > 8192 or chunks > 32 or len(prefix)+482 > 512:
                raise ValueError('component_budget')
            plans.append((component,members))
        blocks = []
        for component,members in plans:
            vectors = [self._member(value,component,content)[0] for value,content in members]
            blocks.append(normalize(np.mean(vectors,axis=0)))
        return np.stack(blocks).astype(np.float32)

    def encode_record(self, record, log_scales=None):
        """Encode one trusted FULL structural projection using this model version."""
        return compose(self.encode_blocks(record), self.log_scales if log_scales is None else log_scales)


def load_encoder(model_dir=".tools/retrieval/models", adapter_path=None):
    """Load the pinned offline CPU encoder and optional fitted adapter."""
    return Encoder(model_dir, adapter_path=adapter_path)
