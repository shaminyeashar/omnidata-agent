import os, sys
print('🔍 Running Step 01 Verification Gate...\n')
in_venv = sys.prefix != sys.base_prefix
print(f'[1/2] Virtual Environment Active: {in_venv}')
assert in_venv, 'FAIL: Activate .venv first'
submodules = ['modules','modules/telemetry','modules/ingestion','modules/eda_engine','modules/structured_search','modules/unstructured_rag','modules/deep_learn','tests']
for mod in submodules:
    ok = os.path.isdir(mod) and os.path.isfile(os.path.join(mod, '__init__.py'))
    print(f'      -> Package {mod} ready: {ok}')
    assert ok, f'FAIL: Missing {mod}'
print('\n✅ STEP 01 PASSED: All 6 module sandboxes are isolated and ready!')
