"""One private immutable interpretation snapshot per sealed-image gate generation."""
from dataclasses import dataclass
import hashlib
import itertools
import json
import os
import stat
from pathlib import Path
import threading

PROFILE = 'postgresql-16.15-grammar-v0.1'
COMMIT = 'f0595c3d839debdb140903621c1b44a4f4d86256'
POLICY = 'sql-routing-v8-context-leases'
BINARY_SHA256 = '9b252aabef502a9471f64c60ad2b0821e9db209a275c7ba8a4bd01da275e0cf7'
BINARY_SIZE = 136492600
MAPPING_SHA256 = '679284527c19f215a3b6a46c2ac107bbb152959ffd44fe3108f198f8f4a55eeb'
MAPPING_COUNT = 3285
_generations = itertools.count(1)
_generation_lock = threading.Lock()


class ImageError(ValueError):
    """Content-free infrastructure error; never accepts SQL after failure."""
    category = 'infrastructureFailure'


def duplicates(pairs):
    """Reject ambiguous JSON before any snapshot exists."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ImageError('duplicate parser configuration field')
        result[key] = value
    return result


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False,
        separators=(',', ':'), sort_keys=True).encode('utf8')).hexdigest()


def workspace_root():
    """Support staging and later reviewed installation without environment overrides."""
    for parent in Path(__file__).resolve().parents:
        if (parent/'config/sqlean-parser-lock.json').is_file():
            return parent
    raise ImageError('parser workspace unavailable')


@dataclass(frozen=True, slots=True)
class ConfigSnapshot:
    binary_sha256: str
    expected_size: int
    profile: str
    commit: str
    production_lhs: tuple[str, ...]
    mapping_sha256: str
    policy: str
    source_sha256: str
    generation: int
    digest: str

    @classmethod
    def from_mapping(cls, data, *, source_sha256=None):
        """Validate pinned interpretation and defensively copy every ordered entry."""
        if not isinstance(data, dict):
            raise ImageError('invalid parser configuration')
        if (data.get('binary_sha256') != BINARY_SHA256 or
                data.get('profile') != PROFILE or data.get('postgresql_commit') != COMMIT):
            raise ImageError('parser configuration pin mismatch')
        # Revision6 lock has no size field. The reviewed compiled pin is authoritative;
        # a supplied field must agree and is never inferred from a mutable source stat.
        size = data.get('binary_size', BINARY_SIZE)
        if type(size) is not int or size != BINARY_SIZE or size <= 0:
            raise ImageError('parser size pin mismatch')
        if data.get('policy', POLICY) != POLICY:
            raise ImageError('parser policy pin mismatch')
        mapping = data.get('production_lhs')
        if (not isinstance(mapping, list) or len(mapping) != MAPPING_COUNT or
                not all(type(value) is str and value for value in mapping)):
            raise ImageError('invalid production mapping')
        copied = tuple(mapping)
        mapping_digest = canonical_digest(copied)
        if mapping_digest != MAPPING_SHA256:
            raise ImageError('production mapping pin mismatch')
        with _generation_lock:
            generation = next(_generations)
        configuration_digest = source_sha256 if source_sha256 is not None else canonical_digest(data)
        fields = (BINARY_SHA256, size, PROFILE, COMMIT, copied,
                  mapping_digest, POLICY, configuration_digest, generation)
        return cls(*fields, canonical_digest(fields))

    @classmethod
    def load(cls, path):
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOFOLLOW)
            with os.fdopen(descriptor, 'rb') as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise ImageError('invalid parser configuration source')
                raw = source.read(1048577)
            if len(raw) > 1048576:
                raise ImageError('parser configuration too large')
            return cls.from_mapping(json.loads(raw.decode('utf8'), object_pairs_hook=duplicates),
                source_sha256=hashlib.sha256(raw).hexdigest())
        except (OSError, UnicodeError, ValueError, TypeError, RecursionError) as error:
            raise ImageError('parser configuration unavailable') from error
