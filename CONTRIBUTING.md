# Contributing

Useful contributions include a real integration example, a comparison that was
misclassified, clearer error messages, or a report interaction that is hard to
use. Please include a small anonymized reproduction and the expected behavior.

Discuss changes to identity, relevance labels, gate semantics, or the snapshot
contract before building a large patch. Avoid attaching private query text,
customer documents, credentials, or unreviewed production traces.

Use Python 3.10 or newer. Runtime dependencies are intentionally empty.

```sh
python -m pip install -e . build ruff
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
python -m build
```

Add tests for behavioral changes. Preserve the distinction between observed
change, labeled quality, and unknown causes. Documentation, comments, issues,
and pull requests use English.
