.PHONY: run_fuzz_tests clean run_test_gui_new_match_highlight run_gui_crash_test

run_test_gui_new_match_highlight:
	python3 python/test_gui_new_match_highlight.py

run_fuzz_tests:
	python3 test_competitive_variety_fuzzing.py

run_player_removal_persistence_test:
	python3 test_player_removal_persistence.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
