"""Minimal stub for `triton.language`.

Only exists so that `import triton.language as tl` succeeds.
"""

from __future__ import annotations

# Used only for type annotations in sam3 EDT kernel signature.
constexpr = object()


def _unavailable(*_args, **_kwargs):
    raise RuntimeError("Triton is not available on this platform")


program_id = _unavailable
load = _unavailable
store = _unavailable
