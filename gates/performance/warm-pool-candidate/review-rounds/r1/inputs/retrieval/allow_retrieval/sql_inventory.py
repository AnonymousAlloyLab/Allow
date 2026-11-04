"""One explicit inventory for installed and startup-loaded SQL proxy sources."""

PROXY_MODULES = (
    '__init__.py', 'common.py', 'sql_connections.py', 'sql_proxy.py',
    'sql_guard.py', 'sql_image.py', 'sql_image_init.py', 'sql_image_config.py',
    'sql_inventory.py', 'sql_context_protocol.py', 'sql_context_journal.py',
    'sql_context_identity.py', 'sql_context_observer.py', 'sql_context_lease.py',
    'sql_context_control.py',
)


def source_names():
    """Return every policy module and pinned parser/dependency configuration path."""
    return tuple('retrieval/allow_retrieval/' + name for name in PROXY_MODULES) + (
        'config/sqlean-parser-lock.json', 'retrieval/requirements-ml.lock',
    )
