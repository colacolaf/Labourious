"""labourious.__main__ — entry point for `python -m labourious`.

Forwards via ``sys.exit(labourious.main(sys.argv[1:]))`` so a failed
flow exits non-zero (the runtime itself uses ``sys.exit(main())``
in its own ``__main__`` block).
"""
from __future__ import annotations

import sys

from labourious import main


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
