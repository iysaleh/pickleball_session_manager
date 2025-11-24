.PHONY: run_fuzz_tests clean run_test_gui_new_match_highlight

run_test_gui_new_match_highlight:
	python python/test_gui_new_match_highlight.py

run_fuzz_tests:
	python test_competitive_variety_fuzzing.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
