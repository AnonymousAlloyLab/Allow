# Generated artifacts

New transfer packages are written to `releases/`, which is intentionally ignored
by Git. The small release manifest is committed here after the package is built
and audited. It records hashes and finite acceptance evidence, not deployment.

`local-history/` is also ignored and reserved for local preservation of generated
files removed from active repository tracking. Historical evidence already under
`gates/`, `closure/` and `dist/` remains at its bound paths.

No provider credentials, private corpus, database data or accounting journals
belong in a distributable package.
