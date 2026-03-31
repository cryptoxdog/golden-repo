# S2-7: CI Test Refactor Instructions

**Purpose:** After installing `tests/ci/_scan_utils.py`, apply these changes to the three CI test files that currently contain duplicated `get_python_files()` implementations.

---

## tests/ci/test_adr_enforcement.py

1. **Remove** the local `def get_python_files(directories: list[str]) -> list[Path]:` function (around line 101).
2. **Add** at the top of the file (after other imports):
   ```python
   from tests.ci._scan_utils import iter_python_files, get_python_files
   ```
3. **Replace** all calls to the local `get_python_files()` with the imported version.

---

## tests/ci/test_anti_patterns.py

1. **Remove** the local `def get_python_files(directories: list[str]) -> list[Path]:` function (around line 82).
2. **Add** at the top of the file:
   ```python
   from tests.ci._scan_utils import get_python_files
   ```
3. **Replace** all calls to the local `get_python_files()` with the imported version.

---

## tests/ci/test_structural_invariants.py

1. **Remove** the local `def _get_python_files(directories: list[str]) -> list[Path]:` function (around line 56).
2. **Add** at the top of the file:
   ```python
   from tests.ci._scan_utils import get_python_files
   ```
3. **Replace** all calls to the local `_get_python_files()` with the imported `get_python_files()`.

---

## Verification

```bash
pytest tests/ci/test_adr_enforcement.py \
       tests/ci/test_anti_patterns.py \
       tests/ci/test_structural_invariants.py -v
```

All tests should pass with identical behaviour to the pre-refactor state.

---

## Note on Signature Compatibility

The shared `get_python_files()` in `_scan_utils.py` accepts `root: Path | None = None` and `skip_dirs: frozenset[str] | None = None`. The existing local functions in the three test files accept `directories: list[str]` (a list of subdirectory names). When refactoring, you may need to adapt the call sites slightly — either pass `root=get_repo_root()` and let the shared function handle discovery, or adjust the calling code to match the new signature.
