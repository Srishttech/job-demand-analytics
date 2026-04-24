# Fix Flask ImportError (DLL load failed on 'select') - UPDATED TO SYSTEM PYTHON + VENV

## Completed:
- [x] Step 1: Remove broken .venv / penv
- [x] Step 2: Create freshenv with `python -m venv freshenv` ✓
- [x] Step 3: Activate freshenv ✓ Prompt (freshenv)
- [ ] Step 4: `python -m pip install -r requirements.txt` (RUNNING: pandas building)
- [ ] Step 5: Test `python app.py`
- [ ] Step 6: `python init_db.py` if needed
- [ ] Step 7: http://localhost:5000

Note: uv blocked by Windows App Control policy; using system Python 3.12.13 bypass.

Original TODO: uv venv attempt failed due to policy.
