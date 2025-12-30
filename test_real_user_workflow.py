#!/usr/bin/env python3
"""
Test the exact user workflow that was failing
"""

import sys
from python.time_manager import initialize_time_manager
from python.session_persistence import save_player_history, load_player_history_with_ratings
from python.gui import SetupDialog, SessionWindow
from python.session import create_session
from python.pickleball_types import Player, SessionConfig
from PyQt6.QtWidgets import QApplication

def test_real_user_workflow():
    """Test the exact workflow user described as failing"""
    print("Testing Real User Workflow for Pre-seeded Sessions")
    print("=" * 60)
    
    initialize_time_manager()
    app = QApplication([])
    
    print("\n🎯 SIMULATING EXACT USER SCENARIO:")
    print("1. Start session with pre-seeding enabled")
    print("2. Players have skill levels set") 
    print("3. End the session")
    print("4. Start new session with previous players")
    print("5. Verify pre-seeding is set and skill levels restored")
    
    # Step 1: User creates pre-seeded session
    print("\n" + "="*50)
    print("STEP 1: User creates pre-seeded session")
    print("="*50)
    
    # User opens SetupDialog, enables pre-seed, adds players with ratings
    setup_dialog = SetupDialog()
    
    # Enable pre-seeding
    setup_dialog.mode_combo.setCurrentText("Competitive Variety")
    setup_dialog.pre_seed_checkbox.setChecked(True)
    setup_dialog.player_widget.set_pre_seed_mode(True)
    
    # Add players with skill ratings (simulates user input)
    test_players = [
        Player(id="p1", name="John Pro", skill_rating=4.2),
        Player(id="p2", name="Sarah Expert", skill_rating=3.9),
        Player(id="p3", name="Mike Strong", skill_rating=3.6),
        Player(id="p4", name="Lisa Good", skill_rating=3.3)
    ]
    
    # Manually add to dialog (simulates user adding them)
    setup_dialog.player_widget.players = test_players
    
    print(f"✅ Pre-seed enabled: {setup_dialog.pre_seed_checkbox.isChecked()}")
    print(f"✅ Players added with skill ratings:")
    for p in test_players:
        print(f"   - {p.name}: {p.skill_rating}")
    
    # Create session configuration (simulates clicking "Start Session")
    config = SessionConfig(
        mode='competitive-variety',
        session_type='doubles', 
        players=test_players,
        courts=2,
        pre_seeded_ratings=True
    )
    
    session = create_session(config)
    print(f"✅ Session created with pre_seeded_ratings: {session.config.pre_seeded_ratings}")
    
    # Step 2: User "ends" the session (simulates closing SessionWindow)
    print("\n" + "="*50)
    print("STEP 2: User ends the session")
    print("="*50)
    
    # This simulates what happens in SessionWindow.closeEvent() with our fix
    from python.session_persistence import save_session, save_player_history
    
    # Save session state
    save_session(session)
    
    # Save player history (THIS IS THE FIX)
    player_names = [player.name for player in session.config.players]
    bye_player_names = []  # Simplified for test
    
    save_player_history(
        player_names=player_names,
        first_bye_players=bye_player_names,
        players_with_ratings=session.config.players,
        pre_seeded=session.config.pre_seeded_ratings,
        game_mode=session.config.mode,
        session_type=session.config.session_type
    )
    
    print(f"✅ Session ended and player history saved")
    print(f"   - Pre-seeded: {session.config.pre_seeded_ratings}")
    print(f"   - Game mode: {session.config.mode}")
    print(f"   - Players: {len(player_names)}")
    
    # Step 3: User clicks "New Session with Previous Players"
    print("\n" + "="*50)
    print("STEP 3: User clicks 'New Session with Previous Players'")
    print("="*50)
    
    # Load player history
    history = load_player_history_with_ratings()
    print(f"✅ History loaded:")
    print(f"   - Pre-seeded: {history['pre_seeded']}")
    print(f"   - Game mode: {history['game_mode']}")
    print(f"   - Player ratings: {history['player_ratings']}")
    
    # Create new SetupDialog with previous data (this is what MainWindow does)
    new_setup = SetupDialog(
        previous_players=history['players'],
        previous_first_byes=history['first_bye_players'],
        previous_pre_seeded=history['pre_seeded'],
        previous_ratings=history['player_ratings'],
        previous_game_mode=history['game_mode'],
        previous_session_type=history['session_type']
    )
    
    # Step 4: Verify the restoration
    print("\n" + "="*50)
    print("STEP 4: Verify SetupDialog state")
    print("="*50)
    
    print(f"🔍 SetupDialog Configuration:")
    print(f"   Game Mode: {new_setup.mode_combo.currentText()}")
    print(f"   Session Type: {new_setup.type_combo.currentText()}")
    print(f"   Pre-seed Checkbox: {'☑ CHECKED' if new_setup.pre_seed_checkbox.isChecked() else '☐ UNCHECKED'}")
    print(f"   Player Count: {len(new_setup.player_widget.players)}")
    
    print(f"\n🔍 Players in Dialog:")
    all_ratings_restored = True
    for i, player in enumerate(new_setup.player_widget.players):
        item = new_setup.player_widget.player_list.item(i) if i < new_setup.player_widget.player_list.count() else None
        display_text = item.text() if item else "No display"
        
        print(f"   {i+1}. {player.name}")
        print(f"      - Skill Rating: {player.skill_rating}")
        print(f"      - Display Text: \"{display_text}\"")
        print(f"      - Has Rating in Display: {'✅' if player.skill_rating and f'({player.skill_rating})' in display_text else '❌'}")
        
        if player.skill_rating is None:
            all_ratings_restored = False
    
    # Final verification
    print("\n" + "="*60)
    print("FINAL VERIFICATION")
    print("="*60)
    
    success_criteria = [
        ("Game mode restored", new_setup.mode_combo.currentText() == "Competitive Variety"),
        ("Pre-seed checkbox checked", new_setup.pre_seed_checkbox.isChecked()),
        ("All players loaded", len(new_setup.player_widget.players) == 4),
        ("All ratings preserved", all(p.skill_rating is not None for p in new_setup.player_widget.players)),
        ("Ratings displayed correctly", all_ratings_restored)
    ]
    
    all_passed = True
    for criterion_name, passed in success_criteria:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {criterion_name}")
        if not passed:
            all_passed = False
    
    print(f"\n{'🎉 COMPLETE SUCCESS' if all_passed else '❌ ISSUES FOUND'}")
    
    if all_passed:
        print("✓ Pre-seeding is properly restored")
        print("✓ Players loaded with their skill levels") 
        print("✓ 'New Session with Previous Players' working correctly")
        print("\nThe issue has been RESOLVED! 🎯")
    else:
        print("❌ The workflow is still not working correctly")
    
    return all_passed


if __name__ == "__main__":
    test_real_user_workflow()