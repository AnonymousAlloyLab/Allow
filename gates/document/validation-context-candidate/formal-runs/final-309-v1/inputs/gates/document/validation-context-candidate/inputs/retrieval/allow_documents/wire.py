"""Strict bounded document bridge framing and exact original request identity."""
import base64
import hashlib
import json
import re
import uuid

MAX_INPUT = 3145728
MAX_RESPONSE = 1048576
MAX_REQUEST = 262144
ARTIFACT_FIELDS = {'artifactId', 'mode', 'source', 'sourceHash', 'module', 'occurrences', 'trivia',
                   'analysisDescriptors', 'policyVersion', 'dependencyHash'}


def pairs(items):
    """Reject duplicate JSON fields rather than accepting a last writer."""
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def decode(raw, limit=MAX_INPUT):
    """Decode exact strict UTF8 JSON with closed integer/scalar support."""
    if len(raw) > limit or raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('input_limit')
    result = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
    check_scalars(result)
    return result


def check_scalars(value):
    """Bound nesting and reject non-scalar strings and unsafe JSON numbers."""
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > 96:
            raise ValueError('json_depth')
        if isinstance(item, str):
            item.encode('utf-8', errors='strict')
        elif type(item) is int and not -9007199254740991 <= item <= 9007199254740991:
            raise ValueError('integer_range')
        elif isinstance(item, float):
            raise ValueError('floating_number')
        elif isinstance(item, dict):
            stack.extend((x, depth + 1) for pair in item.items() for x in pair)
        elif isinstance(item, list):
            stack.extend((x, depth + 1) for x in item)


def encode(value):
    """Encode a bounded UTF8 internal object, never normalizing public requests."""
    check_scalars(value)
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def fields(value, required):
    """Require one exact closed object shape."""
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError('unexpected_fields')
    return value


def identifier(value):
    """Validate opaque server document/artifact identifiers."""
    if not isinstance(value, str) or not value.startswith('server:'):
        raise ValueError('invalid_server_id')
    tail = value[7:]
    if str(uuid.UUID(tail)) != tail:
        raise ValueError('invalid_server_id')
    return value


def fresh_id():
    """Create a cryptographically random server identity."""
    return 'server:' + str(uuid.uuid4())


def b64(raw):
    """Encode exact transport or stored response bytes."""
    return base64.b64encode(raw).decode('ascii')


def unb64(value, limit):
    """Bound a base64 field before allocating decoded payload."""
    if not isinstance(value, str) or len(value) > ((limit + 2) // 3) * 4:
        raise ValueError('encoded_limit')
    raw = base64.b64decode(value, validate=True)
    if len(raw) > limit:
        raise ValueError('decoded_limit')
    return raw


def request(args):
    """Validate exact receipt identity without parsing an existing receipt body."""
    document = args['documentId']
    if document != 'CREATE':
        identifier(document)
    key = args['key']
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,128}', key):
        raise ValueError('invalid_key')
    if args['method'] != 'POST' or not isinstance(args['route'], str):
        raise ValueError('invalid_route')
    expected = '/api/v1/documents' if document == 'CREATE' else '/api/v1/documents/' + document
    routes = (expected, expected + '/commit', expected + '/history-copy')
    if document != 'CREATE':
        encoded = '/api/v1/documents/' + document.replace(':','%3A')
        routes += (encoded + '/commit', encoded + '/history-copy')
    if args['route'] not in routes:
        raise ValueError('invalid_route')
    body = unb64(args['bodyBase64'], MAX_REQUEST)
    body.decode('utf-8', errors='strict')
    return document, key, args['method'], args['route'], body


def artifact(value, policy):
    """Bound trusted checked artifact frames before entering SQL transactions."""
    fields(value, ARTIFACT_FIELDS)
    identifier(value['artifactId'])
    if value['policyVersion'] != policy or not isinstance(policy, str) or not 1 <= len(policy) <= 128:
        raise ValueError('invalid_policy')
    source = value['source'].encode('utf-8', errors='strict')
    if len(source) > 32768 or value['mode'] not in ('BLOCK_SUPPORTED', 'TEXT_ONLY'):
        raise ValueError('invalid_artifact')
    if not isinstance(value['occurrences'], list) or len(value['occurrences']) > 2048:
        raise ValueError('invalid_maps')
    if not isinstance(value['analysisDescriptors'], list) or len(value['analysisDescriptors']) > 32:
        raise ValueError('invalid_commands')
    if value['mode'] == 'TEXT_ONLY' and (value['module'] is not None or value['occurrences']):
        raise ValueError('text_has_graph')
    if value['mode'] == 'BLOCK_SUPPORTED' and not isinstance(value['module'], dict):
        raise ValueError('missing_module')
    raw = encode(value)
    if len(raw) > MAX_RESPONSE:
        raise ValueError('artifact_limit')
    source_hash = hashlib.sha256(source).hexdigest()
    if value['sourceHash'] != source_hash:
        raise ValueError('source_hash_mismatch')
    return raw, source_hash
