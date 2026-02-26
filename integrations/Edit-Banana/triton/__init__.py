"""Minimal stub for `triton` on Windows.

The PyPI `sam3` package imports Triton unconditionally for an EDT kernel. Triton
is not available on Windows via pip, but the EDT kernel is not required for the
core image segmentation path used by Edit-Banana.

If code paths try to execute Triton kernels, this stub raises a clear error.
"""

from __future__ import annotations

from typing import Any, Callable, Optional


class _Kernel:
    def __init__(self, fn: Callable[..., Any]):
        self._fn = fn

    def __getitem__(self, _grid: Any):
        raise RuntimeError(
            "Triton is not available on Windows in this environment. "
            "Install/run on a platform with Triton support, or switch to a non-Triton fallback."
        )


def jit(fn: Optional[Callable[..., Any]] = None, **_kwargs: Any):
    if fn is None:
        def decorator(f: Callable[..., Any]):
            return _Kernel(f)
        return decorator
    return _Kernel(fn)
