.PHONY: run_fuzz_tests clean run_test_gui_new_match_highlight run_gui_crash_test

run_test_gui_new_match_highlight:
	python3 python/test_gui_new_match_highlight.py

run_fuzz_tests:
	python3 test_competitive_variety_fuzzing.py

run_player_removal_persistence_test:
	python3 test_player_removal_persistence.py

run_test_back_to_back_partner_bug:
	python3 test_back_to_back_partner_bug.py

run_test_partner_repetition_8_players:
	python3 test_partner_repetition_8_players.py

run_test_opponent_repetition_8_players:
	python3 test_opponent_repetition_8_players.py

run_test_direct_history_check:
	python3 test_direct_history_check.py

run_test_priority_queueing:
	python3 test_priority_queueing.py

run_test_per_player_repetition:
	python3 test_per_player_repetition.py

run_test_dense_constraints:
	python3 test_dense_constraints.py

run_test_bracket_restrictions:
	python3 test_bracket_restrictions.py

run_test_roaming_range:
	python3 test_roaming_range.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
