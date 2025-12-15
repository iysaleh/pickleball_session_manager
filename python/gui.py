"""
PyQt6 GUI for Pickleball Session Manager
"""

import sys
import json
import os
import subprocess
from typing import Optional, List, Dict
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QSpinBox, QComboBox, QLabel, QListWidget,
    QListWidgetItem, QDialog, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QSpinBox, QGroupBox, QCheckBox, QFrame, QScrollArea,
    QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QRect, QSize, QPropertyAnimation, QPoint, QEasingCurve, QParallelAnimationGroup
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QPixmap

from python.types import (
    Player, Session, SessionConfig, GameMode, SessionType, Match,
    MatchStatus, QueuedMatch
)
from python.session import (
    create_session, add_player_to_session, remove_player_from_session,
    complete_match, forfeit_match, get_player_name, get_matches_for_court,
    get_active_matches, get_completed_matches, evaluate_and_create_matches,
    get_active_player_names
)


class ClickableLabel(QLabel):
    """Custom label that emits a signal on double-click"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.double_clicked = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click"""
        self.double_clicked = True
        if hasattr(self.parent(), 'edit_court_title'):
            self.parent().edit_court_title()


class EditableCourtFrame(QFrame):
    """Custom frame that handles double-click for court editing"""
    
    def __init__(self, court_widget, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.court_widget = court_widget
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click on court to edit"""
        self.court_widget.edit_court_teams()


class PlayerListWidget(QWidget):
    """Widget for managing player list"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.players: List[Player] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Player input
        input_layout = QHBoxLayout()
        self.player_input = QLineEdit()
        self.player_input.setPlaceholderText("Enter player name")
        self.player_input.returnPressed.connect(self.add_player)
        
        add_btn = QPushButton("Add Player")
        add_btn.clicked.connect(self.add_player)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected_player)
        
        input_layout.addWidget(self.player_input)
        input_layout.addWidget(add_btn)
        input_layout.addWidget(remove_btn)
        layout.addLayout(input_layout)
        
        # Player count
        count_layout = QHBoxLayout()
        self.player_count_label = QLabel("Total Players: 0")
        self.player_count_label.setStyleSheet("font-weight: bold; font-size: 12px; color: white; background-color: #2a2a2a;")
        count_layout.addWidget(self.player_count_label)
        count_layout.addStretch()
        layout.addLayout(count_layout)
        
        # Player list
        self.player_list = QListWidget()
        layout.addWidget(self.player_list)
        
        self.setLayout(layout)
    
    def add_player(self):
        """Add a player to the list"""
        name = self.player_input.text().strip()
        if not name:
            return
        
        player = Player(id=f"player_{len(self.players)}_{datetime.now().timestamp()}", name=name)
        self.players.append(player)
        
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, player.id)
        self.player_list.addItem(item)
        
        self.player_input.clear()
        self.player_input.setFocus()
        self.update_player_count()
    
    def remove_selected_player(self):
        """Remove selected player from list"""
        current_item = self.player_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a player to remove")
            return
        
        player_id = current_item.data(Qt.ItemDataRole.UserRole)
        self.players = [p for p in self.players if p.id != player_id]
        self.player_list.takeItem(self.player_list.row(current_item))
        self.update_player_count()
    
    def get_players(self) -> List[Player]:
        """Get current player list"""
        return self.players.copy()
    
    def update_player_count(self):
        """Update the player count label"""
        self.player_count_label.setText(f"Total Players: {len(self.players)}")
    
    def clear(self):
        """Clear all players"""
        self.players = []
        self.player_list.clear()
        self.update_player_count()


class ManageLocksDialog(QDialog):
    """Dialog for managing player locks and bans"""
    
    def __init__(self, players: List[Player], banned_pairs: List, locked_teams: List, parent=None):
        super().__init__(parent)
        self.players = players
        self.banned_pairs = banned_pairs
        self.locked_teams = locked_teams
        self.init_ui()
        
    def get_player_name(self, player_id):
        for p in self.players:
            if p.id == player_id:
                return p.name
        return player_id
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        tabs = QTabWidget()
        self.locks_tab = QWidget()
        self.bans_tab = QWidget()
        
        self.setup_locks_tab()
        self.setup_bans_tab()
        
        tabs.addTab(self.locks_tab, "Player Locks (Partners)")
        tabs.addTab(self.bans_tab, "Banned Pairs")
        
        layout.addWidget(tabs)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        self.setWindowTitle("Manage Locks & Bans")
        self.resize(500, 400)
        
        # Style
        self.setStyleSheet("""
            QDialog { background-color: #2a2a2a; color: white; }
            QTabWidget::pane { border: 1px solid #555; }
            QTabBar::tab { background: #3a3a3a; color: white; padding: 8px; }
            QTabBar::tab:selected { background: #2196F3; }
            QWidget { background-color: #2a2a2a; color: white; }
            QListWidget { background-color: #3a3a3a; border: 1px solid #555; }
            QPushButton { background-color: #0d47a1; color: white; padding: 5px; border-radius: 3px; }
        """)

    def setup_locks_tab(self):
        layout = QVBoxLayout()
        
        self.locks_list = QListWidget()
        self.refresh_locks()
        layout.addWidget(self.locks_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Lock")
        add_btn.clicked.connect(self.add_lock)
        remove_btn = QPushButton("Remove Lock")
        remove_btn.clicked.connect(self.remove_lock)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)
        
        self.locks_tab.setLayout(layout)

    def setup_bans_tab(self):
        layout = QVBoxLayout()
        
        self.bans_list = QListWidget()
        self.refresh_bans()
        layout.addWidget(self.bans_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("Add Ban")
        add_btn.clicked.connect(self.add_ban)
        remove_btn = QPushButton("Remove Ban")
        remove_btn.clicked.connect(self.remove_ban)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        layout.addLayout(btn_layout)
        
        self.bans_tab.setLayout(layout)
        
    def refresh_locks(self):
        self.locks_list.clear()
        for team in self.locked_teams:
            names = [self.get_player_name(pid) for pid in team]
            item = QListWidgetItem(" + ".join(names))
            item.setData(Qt.ItemDataRole.UserRole, team)
            self.locks_list.addItem(item)
            
    def refresh_bans(self):
        self.bans_list.clear()
        for pair in self.banned_pairs:
            names = [self.get_player_name(pid) for pid in pair]
            item = QListWidgetItem(" <> ".join(names))
            item.setData(Qt.ItemDataRole.UserRole, pair)
            self.bans_list.addItem(item)

    def add_lock(self):
        self.show_add_dialog("Add Player Lock", self.locked_teams, is_lock=True)

    def add_ban(self):
        self.show_add_dialog("Add Banned Pair", self.banned_pairs, is_lock=False)
        
    def show_add_dialog(self, title, target_list, is_lock):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()
        
        combo1 = QComboBox()
        combo2 = QComboBox()
        
        sorted_players = sorted(self.players, key=lambda p: p.name)
        
        # Identify players who are already locked
        locked_player_ids = set()
        if is_lock:
            for team in self.locked_teams:
                for pid in team:
                    locked_player_ids.add(pid)
        
        # Helper to update a combo's items
        def update_combo_options(combo, exclude_id=None):
            # Block signals to prevent recursion loops
            combo.blockSignals(True)
            
            # Save current selection
            current_id = combo.currentData()
            
            combo.clear()
            combo.addItem("(Select a player)", None)
            
            found_current = False
            for p in sorted_players:
                # Skip if player is already locked (and we are adding a lock)
                if is_lock and p.id in locked_player_ids:
                    continue
                    
                if p.id != exclude_id:
                    combo.addItem(p.name, p.id)
                    if p.id == current_id:
                        found_current = True
            
            # Restore selection if still valid, otherwise reset
            if found_current:
                 index = combo.findData(current_id)
                 combo.setCurrentIndex(index)
            else:
                 combo.setCurrentIndex(0)
                 
            combo.blockSignals(False)
        
        # Initial population
        update_combo_options(combo1)
        update_combo_options(combo2)

        def on_combo1_changed(index):
            selected_id = combo1.currentData()
            update_combo_options(combo2, selected_id)
            
        def on_combo2_changed(index):
            selected_id = combo2.currentData()
            update_combo_options(combo1, selected_id)
            
        combo1.currentIndexChanged.connect(on_combo1_changed)
        combo2.currentIndexChanged.connect(on_combo2_changed)

        layout.addWidget(QLabel("Player 1:"))
        layout.addWidget(combo1)
        layout.addWidget(QLabel("Player 2:"))
        layout.addWidget(combo2)
        
        btn = QPushButton("Add")
        layout.addWidget(btn)
        
        def on_add():
            p1 = combo1.currentData()
            p2 = combo2.currentData()
            
            if p1 is None or p2 is None:
                QMessageBox.warning(dialog, "Error", "Please select two players")
                return
            
            if p1 == p2:
                QMessageBox.warning(dialog, "Error", "Select different players")
                return
            
            # Check duplicates
            if is_lock:
                # Check if either player is already locked
                for team in self.locked_teams:
                    if p1 in team or p2 in team:
                         QMessageBox.warning(dialog, "Error", "One or both players are already in a locked team")
                         return
                new_item = [p1, p2]
            else:
                # Check if pair already banned
                if (p1, p2) in self.banned_pairs or (p2, p1) in self.banned_pairs:
                    QMessageBox.warning(dialog, "Error", "Pair already banned")
                    return
                new_item = (p1, p2)
            
            target_list.append(new_item)
            if is_lock:
                self.refresh_locks()
            else:
                self.refresh_bans()
            dialog.accept()
            
        btn.clicked.connect(on_add)
        dialog.setLayout(layout)
        dialog.exec()

    def remove_lock(self):
        row = self.locks_list.currentRow()
        if row >= 0:
            del self.locked_teams[row]
            self.refresh_locks()
            
    def remove_ban(self):
        row = self.bans_list.currentRow()
        if row >= 0:
            del self.banned_pairs[row]
            self.refresh_bans()


class SetupDialog(QDialog):
    """Dialog for session setup"""
    
    def __init__(self, parent=None, previous_players=None):
        super().__init__(parent)
        self.session: Optional[Session] = None
        self.previous_players = previous_players or []
        self.banned_pairs = []
        self.locked_teams = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Game Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Game Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Round Robin", "King of the Court", "Competitive Variety"])
        mode_layout.addWidget(self.mode_combo)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # Session Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Session Type:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Doubles", "Singles"])
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)
        
        # Number of Courts
        courts_layout = QHBoxLayout()
        courts_layout.addWidget(QLabel("Number of Courts:"))
        self.courts_spin = QSpinBox()
        self.courts_spin.setMinimum(1)
        self.courts_spin.setMaximum(10)
        self.courts_spin.setValue(4)
        courts_layout.addWidget(self.courts_spin)
        courts_layout.addStretch()
        layout.addLayout(courts_layout)

        # Court Sliding
        sliding_layout = QHBoxLayout()
        sliding_layout.addWidget(QLabel("Court Sliding:"))
        self.sliding_combo = QComboBox()
        self.sliding_combo.addItems(["Right to Left", "Left to Right", "None"])
        sliding_layout.addWidget(self.sliding_combo)
        sliding_layout.addStretch()
        layout.addLayout(sliding_layout)
        
        # Players
        layout.addWidget(QLabel("Players:"))
        self.player_widget = PlayerListWidget()
        layout.addWidget(self.player_widget)
        
        # Manage Locks Button
        manage_btn = QPushButton("🤝 Manage Partnerships & Bans")
        manage_btn.clicked.connect(self.manage_locks)
        layout.addWidget(manage_btn)
        
        # Add previous players if available
        if self.previous_players:
            for player_name in self.previous_players:
                player = Player(id=f"player_{len(self.player_widget.players)}_{datetime.now().timestamp()}", name=player_name)
                self.player_widget.players.append(player)
                item = QListWidgetItem(player_name)
                item.setData(Qt.ItemDataRole.UserRole, player.id)
                self.player_widget.player_list.addItem(item)
            self.player_widget.update_player_count()
        
        # Test data button
        test_btn = QPushButton("Add 18 Test Players")
        test_btn.clicked.connect(self.add_test_players)
        layout.addWidget(test_btn)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Start Session")
        ok_btn.clicked.connect(self.start_session)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Apply dark theme to SetupDialog
        dark_stylesheet = """
            QDialog { background-color: #2a2a2a; }
            QWidget { background-color: #2a2a2a; color: white; }
            QLabel { color: white; background-color: #2a2a2a; }
            QLineEdit { 
                background-color: #3a3a3a; 
                color: white; 
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit::placeholder { color: #aaa; }
            QComboBox { 
                background-color: #3a3a3a; 
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QComboBox QAbstractItemView { background-color: #3a3a3a; color: white; }
            QSpinBox { 
                background-color: #3a3a3a; 
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QListWidget { background-color: #3a3a3a; color: white; border: 1px solid #555; }
            QListWidget::item:selected { background-color: #2196F3; }
            QPushButton { 
                color: white; 
                background-color: #0d47a1;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton:pressed { background-color: #0d47a1; }
        """
        self.setStyleSheet(dark_stylesheet)
        
        self.setWindowTitle("Session Setup")
        self.resize(600, 500)
    
    def manage_locks(self):
        players = self.player_widget.get_players()
        if not players:
             QMessageBox.warning(self, "Error", "Add players first")
             return
        dialog = ManageLocksDialog(players, self.banned_pairs, self.locked_teams, self)
        dialog.exec()

    def add_test_players(self):
        """Add 18 test players"""
        names = [
            "Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince",
            "Eve Wilson", "Frank Castle", "Grace Lee", "Henry Davis",
            "Iris West", "Jack Ryan", "Kate Beckinsale", "Leo Martinez",
            "Maya Patel", "Noah Taylor", "Olivia Stone", "Peter Parker",
            "Quinn Adams", "Rachel Green"
        ]
        
        for name in names:
            player = Player(id=f"player_{len(self.player_widget.players)}_{datetime.now().timestamp()}", name=name)
            self.player_widget.players.append(player)
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, player.id)
            self.player_widget.player_list.addItem(item)
        
        self.player_widget.update_player_count()
    
    def start_session(self):
        """Create and start a session"""
        try:
            players = self.player_widget.get_players()
            
            if len(players) < 2:
                QMessageBox.warning(self, "Error", "At least 2 players are required")
                return
            
            mode_text = self.mode_combo.currentText()
            if mode_text == "Round Robin":
                mode: GameMode = 'round-robin'
            elif mode_text == "King of the Court":
                mode: GameMode = 'king-of-court'
            else:
                mode: GameMode = 'competitive-variety'
            
            type_text = self.type_combo.currentText()
            session_type: SessionType = 'doubles' if type_text == "Doubles" else 'singles'
            
            config = SessionConfig(
                mode=mode,
                session_type=session_type,
                players=players,
                courts=self.courts_spin.value(),
                banned_pairs=self.banned_pairs,
                locked_teams=self.locked_teams,
                court_sliding_mode=self.sliding_combo.currentText(),
                randomize_player_order=False
            )
            
            self.session = create_session(config)
            self.accept()
        except Exception as e:
            error_msg = f"Error creating session:\n{str(e)}\n\nType: {type(e).__name__}"
            print(f"CRASH: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Session Creation Error", error_msg)



class CourtDisplayWidget(QWidget):
    """Visual display of a court with team rectangles"""
    
    def __init__(self, court_number: int, session: Session, parent=None):
        super().__init__(parent)
        self.court_number = court_number
        self.session = session
        self.current_match: Optional[Match] = None
        self.default_title = f"Court {self.court_number}"
        self.custom_title = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Court header
        header = QHBoxLayout()
        self.title = ClickableLabel(self.default_title)
        self.title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title.setStyleSheet("QLabel { color: black; }")
        header.addWidget(self.title)
        header.addStretch()
        layout.addLayout(header)
        
        # Court visual area
        self.court_area = EditableCourtFrame(self)
        self.court_area.setStyleSheet("QFrame { background-color: #c4d76d; border: 2px solid #333; border-radius: 5px; }")
        self.court_area.setMinimumHeight(120)
        court_layout = QVBoxLayout(self.court_area)
        court_layout.setContentsMargins(10, 10, 10, 10)
        
        # Teams display
        teams_layout = QHBoxLayout()
        
        # Team 1 side
        team1_box = QFrame()
        team1_box.setStyleSheet("QFrame { background-color: #ff9999; border: 2px solid #cc0000; border-radius: 3px; }")
        team1_layout = QVBoxLayout(team1_box)
        team1_layout.setContentsMargins(10, 10, 10, 10)
        self.team1_label = QLabel("Team 1")
        self.team1_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.team1_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.team1_label.setStyleSheet("QLabel { color: black; }")
        team1_layout.addWidget(self.team1_label)
        teams_layout.addWidget(team1_box)
        
        # Net separator
        net = QFrame()
        net.setStyleSheet("QFrame { background-color: #333; }")
        net.setFixedWidth(4)
        teams_layout.addWidget(net)
        
        # Team 2 side
        team2_box = QFrame()
        team2_box.setStyleSheet("QFrame { background-color: #99ccff; border: 2px solid #0066cc; border-radius: 3px; }")
        team2_layout = QVBoxLayout(team2_box)
        team2_layout.setContentsMargins(10, 10, 10, 10)
        self.team2_label = QLabel("Team 2")
        self.team2_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.team2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.team2_label.setStyleSheet("QLabel { color: black; }")
        team2_layout.addWidget(self.team2_label)
        teams_layout.addWidget(team2_box)
        
        court_layout.addLayout(teams_layout, 1)
        layout.addWidget(self.court_area, 1)
        
        # Score input area
        score_layout = QHBoxLayout()
        score_label = QLabel("Scores:")
        score_label.setStyleSheet("QLabel { color: black; font-weight: bold; font-size: 12px; }")
        score_layout.addWidget(score_label)
        self.team1_score = QSpinBox()
        self.team1_score.setMinimum(0)
        self.team1_score.setMaximum(20)
        self.team1_score.setStyleSheet("QSpinBox { background-color: white; color: black; border: 1px solid #999; border-radius: 3px; padding: 5px; font-size: 12px; font-weight: bold; }")
        self.team1_score.setMinimumWidth(50)
        score_layout.addWidget(self.team1_score)
        dash_label = QLabel("-")
        dash_label.setStyleSheet("QLabel { color: black; font-weight: bold; font-size: 14px; }")
        score_layout.addWidget(dash_label)
        self.team2_score = QSpinBox()
        self.team2_score.setMinimum(0)
        self.team2_score.setMaximum(20)
        self.team2_score.setStyleSheet("QSpinBox { background-color: white; color: black; border: 1px solid #999; border-radius: 3px; padding: 5px; font-size: 12px; font-weight: bold; }")
        self.team2_score.setMinimumWidth(50)
        score_layout.addWidget(self.team2_score)
        score_layout.addStretch()
        
        # Timer display
        timer_label = QLabel("Game Duration:")
        timer_label.setStyleSheet("QLabel { color: black; font-weight: bold; font-size: 12px; }")
        score_layout.addWidget(timer_label)
        
        self.timer_display = QLabel("00:00")
        self.timer_display.setStyleSheet("QLabel { background-color: white; color: black; border: 1px solid #999; border-radius: 3px; padding: 5px; font-size: 12px; font-weight: bold; min-width: 50px; text-align: center; }")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_display.setMinimumWidth(50)
        score_layout.addWidget(self.timer_display)
        
        layout.addLayout(score_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        complete_btn = QPushButton("✓ Complete")
        complete_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 5px; border-radius: 3px; }")
        complete_btn.clicked.connect(self.complete_match_clicked)
        button_layout.addWidget(complete_btn)
        
        forfeit_btn = QPushButton("✗ Forfeit")
        forfeit_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 5px; border-radius: 3px; }")
        forfeit_btn.clicked.connect(self.forfeit_match_clicked)
        button_layout.addWidget(forfeit_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("QWidget { border: 1px solid #ddd; border-radius: 5px; padding: 5px; background-color: #f9f9f9; }")
    
    def set_match(self, match: Optional[Match]):
        """Update display with a match"""
        # Stop timer for old match
        self.timer.stop()
        self.current_match = match
        
        if not match:
            self.team1_label.setText("Waiting for\nplayers...")
            self.team2_label.setText("Waiting for\nplayers...")
            self.team1_score.setValue(0)
            self.team2_score.setValue(0)
            self.timer_display.setText("00:00")
            self.court_area.setStyleSheet("QFrame { background-color: #e0e0e0; border: 2px dashed #999; border-radius: 5px; }")
            return
        elapsed_seconds = (datetime.now() - match.start_time).total_seconds() if match.start_time else 0
        
        if 0 < elapsed_seconds <= 30:
            self.court_area.setStyleSheet("QFrame { background-color: #c4d76d; border: 3px solid #4CAF50; border-radius: 5px; }") # Green highlight
        else:
            self.court_area.setStyleSheet("QFrame { background-color: #c4d76d; border: 2px solid #333; border-radius: 5px; }")
        # Get player names
        team1_names = [get_player_name(self.session, pid) for pid in match.team1]
        team2_names = [get_player_name(self.session, pid) for pid in match.team2]
        
        self.team1_label.setText("\n".join(team1_names))
        self.team2_label.setText("\n".join(team2_names))
        
        if match.score:
            self.team1_score.setValue(match.score.get('team1_score', 0))
            self.team2_score.setValue(match.score.get('team2_score', 0))
        
        # Start timer for active matches
        self.update_timer()
        self.timer.start(1000)  # Update every second
    
    def update_timer(self):
        """Update the timer display"""
        if not self.current_match or not self.current_match.start_time:
            self.timer_display.setText("00:00")
            return
        
        from datetime import datetime
        elapsed_seconds = int((datetime.now() - self.current_match.start_time).total_seconds())
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        self.timer_display.setText(f"{minutes:02d}:{seconds:02d}")
    
    def complete_match_clicked(self):
        """Handle complete match button"""
        if not self.current_match:
            QMessageBox.warning(self, "Error", "No match to complete")
            return
        
        team1_score = self.team1_score.value()
        team2_score = self.team2_score.value()
        
        if team1_score == team2_score:
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle("Error")
            msgbox.setText("Scores must be different (winner must have higher score)")
            msgbox.setIcon(QMessageBox.Icon.Warning)
            msgbox.setStyleSheet("QMessageBox { background-color: #e0e0e0; } QMessageBox QLabel { color: black; background-color: #e0e0e0; } QPushButton { background-color: #d0d0d0; color: black; padding: 5px; border-radius: 3px; }")
            msgbox.exec()
            return
        
        # Get player names for the match
        team1_names = [get_player_name(self.session, pid) for pid in self.current_match.team1]
        team2_names = [get_player_name(self.session, pid) for pid in self.current_match.team2]
        team1_str = ", ".join(team1_names)
        team2_str = ", ".join(team2_names)
        
        # Order by winning score (higher score on top)
        if team1_score > team2_score:
            winner_str = team1_str
            winner_score = team1_score
            loser_str = team2_str
            loser_score = team2_score
        else:
            winner_str = team2_str
            winner_score = team2_score
            loser_str = team1_str
            loser_score = team1_score
        
        # Create custom dialog with large colored buttons
        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Match Completion")
        dialog.setStyleSheet("QDialog { background-color: #e0e0e0; } QLabel { color: black; background-color: #e0e0e0; }")
        
        layout = QVBoxLayout()
        
        # Score text - make it large and readable with player names, winner on top
        score_text = QLabel(f"{winner_str}: {winner_score}\nbeat\n{loser_str}: {loser_score}\n\nConfirm result?")
        score_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        score_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        score_text.setStyleSheet("QLabel { color: black; background-color: #e0e0e0; padding: 20px; line-height: 1.5; }")
        layout.addWidget(score_text)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Yes button - large green
        yes_btn = QPushButton("✓ Yes")
        yes_btn.setMinimumHeight(60)
        yes_btn.setMinimumWidth(120)
        yes_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        yes_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border: none; border-radius: 5px; padding: 10px; } QPushButton:hover { background-color: #45a049; }")
        yes_btn.clicked.connect(dialog.accept)
        
        # No button - large red
        no_btn = QPushButton("✗ No")
        no_btn.setMinimumHeight(60)
        no_btn.setMinimumWidth(120)
        no_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        no_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; border: none; border-radius: 5px; padding: 10px; } QPushButton:hover { background-color: #da190b; }")
        no_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.setMinimumWidth(400)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            success, slides = complete_match(self.session, self.current_match.id, team1_score, team2_score)
            if success:
                self.team1_score.setValue(0)
                self.team2_score.setValue(0)
                
                # Handle slides
                if slides:
                    parent = self.window()
                    if hasattr(parent, 'animate_court_sliding'):
                        parent.animate_court_sliding(slides)
                
                # Save session after completing a match
                from python.session_persistence import save_session
                save_session(self.session)
            else:
                QMessageBox.warning(self, "Error", "Failed to complete match")
    
    def forfeit_match_clicked(self):
        """Handle forfeit button"""
        if not self.current_match:
            QMessageBox.warning(self, "Error", "No match to forfeit")
            return
        
        msgbox = QMessageBox(self)
        msgbox.setWindowTitle("Confirm Forfeit")
        msgbox.setText("Are you sure you want to forfeit this match?")
        msgbox.setStyleSheet("QMessageBox { background-color: #e0e0e0; } QMessageBox QLabel { color: black; background-color: #e0e0e0; } QPushButton { background-color: #d0d0d0; color: black; padding: 5px; border-radius: 3px; }")
        msgbox.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        reply = msgbox.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            if forfeit_match(self.session, self.current_match.id):
                # Save session after forfeiting a match
                from python.session_persistence import save_session
                save_session(self.session)
            else:
                QMessageBox.warning(self, "Error", "Failed to forfeit match")
    
    def edit_court_title(self):
        """Edit the court title"""
        try:
            # Get current title (either custom or default)
            current_text = self.custom_title if self.custom_title else self.default_title
            
            # Create input dialog with dark theme
            dialog = QInputDialog(self)
            dialog.setWindowTitle("Edit Court Name")
            dialog.setLabelText("Enter new court name (or leave blank to reset):")
            dialog.setTextValue(current_text)
            dialog.setStyleSheet("""
                QInputDialog {
                    background-color: #2a2a2a;
                }
                QLabel {
                    color: white;
                    background-color: #2a2a2a;
                }
                QLineEdit {
                    background-color: #3a3a3a;
                    color: white;
                    border: 1px solid #555;
                    border-radius: 3px;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    padding: 5px 15px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            
            ok = dialog.exec()
            
            if ok == QInputDialog.DialogCode.Accepted:
                new_title = dialog.textValue()
                if new_title.strip() == "":
                    # Reset to default
                    self.custom_title = None
                    self.title.setText(self.default_title)
                else:
                    # Set custom title
                    self.custom_title = new_title.strip()
                    self.title.setText(self.custom_title)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error editing court title:\n{str(e)}")
    
    def edit_court_teams(self):
        """Edit the teams on this court (double-click handler)"""
        try:
            if not self.current_match:
                QMessageBox.warning(self, "No Match", "No match currently on this court")
                return
            
            # Get parent session window
            parent_window = self.parent()
            while parent_window and not isinstance(parent_window, SessionWindow):
                parent_window = parent_window.parent()
            
            if not parent_window:
                QMessageBox.critical(self, "Error", "Could not find parent window")
                return
            
            parent_window.edit_court_match(self.court_number, self.current_match.id)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error editing court:\n{str(e)}")


class SessionWindow(QMainWindow):
    """Main window for active session"""
    
    def __init__(self, session: Session, parent_window=None):
        super().__init__()
        try:
            self.session = session
            self.parent_window = parent_window
            self.court_widgets: Dict[int, CourtDisplayWidget] = {}
            self.sound_enabled = False
            self.last_known_matches: Dict[int, str] = {}
            self.announcement_queue: List[str] = []
            self.is_announcing = False
            self.announcement_timer = QTimer()
            self.announcement_timer.timeout.connect(self.process_announcement_queue)
            self.announcement_timer.start(1000) # Check queue every second
            self.init_ui()
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.refresh_display)
            self.update_timer.start(1000)
            self.refresh_display()
        except Exception as e:
            error_msg = f"Error initializing SessionWindow:\n{str(e)}\n\nType: {type(e).__name__}"
            print(f"SESSION WINDOW INIT ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            raise
    
    def closeEvent(self, event):
        """Handle window close"""
        self.update_timer.stop()
        
        # Save session state before closing
        from python.session_persistence import save_session
        save_session(self.session)
        
        if self.parent_window:
            self.parent_window.show()
        event.accept()

    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        
        # Title with info
        self.title = QLabel(f"{self.session.config.mode} - {self.session.config.session_type.title()}")
        self.title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.title.setStyleSheet("QLabel { color: white; background-color: #1a1a1a; padding: 10px; border-radius: 3px; }")
        main_layout.addWidget(self.title)
        
        # Main content area (courts + waiting list)
        content_layout = QHBoxLayout()
        
        # Courts section
        courts_section = QVBoxLayout()
        
        # Courts header with sound toggle
        courts_header = QHBoxLayout()
        
        courts_label = QLabel("Active Courts")
        courts_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        courts_label.setStyleSheet("QLabel { color: white; background-color: #1a1a1a; padding: 8px; border-radius: 3px; }")
        courts_header.addWidget(courts_label, 1)
        
        self.sound_toggle_btn = QPushButton("🔇")
        self.sound_toggle_btn.setCheckable(True)
        self.sound_toggle_btn.setFixedSize(40, 35)
        self.sound_toggle_btn.setToolTip("Toggle Voice Announcements")
        self.sound_toggle_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3a3a3a; 
                color: white; 
                font-size: 20px; 
                border: 1px solid #555; 
                border-radius: 3px; 
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        self.sound_toggle_btn.clicked.connect(self.toggle_sound)
        courts_header.addWidget(self.sound_toggle_btn)
        
        courts_section.addLayout(courts_header)
        
        # Courts scroll area
        courts_scroll = QScrollArea()
        courts_scroll.setWidgetResizable(True)
        courts_container = QWidget()
        courts_layout = QGridLayout(courts_container)
        courts_layout.setSpacing(10)
        
        for court_num in range(1, self.session.config.courts + 1):
            widget = CourtDisplayWidget(court_num, self.session)
            self.court_widgets[court_num] = widget
            row = (court_num - 1) // 2
            col = (court_num - 1) % 2
            courts_layout.addWidget(widget, row, col)
        
        courts_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding), 
                            (self.session.config.courts + 1) // 2, 0, 1, 2)
        courts_scroll.setWidget(courts_container)
        courts_section.addWidget(courts_scroll, 1)
        content_layout.addLayout(courts_section, 3)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(divider)
        
        # Right sidebar section (waiting list + queue)
        right_section = QVBoxLayout()
        
        # Waiting list section header with toggle button
        waiting_header = QHBoxLayout()
        waiting_label = QLabel("⏳ Waitlist")
        waiting_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        waiting_label.setStyleSheet("QLabel { color: white; background-color: #1a1a1a; padding: 8px; border-radius: 3px; }")
        waiting_header.addWidget(waiting_label)
        
        # Toggle button for wait times
        self.toggle_wait_times_btn = QPushButton("Show Time Waited")
        self.toggle_wait_times_btn.setMaximumWidth(120)
        self.toggle_wait_times_btn.setStyleSheet("QPushButton { background-color: #4a4a4a; color: white; font-weight: bold; padding: 5px; border-radius: 3px; font-size: 10px; } QPushButton:hover { background-color: #5a5a5a; }")
        self.toggle_wait_times_btn.clicked.connect(self.toggle_wait_times_display)
        self.show_wait_times = False
        waiting_header.addWidget(self.toggle_wait_times_btn)
        waiting_header.addStretch()
        
        right_section.addLayout(waiting_header)
        
        self.waiting_list = QListWidget()
        self.waiting_list.setMinimumWidth(250)
        self.waiting_list.setMaximumHeight(150)
        right_section.addWidget(self.waiting_list)
        
        self.waiting_count = QLabel("0 players waiting")
        self.waiting_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.waiting_count.setStyleSheet("QLabel { color: white; font-weight: bold; background-color: #2a2a2a; }")
        right_section.addWidget(self.waiting_count)
        
        # Queue section
        queue_label = QLabel("📋 Match Queue")
        queue_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        queue_label.setStyleSheet("QLabel { color: white; background-color: #1a1a1a; padding: 8px; border-radius: 3px; }")
        right_section.addWidget(queue_label)
        
        self.queue_list = QListWidget()
        self.queue_list.setMinimumWidth(250)
        right_section.addWidget(self.queue_list, 1)
        
        self.queue_count = QLabel("0 matches queued")
        self.queue_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.queue_count.setStyleSheet("QLabel { color: white; font-weight: bold; background-color: #2a2a2a; }")
        right_section.addWidget(self.queue_count)
        
        # History section
        history_label = QLabel("📜 Match History")
        history_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        history_label.setStyleSheet("QLabel { color: white; background-color: #1a1a1a; padding: 8px; border-radius: 3px; }")
        right_section.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.setMinimumWidth(250)
        self.history_list.itemDoubleClicked.connect(self.edit_match_history)
        right_section.addWidget(self.history_list, 1)
        
        self.history_count = QLabel("0 matches completed")
        self.history_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_count.setStyleSheet("QLabel { color: white; font-weight: bold; background-color: #2a2a2a; }")
        right_section.addWidget(self.history_count)
        
        content_layout.addLayout(right_section, 1)
        main_layout.addLayout(content_layout, 1)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        make_court_btn = QPushButton("🏗️ Make Court")
        make_court_btn.setStyleSheet("QPushButton { background-color: #555555; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        make_court_btn.clicked.connect(self.make_court)
        button_layout.addWidget(make_court_btn)
        
        players_btn = QPushButton("👥 Add/Remove Players")
        players_btn.setStyleSheet("QPushButton { background-color: #9C27B0; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        players_btn.clicked.connect(self.manage_players)
        button_layout.addWidget(players_btn)
        
        locks_btn = QPushButton("🤝 Manage Partnerships & Bans")
        locks_btn.setStyleSheet("QPushButton { background-color: #607D8B; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        locks_btn.clicked.connect(self.manage_locks)
        button_layout.addWidget(locks_btn)
        
        stats_btn = QPushButton("📊 Show Statistics")
        stats_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        stats_btn.clicked.connect(self.show_statistics)
        button_layout.addWidget(stats_btn)
        
        export_btn = QPushButton("📥 Export Session")
        export_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        export_btn.clicked.connect(self.export_session)
        button_layout.addWidget(export_btn)
        
        end_btn = QPushButton("End Session")
        end_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        end_btn.clicked.connect(self.end_session)
        button_layout.addWidget(end_btn)
        
        button_layout.addStretch()
        
        announce_btn = QPushButton("📢 Announce Courts")
        announce_btn.setStyleSheet("QPushButton { background-color: #673AB7; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        announce_btn.clicked.connect(self.announce_all_courts)
        button_layout.addWidget(announce_btn)
        
        main_layout.addLayout(button_layout)
        
        central_widget.setLayout(main_layout)
        
        # Apply dark theme to SessionWindow
        dark_stylesheet = """
            QMainWindow { background-color: #2a2a2a; }
            QWidget { background-color: #2a2a2a; color: white; }
            QLabel { color: white; background-color: #2a2a2a; }
            QListWidget { background-color: #3a3a3a; color: white; border: 1px solid #555; }
            QListWidget::item:selected { background-color: #2196F3; }
            QScrollArea { background-color: #2a2a2a; }
            QFrame { background-color: #2a2a2a; color: white; }
            QPushButton { color: white; }
        """
        self.setStyleSheet(dark_stylesheet)
        
        self.setWindowTitle("Pickleball Session Manager")
        self.resize(1400, 800)
    
    def toggle_sound(self):
        """Toggle sound announcements"""
        self.sound_enabled = self.sound_toggle_btn.isChecked()
        if self.sound_enabled:
            self.sound_toggle_btn.setText("🔊")
        else:
            self.sound_toggle_btn.setText("🔇")

    def announce_all_courts(self):
        """Announce all currently active courts"""
        has_matches = False
        for widget in self.court_widgets.values():
            if widget.current_match:
                has_matches = True
                break
        
        if not has_matches:
            self.announcement_queue.append("No matches are currently in progress.")
            return

        self.announcement_queue.append("Announcing current matches.")
        
        for court_num in sorted(self.court_widgets.keys()):
            widget = self.court_widgets[court_num]
            if widget.current_match:
                try:
                    match = widget.current_match
                    team1_names = [get_player_name(self.session, pid) for pid in match.team1]
                    team2_names = [get_player_name(self.session, pid) for pid in match.team2]
                    
                    court_name = widget.custom_title if widget.custom_title else f"Court {court_num}"
                    
                    t1_str = " And ".join(team1_names)
                    t2_str = " And ".join(team2_names)
                    
                    text = f"On {court_name}, {t1_str} versus {t2_str}."
                    self.announcement_queue.append(text)
                except Exception as e:
                    print(f"Error announcing court {court_num}: {e}")

    def play_sound(self, sound_path):
        """Play a sound file in a cross-platform way"""
        import platform
        system = platform.system()
        
        if system == "Darwin": # macOS
            subprocess.Popen(f"afplay {sound_path}", shell=True)
        elif system == "Linux":
            subprocess.Popen(f"aplay {sound_path}", shell=True)
        elif system == "Windows":
            # PowerShell command to play sound
            cmd = f'powershell -c (New-Object Media.SoundPlayer "{sound_path}").PlaySync()'
            subprocess.Popen(cmd, shell=True)

    def announce_match(self, court_num: int, match: Match):
        """Queue a match announcement"""
        try:
            team1_names = [get_player_name(self.session, pid) for pid in match.team1]
            team2_names = [get_player_name(self.session, pid) for pid in match.team2]
            
            # Format: "New Match Ready on Court <courtName>, <Player1> And <Player2> versus <Player3> And <Player4>."
            
            court_name = f"Court {court_num}"
            if court_num in self.court_widgets:
                widget = self.court_widgets[court_num]
                if widget.custom_title:
                    court_name = widget.custom_title
            
            t1_str = " And ".join(team1_names)
            t2_str = " And ".join(team2_names)
            
            text = f"New Match Ready on {court_name}, {t1_str} versus {t2_str}."
            self.announcement_queue.append(text)
            
        except Exception as e:
            print(f"Error queueing announcement: {e}")

    def process_announcement_queue(self):
        """Process the next announcement in the queue if not currently announcing"""
        if self.is_announcing or not self.announcement_queue:
            return

        self.is_announcing = True
        text = self.announcement_queue.pop(0)
        
        try:
            import platform
            system = platform.system()
            
            # Construct command based on OS
            if system == "Darwin": # macOS
                subprocess.Popen(f"say \"{text}\"", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            elif system == "Linux":
                # espeak is a common TTS on Linux
                subprocess.Popen(f"espeak \"{text}\"", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            elif system == "Windows":
                # PowerShell for TTS
                tts_cmd = f'(New-Object -ComObject SAPI.SpVoice).Speak(\\"{text}\\") > $null'
                subprocess.Popen(f'powershell -c "{tts_cmd}"', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Estimate duration to clear the flag (rough approximation: 0.5s per word)
            word_count = len(text.split())
            duration = (word_count * 400) + 500
            
            # Reset flag after duration
            QTimer.singleShot(duration, self._reset_announcing_flag)
            
        except Exception as e:
            print(f"Error playing announcement: {e}")
            self.is_announcing = False

    def _reset_announcing_flag(self):
        self.is_announcing = False

    def update_title(self, summary: Dict):
        """Update title with session info"""
        info = f"{self.session.config.mode.title()} - {self.session.config.session_type.title()} | "
        info += f"Courts: {summary['active_matches']}/{summary['total_courts']} | "
        info += f"Queued: {summary['queued_matches']} | "
        info += f"Completed: {summary['completed_matches']}"
        
        self.title.setText(info)
    
    def manage_locks(self):
        """Open dialog to manage locks and bans"""
        if self.session.config.locked_teams is None:
            self.session.config.locked_teams = []
            
        dialog = ManageLocksDialog(self.session.config.players, self.session.config.banned_pairs, self.session.config.locked_teams, self)
        if dialog.exec():
            # Regenerate queue to respect new constraints
            try:
                # Clear existing queue
                self.session.match_queue = []
                
                # Regenerate if Round Robin
                if self.session.config.mode == 'round-robin':
                    from python.roundrobin import generate_round_robin_queue
                    
                    self.session.match_queue = generate_round_robin_queue(
                        [p for p in self.session.config.players if p.id in self.session.active_players],
                        self.session.config.session_type,
                        self.session.config.banned_pairs,
                        locked_teams=self.session.config.locked_teams,
                        player_stats=self.session.player_stats,
                        active_matches=self.session.matches
                    )
                
                # For Competitive Variety, queue is usually dynamic/empty so clearing it allows
                # the population logic to run fresh with new constraints.
                
                self.refresh_display()
                
                # Save session
                from python.session_persistence import save_session
                save_session(self.session)
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error updating queue: {str(e)}")
    
    def toggle_wait_times_display(self):
        """Toggle the display of wait times in the waitlist"""
        self.show_wait_times = not self.show_wait_times
        if self.show_wait_times:
            self.toggle_wait_times_btn.setText("Hide Time Waited")
        else:
            self.toggle_wait_times_btn.setText("Show Time Waited")
        # Trigger a refresh to update the display
        self.refresh_display()
    
    def animate_court_sliding(self, slides: List[Dict]):
        """Animate court changes"""
        self.update_timer.stop()
        self.pending_slides = slides  # Store slides to handle announcements later
        
        # Container for ghosts - use the widget inside the scroll area
        # self.court_widgets[1] is a CourtDisplayWidget
        if not self.court_widgets:
            self.refresh_display()
            self.update_timer.start(1000)
            return

        first_court = self.court_widgets[1]
        container = first_court.parent()
        
        self.animation_group = QParallelAnimationGroup()
        self.ghosts = [] # Keep references to delete later
        
        # Sort slides to handle overlapping movements if necessary?
        # Parallel animation handles it fine visually.
        
        for slide in slides:
            src_idx = slide['from']
            dst_idx = slide['to']
            
            if src_idx not in self.court_widgets or dst_idx not in self.court_widgets:
                continue

            src_widget = self.court_widgets[src_idx]
            dst_widget = self.court_widgets[dst_idx]
            
            # Create snapshot of source
            pixmap = QPixmap(src_widget.size())
            src_widget.render(pixmap)
            
            # Create cover for source (to hide the static widget underneath)
            # Use a color that matches the background or looks like an empty slot
            cover = QLabel(container)
            cover.setStyleSheet("background-color: #2a2a2a;") 
            cover.setGeometry(src_widget.geometry())
            cover.show()
            self.ghosts.append(cover)
            
            # Create ghost label
            ghost = QLabel(container)
            ghost.setPixmap(pixmap)
            ghost.setGeometry(src_widget.geometry())
            ghost.show()
            self.ghosts.append(ghost)
            
            # Animation
            anim = QPropertyAnimation(ghost, b"pos")
            anim.setDuration(600) # 600ms for a snappy slide
            anim.setStartValue(src_widget.pos())
            anim.setEndValue(dst_widget.pos())
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            
            self.animation_group.addAnimation(anim)
            
            # Raise ghost to ensure it flies over everything
            ghost.raise_()

        # Connect finished signal
        self.animation_group.finished.connect(self.on_animation_finished)
        self.animation_group.start()

    def on_animation_finished(self):
        """Cleanup after animation"""
        for ghost in self.ghosts:
            ghost.deleteLater()
        self.ghosts = []
        
        # Pre-update last_known_matches for slid matches to prevent announcement
        if hasattr(self, 'pending_slides'):
            for slide in self.pending_slides:
                dst_idx = slide['to']
                match_id = slide['match_id']
                self.last_known_matches[dst_idx] = match_id
            self.pending_slides = []
        
        self.refresh_display()
        self.update_timer.start(1000)

    def refresh_display(self):
        """Refresh court displays"""
        try:
            from python.queue_manager import (
                populate_empty_courts, get_match_for_court, get_session_summary,
                get_waiting_players, get_queued_matches_for_display
            )
            from python.utils import start_player_wait_timer, stop_player_wait_timer
            
            populate_empty_courts(self.session)
            
            # Update court displays and stop wait timers for players in matches
            players_in_matches = set()
            for court_num in range(1, self.session.config.courts + 1):
                widget = self.court_widgets.get(court_num)
                if widget is None:
                    continue
                match = get_match_for_court(self.session, court_num)
                
                # Check for new match announcement
                current_match_id = match.id if match else None
                last_match_id = self.last_known_matches.get(court_num)
                
                if current_match_id and current_match_id != last_match_id:
                    # New match detected
                    if self.sound_enabled:
                        self.announce_match(court_num, match)
                
                self.last_known_matches[court_num] = current_match_id
                
                widget.set_match(match)
                if match:
                    players_in_matches.update(match.team1 + match.team2)
                    # Stop wait timers for players now in a match
                    for player_id in (match.team1 + match.team2):
                        if player_id in self.session.player_stats:
                            stop_player_wait_timer(self.session.player_stats[player_id])
            
            # Update waiting players list and start wait timers
            waiting_ids = get_waiting_players(self.session)
            self.waiting_list.clear()
            for player_id in waiting_ids:
                player_name = get_player_name(self.session, player_id)
                # Start wait timer for players on waitlist
                if player_id in self.session.player_stats:
                    start_player_wait_timer(self.session.player_stats[player_id])
                    # Get current wait time and format it only if toggle is on
                    if self.show_wait_times:
                        from python.utils import get_current_wait_time, format_duration
                        stats = self.session.player_stats[player_id]
                        
                        # Current wait time (since last match)
                        current_wait = get_current_wait_time(stats)
                        current_wait_str = format_duration(current_wait)
                        
                        # Total accumulated wait time
                        total_wait = stats.total_wait_time + current_wait
                        total_wait_str = format_duration(total_wait)
                        
                        item_text = f"{player_name}  [{current_wait_str} / {total_wait_str}]"
                    else:
                        item_text = player_name
                else:
                    item_text = player_name
                self.waiting_list.addItem(item_text)
            
            self.waiting_count.setText(f"{len(waiting_ids)} player{'s' if len(waiting_ids) != 1 else ''} waiting")
            
            # Update queued matches list
            queued_matches = get_queued_matches_for_display(self.session)
            self.queue_list.clear()
            for team1_str, team2_str in queued_matches:
                item_text = f"{team1_str}\nvs\n{team2_str}"
                self.queue_list.addItem(item_text)
            
            self.queue_count.setText(f"{len(queued_matches)} match{'es' if len(queued_matches) != 1 else ''} queued")
            
            # Update match history list
            from python.session import get_completed_matches
            completed = get_completed_matches(self.session)
            self.history_list.clear()
            # Sort by end_time descending (most recent first), then add to list
            sorted_completed = sorted(completed, key=lambda m: m.end_time or '', reverse=True)
            for match in sorted_completed:
                team1_names = [get_player_name(self.session, pid) for pid in match.team1]
                team2_names = [get_player_name(self.session, pid) for pid in match.team2]
                team1_str = ", ".join(team1_names)
                team2_str = ", ".join(team2_names)
                
                if match.score:
                    t1_score = match.score.get('team1_score', 0)
                    t2_score = match.score.get('team2_score', 0)
                    item_text = f"{team1_str} {t1_score}\nvs\n{team2_str} {t2_score}"
                else:
                    item_text = f"{team1_str}\nvs\n{team2_str}"
                
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, match.id)
                self.history_list.addItem(item)
            
            self.history_count.setText(f"{len(completed)} match{'es' if len(completed) != 1 else ''} completed")
            
            # Update summary info
            summary = get_session_summary(self.session)
            self.update_title(summary)
        except Exception as e:
            error_msg = f"Error in refresh_display:\n{str(e)}"
            print(f"REFRESH ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
    
    def export_session(self):
        """Export session results to a file"""
        try:
            from python.queue_manager import get_waiting_players, get_match_for_court
            from datetime import datetime
            
            # Get current state
            waiting_ids = get_waiting_players(self.session)
            
            # Build export data
            export_lines = []
            export_lines.append(f"Pickleball Session Export")
            export_lines.append(f"{'='*70}")
            export_lines.append(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            export_lines.append(f"Mode: {self.session.config.mode.title()}")
            export_lines.append(f"Type: {self.session.config.session_type.title()}")
            export_lines.append(f"Courts: {self.session.config.courts}")
            export_lines.append("")
            
            # Active matches on courts
            export_lines.append("CURRENTLY ON COURTS:")
            export_lines.append("-" * 70)
            for court_num in range(1, self.session.config.courts + 1):
                match = get_match_for_court(self.session, court_num)
                if match:
                    team1_names = [get_player_name(self.session, pid) for pid in match.team1]
                    team2_names = [get_player_name(self.session, pid) for pid in match.team2]
                    export_lines.append(f"Court {court_num}: {', '.join(team1_names)} vs {', '.join(team2_names)}")
                else:
                    export_lines.append(f"Court {court_num}: Empty")
            export_lines.append("")
            
            # Waitlist
            export_lines.append("WAITLIST:")
            export_lines.append("-" * 70)
            if waiting_ids:
                for player_id in waiting_ids:
                    player_name = get_player_name(self.session, player_id)
                    export_lines.append(f"  - {player_name}")
            else:
                export_lines.append("  (No players waiting)")
            export_lines.append("")
            
            # Player statistics sorted by ELO
            export_lines.append("PLAYER STATISTICS (sorted by ELO):")
            export_lines.append("-" * 70)
            
            # Collect player data with ELO ratings
            player_data = []
            for player in self.session.config.players:
                if player.id not in self.session.active_players:
                    continue
                
                stats = self.session.player_stats[player.id]
                
                # Calculate ELO rating for all modes
                elo = 0
                try:
                    if self.session.config.mode == 'competitive-variety':
                        from python.competitive_variety import calculate_elo_rating
                        elo = calculate_elo_rating(stats)
                    else:
                        # For other modes, use a simple ELO-like calculation
                        from python.kingofcourt import calculate_player_rating
                        elo = calculate_player_rating(stats)
                except:
                    # Fallback if ELO calculation fails
                    elo = 1500 if stats.games_played == 0 else (1500 + (stats.wins - stats.losses) * 50)
                
                record = f"{stats.wins}-{stats.losses}"
                win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
                
                # Include wait time (accumulated + current if waiting)
                from python.utils import get_current_wait_time, format_duration
                current_wait = get_current_wait_time(stats)
                total_wait_seconds = stats.total_wait_time + current_wait
                
                # Calculate average point differential
                avg_pt_diff = (stats.total_points_for - stats.total_points_against) / stats.games_played if stats.games_played > 0 else 0
                
                player_data.append((player.name, elo, record, stats.games_played, win_pct, total_wait_seconds, avg_pt_diff, stats.total_points_for, stats.total_points_against))
            
            # Sort by ELO descending
            player_data.sort(key=lambda x: x[1], reverse=True)
            
            # Write header
            export_lines.append(f"{'Player':<25} {'ELO':<10} {'W-L':<10} {'Games':<10} {'Win %':<10} {'Wait Time':<12} {'Avg Pt Diff':<15} {'Pts For':<10} {'Pts Against':<12}")
            export_lines.append("-" * 132)
            
            # Write player data
            for player_name, elo, record, games_played, win_pct, total_wait_seconds, avg_pt_diff, pts_for, pts_against in player_data:
                win_pct_str = f"{win_pct:.1f}%" if games_played > 0 else "N/A"
                wait_time_str = format_duration(total_wait_seconds)
                avg_pt_diff_str = f"{avg_pt_diff:.1f}" if games_played > 0 else "N/A"
                export_lines.append(
                    f"{player_name:<25} {elo:<10.0f} {record:<10} {games_played:<10} {win_pct_str:<10} {wait_time_str:<12} {avg_pt_diff_str:<15} {pts_for:<10} {pts_against:<12}"
                )
            
            export_lines.append("")
            
            # Match History (most recent first)
            completed_matches = [m for m in self.session.matches if m.status == 'completed']
            if completed_matches:
                export_lines.append("MATCH HISTORY:")
                export_lines.append("-" * 70)
                
                from python.utils import calculate_match_duration, format_duration
                
                total_duration = 0
                match_count = 0
                
                for match in reversed(completed_matches):
                    team1_names = [get_player_name(self.session, pid) for pid in match.team1]
                    team2_names = [get_player_name(self.session, pid) for pid in match.team2]
                    
                    if match.score:
                        team1_score = match.score.get('team1_score', 0)
                        team2_score = match.score.get('team2_score', 0)
                        
                        # Calculate match duration
                        duration = calculate_match_duration(match)
                        duration_str = format_duration(duration) if duration else "N/A"
                        
                        if duration:
                            total_duration += duration
                            match_count += 1
                        
                        # Format: Higher score on top
                        if team1_score >= team2_score:
                            export_lines.append(f"{', '.join(team1_names)}: {team1_score} beat {', '.join(team2_names)}: {team2_score} [{duration_str}]")
                        else:
                            export_lines.append(f"{', '.join(team2_names)}: {team2_score} beat {', '.join(team1_names)}: {team1_score} [{duration_str}]")
                
                # Add average duration
                if match_count > 0:
                    avg_duration = total_duration // match_count
                    avg_duration_str = format_duration(avg_duration)
                    export_lines.append("")
                    export_lines.append(f"Average Match Duration: {avg_duration_str}")
                
                export_lines.append("")
            
            export_lines.append("=" * 70)
            
            # Write to file
            export_text = "\n".join(export_lines)
            
            # Save to file in current directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pickleball_session_{timestamp}.txt"
            filepath = os.path.join(os.getcwd(), filename)
            
            with open(filepath, 'w') as f:
                f.write(export_text)
            
            QMessageBox.information(
                self, "Export Successful",
                f"Session exported to:\n{filename}"
            )
            
        except Exception as e:
            error_msg = f"Error exporting session:\n{str(e)}"
            print(f"EXPORT ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", error_msg)
    
    def manage_players(self):
        """Open dialog to add or remove players"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("Manage Players")
            dialog.setStyleSheet("QDialog { background-color: #2a2a2a; } QLabel { color: white; }")
            dialog.setMinimumWidth(600)
            dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout()
            
            # Track pending changes
            players_to_add = []
            players_to_remove = []
            
            # Add new player section
            add_section = QGroupBox("Add New Player")
            add_section.setStyleSheet("QGroupBox { color: white; background-color: #2a2a2a; border: 1px solid #555; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }")
            add_layout = QHBoxLayout()
            
            name_input = QLineEdit()
            name_input.setPlaceholderText("Enter player name")
            name_input.setStyleSheet("QLineEdit { background-color: #3a3a3a; color: white; border: 1px solid #555; border-radius: 3px; padding: 5px; }")
            add_layout.addWidget(name_input)
            
            add_btn = QPushButton("Add Player")
            add_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 5px 15px; border-radius: 3px; }")
            add_layout.addWidget(add_btn)
            
            add_section.setLayout(add_layout)
            layout.addWidget(add_section)
            
            # Current players section
            remove_section = QGroupBox("Remove Player")
            remove_section.setStyleSheet("QGroupBox { color: white; background-color: #2a2a2a; border: 1px solid #555; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }")
            remove_layout = QVBoxLayout()
            
            player_list = QListWidget()
            player_list.setStyleSheet("""
                QListWidget { 
                    background-color: #3a3a3a; 
                    color: white;
                    border: 1px solid #555;
                    border-radius: 3px;
                }
                QListWidget::item:selected {
                    background-color: #2196F3;
                }
            """)
            
            # Populate player list
            def refresh_player_list():
                player_list.clear()
                # Show current players minus those marked for removal
                current_player_ids = self.session.active_players - set(players_to_remove)
                for player in self.session.config.players:
                    if player.id in current_player_ids:
                        in_game = "🟢 ON COURT" if any(player.id in m.team1 + m.team2 for m in self.session.matches if m.status in ['waiting', 'in-progress']) else ""
                        status = "❌ REMOVED" if player.id in players_to_remove else in_game
                        item_text = f"{player.name} {status}"
                        item = QListWidgetItem(item_text)
                        item.setData(Qt.ItemDataRole.UserRole, player.id)
                        player_list.addItem(item)
                
                # Show newly added players
                for player_name in players_to_add:
                    item_text = f"{player_name} ✨ NEW"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, f"new_{player_name}")
                    player_list.addItem(item)
            
            refresh_player_list()
            remove_layout.addWidget(player_list)
            
            remove_btn = QPushButton("Remove Selected Player")
            remove_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 5px 15px; border-radius: 3px; }")
            remove_layout.addWidget(remove_btn)
            
            remove_section.setLayout(remove_layout)
            layout.addWidget(remove_section)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            save_btn = QPushButton("Save and Close")
            save_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
            button_layout.addStretch()
            button_layout.addWidget(save_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            # Connect buttons
            def add_player():
                player_name = name_input.text().strip()
                if not player_name:
                    QMessageBox.warning(dialog, "Error", "Please enter a player name")
                    return
                
                # Check if player already exists (in session or in add queue)
                if any(p.name.lower() == player_name.lower() for p in self.session.config.players):
                    QMessageBox.warning(dialog, "Error", "Player already exists")
                    return
                
                if any(name.lower() == player_name.lower() for name in players_to_add):
                    QMessageBox.warning(dialog, "Error", "Player already queued for addition")
                    return
                
                players_to_add.append(player_name)
                name_input.clear()
                refresh_player_list()
            
            def remove_player():
                current_item = player_list.currentItem()
                if not current_item:
                    QMessageBox.warning(dialog, "Error", "Please select a player to remove")
                    return
                
                player_id = current_item.data(Qt.ItemDataRole.UserRole)
                
                # Handle newly added players
                if player_id.startswith("new_"):
                    player_name = player_id[4:]
                    if player_name in players_to_add:
                        players_to_add.remove(player_name)
                else:
                    # Handle existing players
                    if player_id not in players_to_remove:
                        players_to_remove.append(player_id)
                    else:
                        players_to_remove.remove(player_id)
                
                refresh_player_list()
            
            def save_changes():
                try:
                    # Remove players
                    for player_id in players_to_remove:
                        player = next((p for p in self.session.config.players if p.id == player_id), None)
                        if not player:
                            continue
                        
                        # Forfeit any active matches
                        for match in self.session.matches:
                            if match.status in ['waiting', 'in-progress']:
                                if player_id in match.team1 or player_id in match.team2:
                                    forfeit_match(self.session, match.id)
                        
                        # Remove from active players (keeps in config to preserve history)
                        remove_player_from_session(self.session, player_id)
                    
                    # Add players
                    for player_name in players_to_add:
                        new_player = Player(id=f"player_{datetime.now().timestamp()}", name=player_name)
                        add_player_to_session(self.session, new_player)
                    
                    # Regenerate match queue once at the end
                    if players_to_add or players_to_remove:
                        from python.roundrobin import generate_round_robin_queue
                        from python.queue_manager import populate_empty_courts, get_waiting_players
                        
                        if self.session.config.mode == 'round-robin':
                            self.session.match_queue = generate_round_robin_queue(
                                [p for p in self.session.config.players if p.id in self.session.active_players],
                                self.session.config.session_type,
                                self.session.config.banned_pairs,
                                player_stats=self.session.player_stats,
                                active_matches=self.session.matches
                            )
                        else:
                            # For competitive-variety, clear the queue to let dynamic allocator handle it
                            self.session.match_queue = []
                        
                        # Prioritize matches with waiting players at the front of the queue
                        if self.session.match_queue:
                            waiting_ids = set(get_waiting_players(self.session))
                            if waiting_ids:
                                waiting_matches = []
                                other_matches = []
                                for queued_match in self.session.match_queue:
                                    match_players = set(queued_match.team1 + queued_match.team2)
                                    if match_players & waiting_ids:
                                        waiting_matches.append(queued_match)
                                    else:
                                        other_matches.append(queued_match)
                                self.session.match_queue = waiting_matches + other_matches
                        
                        # Populate any empty courts with the newly regenerated queue
                        populate_empty_courts(self.session)
                        self.refresh_display()
                    
                    dialog.accept()
                except Exception as e:
                    QMessageBox.critical(dialog, "Error", f"Error saving changes:\n{str(e)}")
            
            add_btn.clicked.connect(add_player)
            remove_btn.clicked.connect(remove_player)
            save_btn.clicked.connect(save_changes)
            
            dialog.exec()
            
        except Exception as e:
            error_msg = f"Error managing players:\n{str(e)}"
            print(f"PLAYER MANAGEMENT ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def edit_match_history(self, item):
        """Edit a match from history"""
        try:
            match_id = item.data(Qt.ItemDataRole.UserRole)
            
            # Find the match
            match = None
            for m in self.session.matches:
                if m.id == match_id:
                    match = m
                    break
            
            if not match:
                QMessageBox.warning(self, "Error", "Match not found")
                return
            
            # Create edit dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Match Score")
            dialog.setStyleSheet("QDialog { background-color: #e0e0e0; } QLabel { color: black; background-color: #e0e0e0; }")
            
            layout = QVBoxLayout()
            
            # Team info
            team1_names = [get_player_name(self.session, pid) for pid in match.team1]
            team2_names = [get_player_name(self.session, pid) for pid in match.team2]
            team1_str = ", ".join(team1_names)
            team2_str = ", ".join(team2_names)
            
            title_label = QLabel(f"Edit Score:\n{team1_str} vs {team2_str}")
            title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            title_label.setStyleSheet("QLabel { color: black; background-color: #e0e0e0; padding: 10px; }")
            layout.addWidget(title_label)
            
            # Score inputs
            score_layout = QHBoxLayout()
            score_layout.addWidget(QLabel("Team 1 Score:"))
            team1_spin = QSpinBox()
            team1_spin.setMinimum(0)
            team1_spin.setMaximum(20)
            if match.score:
                team1_spin.setValue(match.score.get('team1_score', 0))
            score_layout.addWidget(team1_spin)
            
            score_layout.addWidget(QLabel("Team 2 Score:"))
            team2_spin = QSpinBox()
            team2_spin.setMinimum(0)
            team2_spin.setMaximum(20)
            if match.score:
                team2_spin.setValue(match.score.get('team2_score', 0))
            score_layout.addWidget(team2_spin)
            
            layout.addLayout(score_layout)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            save_btn = QPushButton("Save")
            save_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 5px; }")
            button_layout.addWidget(save_btn)
            
            # Check if there's a snapshot for this match to enable Load button
            has_snapshot = any(snap.match_id == match_id for snap in self.session.match_history_snapshots)
            
            load_btn = QPushButton("Load")
            load_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 5px; }")
            load_btn.setEnabled(has_snapshot)
            if has_snapshot:
                load_btn.setToolTip("Load session to state before this match was completed")
            else:
                load_btn.setToolTip("No saved state for this match")
            button_layout.addWidget(load_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 5px; }")
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            def save_changes():
                t1_score = team1_spin.value()
                t2_score = team2_spin.value()
                
                if t1_score == t2_score:
                    msgbox = QMessageBox(dialog)
                    msgbox.setWindowTitle("Error")
                    msgbox.setText("Scores must be different")
                    msgbox.setIcon(QMessageBox.Icon.Warning)
                    msgbox.setStyleSheet("QMessageBox { background-color: #e0e0e0; } QMessageBox QLabel { color: black; background-color: #e0e0e0; } QPushButton { background-color: #d0d0d0; color: black; padding: 5px; border-radius: 3px; }")
                    msgbox.exec()
                    return
                
                match.score = {'team1_score': t1_score, 'team2_score': t2_score}
                dialog.accept()
                self.refresh_display()
            
            def load_state():
                # Find the snapshot for this match
                snapshot = None
                for snap in self.session.match_history_snapshots:
                    if snap.match_id == match_id:
                        snapshot = snap
                        break
                
                if not snapshot:
                    QMessageBox.warning(dialog, "Error", "Could not find saved state for this match")
                    return
                
                # Load the state
                from python.session import load_session_from_snapshot
                success = load_session_from_snapshot(self.session, snapshot)
                
                if success:
                    dialog.accept()
                    self.refresh_display()
                    QMessageBox.information(self, "Success", "Session loaded to state before this match was completed")
                else:
                    QMessageBox.critical(dialog, "Error", "Failed to load session state")
            
            save_btn.clicked.connect(save_changes)
            load_btn.clicked.connect(load_state)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error editing match:\n{str(e)}")
    
    def show_statistics(self):
        """Show detailed statistics for all players"""
        try:
            # Create statistics dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Player Statistics")
            dialog.setStyleSheet("QDialog { background-color: #2a2a2a; } QLabel { color: white; background-color: #2a2a2a; }")
            dialog.setMinimumWidth(1000)
            dialog.setMinimumHeight(600)
            
            layout = QVBoxLayout()
            
            # Determine columns based on game mode
            is_competitive_variety = self.session.config.mode == 'competitive-variety'
            
            if is_competitive_variety:
                # Include ELO rating for competitive variety
                column_labels = [
                    "Player", "ELO", "W-L", "Games", "Waited", "Wait Time", "Win %", 
                    "Partners", "Opponents", "Avg Pt Diff", "Pts For", "Pts Against"
                ]
                num_columns = 12
            else:
                column_labels = [
                    "Player", "W-L", "Games", "Waited", "Wait Time", "Win %", 
                    "Partners", "Opponents", "Avg Pt Diff", "Pts For", "Pts Against"
                ]
                num_columns = 11
            
            # Create table
            table = QTableWidget()
            table.setColumnCount(num_columns)
            table.setHorizontalHeaderLabels(column_labels)
            table.setStyleSheet("""
                QTableWidget { 
                    background-color: #3a3a3a; 
                    color: white;
                    gridline-color: #555;
                }
                QTableWidget::item { 
                    padding: 5px;
                    color: white;
                }
                QHeaderView::section { 
                    background-color: #1a1a1a; 
                    color: white; 
                    padding: 5px;
                    border: none;
                    font-weight: bold;
                }
            """)
            
            # Collect player data for sorting
            player_data = []
            for player in self.session.config.players:
                if player.id not in self.session.active_players:
                    continue
                
                stats = self.session.player_stats[player.id]
                
                # Calculate ELO rating if in competitive variety mode
                if is_competitive_variety:
                    from python.competitive_variety import calculate_elo_rating
                    elo = calculate_elo_rating(stats)
                else:
                    elo = 0
                
                # Calculate average point differential
                if stats.games_played > 0:
                    avg_diff = (stats.total_points_for - stats.total_points_against) / stats.games_played
                else:
                    avg_diff = 0
                
                # Win percentage
                win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
                
                # Get current wait time (in case player is currently waiting)
                from python.utils import get_current_wait_time
                current_wait = get_current_wait_time(stats)
                total_wait_seconds = stats.total_wait_time + current_wait
                
                player_data.append((
                    player.name,
                    elo,
                    stats.wins,
                    stats.losses,
                    stats.games_played,
                    stats.games_waited,
                    total_wait_seconds,
                    win_pct,
                    len(stats.partners_played),
                    len(stats.opponents_played),
                    avg_diff,
                    stats.total_points_for,
                    stats.total_points_against
                ))
            
            # Sort based on game mode
            if is_competitive_variety:
                # Sort by ELO (descending) for competitive variety
                player_data.sort(key=lambda x: -x[1])
            else:
                # Sort by wins (descending), then by losses (ascending), then by avg_diff (descending)
                player_data.sort(key=lambda x: (-x[2], x[3], -x[10]))
            
            # Populate table
            for row, data in enumerate(player_data):
                table.insertRow(row)
                
                from python.utils import format_duration
                
                if is_competitive_variety:
                    items = [
                        data[0],  # name
                        f"{data[1]:.0f}",  # ELO
                        f"{data[2]}-{data[3]}",  # W-L
                        str(data[4]),  # games
                        str(data[5]),  # waited (count)
                        format_duration(data[6]),  # wait time (seconds)
                        f"{data[7]:.1f}%",  # win %
                        str(data[8]),  # partners
                        str(data[9]),  # opponents
                        f"{data[10]:.1f}",  # avg pt diff
                        str(data[11]),  # pts for
                        str(data[12])  # pts against
                    ]
                else:
                    items = [
                        data[0],  # name
                        f"{data[2]}-{data[3]}",  # W-L
                        str(data[4]),  # games
                        str(data[5]),  # waited (count)
                        format_duration(data[6]),  # wait time (seconds)
                        f"{data[7]:.1f}%",  # win %
                        str(data[8]),  # partners
                        str(data[9]),  # opponents
                        f"{data[10]:.1f}",  # avg pt diff
                        str(data[11]),  # pts for
                        str(data[12])  # pts against
                    ]
                
                for col, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    item.setForeground(QColor("white"))
                    table.setItem(row, col, item)
            
            table.resizeColumnsToContents()
            layout.addWidget(table)
            
            # Close button
            close_btn = QPushButton("Close")
            close_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; border-radius: 3px; }")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error showing statistics:\n{str(e)}")
    
    def make_court(self):
        """Open dialog to manually create a match on an empty court"""
        try:
            from python.queue_manager import get_empty_courts, get_waiting_players
            from python.session import create_manual_match
            
            empty_courts = get_empty_courts(self.session)
            waiting_ids = get_waiting_players(self.session)
            
            if not empty_courts:
                QMessageBox.warning(self, "No Empty Courts", "All courts are currently occupied")
                return
            
            if len(waiting_ids) < 4:
                QMessageBox.warning(self, "Not Enough Players", "Need at least 4 players in the waitlist")
                return
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Make Court")
            dialog.setStyleSheet("QDialog { background-color: #2a2a2a; } QLabel { color: white; background-color: #2a2a2a; } QComboBox { background-color: #3a3a3a; color: white; border: 1px solid #555; border-radius: 3px; padding: 5px; }")
            dialog.setMinimumWidth(500)
            
            layout = QVBoxLayout()
            
            # Court selection
            court_layout = QHBoxLayout()
            court_layout.addWidget(QLabel("Select Court:"))
            court_combo = QComboBox()
            court_combo.addItems([f"Court {c}" for c in empty_courts])
            court_combo.setStyleSheet("QComboBox { background-color: #3a3a3a; color: white; border: 1px solid #555; border-radius: 3px; padding: 5px; } QComboBox QAbstractItemView { background-color: #3a3a3a; color: white; }")
            court_combo.setData = lambda idx, role, val: None  # Make it selectable
            court_layout.addWidget(court_combo)
            layout.addLayout(court_layout)
            
            # Determine if singles or doubles
            is_doubles = self.session.config.session_type == 'doubles'
            num_per_team = 2 if is_doubles else 1
            
            # Create player combo function
            def create_player_combo(exclude_ids=None):
                """Create a combo box for player selection"""
                combo = QComboBox()
                combo.setStyleSheet("""
                    QComboBox { 
                        background-color: #3a3a3a; 
                        color: white; 
                        border: 1px solid #555;
                        border-radius: 3px;
                        padding: 5px;
                    }
                    QComboBox QAbstractItemView { 
                        background-color: #3a3a3a; 
                        color: white;
                    }
                """)
                
                combo.addItem("(Select a player)", None)
                
                exclude_set = exclude_ids or set()
                sorted_waiting = sorted(waiting_ids, key=lambda pid: get_player_name(self.session, pid))
                
                for player_id in sorted_waiting:
                    if player_id not in exclude_set:
                        player_name = get_player_name(self.session, player_id)
                        combo.addItem(player_name, player_id)
                
                return combo
            
            team_combos = {
                'team1': [],
                'team2': []
            }
            
            position_dict = {}
            
            def on_combo_changed():
                """Handle combo box change with auto-swap logic"""
                # Find which combo triggered the change
                changed_combo = None
                changed_team = None
                changed_idx = None
                
                for team_name in ['team1', 'team2']:
                    for idx, combo in enumerate(team_combos[team_name]):
                        # Check if any combo changed by comparing to position_dict
                        current = combo.currentData()
                        previous = position_dict.get((team_name, idx))
                        if current != previous and current is not None:
                            changed_combo = combo
                            changed_team = team_name
                            changed_idx = idx
                            break
                    if changed_combo:
                        break
                
                if not changed_combo:
                    return
                
                selected_player_id = changed_combo.currentData()
                previous_player = position_dict.get((changed_team, changed_idx))
                
                # Check for duplicate
                for team_name in ['team1', 'team2']:
                    for idx, other_combo in enumerate(team_combos[team_name]):
                        if other_combo is changed_combo:
                            continue
                        
                        if other_combo.currentData() == selected_player_id:
                            # Found duplicate, swap them
                            if previous_player:
                                for i in range(other_combo.count()):
                                    if other_combo.itemData(i) == previous_player:
                                        other_combo.blockSignals(True)
                                        other_combo.setCurrentIndex(i)
                                        other_combo.blockSignals(False)
                                        position_dict[(team_name, idx)] = previous_player
                                        break
                            break
                
                # Update position dict
                position_dict[(changed_team, changed_idx)] = selected_player_id
            
            # Team 1 section
            team1_label = QLabel("Team 1:")
            team1_label.setStyleSheet("QLabel { color: #ff9999; font-weight: bold; }")
            layout.addWidget(team1_label)
            
            team1_layout = QVBoxLayout()
            for i in range(num_per_team):
                position_label = QLabel(f"  Position {i + 1}:")
                position_label.setStyleSheet("QLabel { color: #ddd; }")
                team1_layout.addWidget(position_label)
                
                combo = create_player_combo()
                team_combos['team1'].append(combo)
                position_dict[('team1', i)] = None  # Initialize with None
                combo.currentIndexChanged.connect(on_combo_changed)
                
                team1_layout.addWidget(combo)
                team1_layout.addSpacing(5)
            
            layout.addLayout(team1_layout)
            layout.addSpacing(10)
            
            # Team 2 section
            team2_label = QLabel("Team 2:")
            team2_label.setStyleSheet("QLabel { color: #99ccff; font-weight: bold; }")
            layout.addWidget(team2_label)
            
            team2_layout = QVBoxLayout()
            for i in range(num_per_team):
                position_label = QLabel(f"  Position {i + 1}:")
                position_label.setStyleSheet("QLabel { color: #ddd; }")
                team2_layout.addWidget(position_label)
                
                combo = create_player_combo()
                team_combos['team2'].append(combo)
                position_dict[('team2', i)] = None  # Initialize with None
                combo.currentIndexChanged.connect(on_combo_changed)
                
                team2_layout.addWidget(combo)
                team2_layout.addSpacing(5)
            
            layout.addLayout(team2_layout)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            create_btn = QPushButton("Create Court")
            create_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; border-radius: 3px; }")
            button_layout.addWidget(create_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; border-radius: 3px; }")
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            def create_court():
                # Get selections
                court_text = court_combo.currentText()
                court_num = int(court_text.split()[-1])
                
                team1_ids = [combo.currentData() for combo in team_combos['team1'] if combo.currentData()]
                team2_ids = [combo.currentData() for combo in team_combos['team2'] if combo.currentData()]
                
                if len(team1_ids) != num_per_team or len(team2_ids) != num_per_team:
                    QMessageBox.warning(dialog, "Error", f"Each team must have exactly {num_per_team} player(s)")
                    return
                
                # Check for overlapping players
                if set(team1_ids) & set(team2_ids):
                    QMessageBox.warning(dialog, "Error", "A player cannot be on both teams")
                    return
                
                # Create match
                if create_manual_match(self.session, court_num, team1_ids, team2_ids):
                    self.refresh_display()
                    dialog.accept()
                else:
                    QMessageBox.critical(dialog, "Error", "Failed to create court")
            
            create_btn.clicked.connect(create_court)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
        
        except Exception as e:
            error_msg = f"Error making court:\n{str(e)}"
            print(f"MAKE COURT ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def edit_court_match(self, court_number: int, match_id: str):
        """Edit a court's match (swap players or change orientation)"""
        try:
            from python.queue_manager import get_waiting_players
            from python.session import update_match_teams
            
            # Find the match
            match = None
            for m in self.session.matches:
                if m.id == match_id:
                    match = m
                    break
            
            if not match or match.status not in ['waiting', 'in-progress']:
                QMessageBox.warning(self, "Invalid Match", "Cannot edit this match")
                return
            
            waiting_ids = get_waiting_players(self.session)
            all_available_ids = list(waiting_ids) + match.team1 + match.team2
            all_available_ids = list(set(all_available_ids))  # Remove duplicates
            all_available_ids.sort(key=lambda pid: get_player_name(self.session, pid))
            
            # Create edit dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Court {court_number}")
            dialog.setStyleSheet("QDialog { background-color: #2a2a2a; } QLabel { color: white; background-color: #2a2a2a; } QComboBox { background-color: #3a3a3a; color: white; border: 1px solid #555; border-radius: 3px; padding: 5px; }")
            dialog.setMinimumWidth(500)
            
            layout = QVBoxLayout()
            
            # Current teams display
            current_label = QLabel("Current Teams:")
            current_label.setStyleSheet("QLabel { color: white; font-weight: bold; }")
            layout.addWidget(current_label)
            
            current_text = f"Team 1: {', '.join([get_player_name(self.session, pid) for pid in match.team1])}\n"
            current_text += f"Team 2: {', '.join([get_player_name(self.session, pid) for pid in match.team2])}"
            current_info = QLabel(current_text)
            current_info.setStyleSheet("QLabel { color: #aaa; background-color: #1a1a1a; padding: 5px; border-radius: 3px; }")
            layout.addWidget(current_info)
            
            layout.addSpacing(10)
            
            # Determine if singles or doubles
            is_doubles = self.session.config.session_type == 'doubles'
            num_per_team = 2 if is_doubles else 1
            
            # Create dropdowns for each player position
            team_combos = {
                'team1': [],
                'team2': []
            }
            
            # Store player ID to combo box mapping for swap detection
            player_to_combos = {}
            
            def create_player_combo(current_player_id=None, exclude_player_ids=None):
                """Create a combo box for player selection"""
                combo = QComboBox()
                combo.setStyleSheet("""
                    QComboBox { 
                        background-color: #3a3a3a; 
                        color: white; 
                        border: 1px solid #555;
                        border-radius: 3px;
                        padding: 5px;
                    }
                    QComboBox QAbstractItemView { 
                        background-color: #3a3a3a; 
                        color: white;
                    }
                """)
                
                combo.addItem("(None)", None)
                
                exclude_ids = exclude_player_ids or set()
                for player_id in all_available_ids:
                    if player_id not in exclude_ids:
                        player_name = get_player_name(self.session, player_id)
                        combo.addItem(player_name, player_id)
                        # Track this combo for this player
                        if player_id not in player_to_combos:
                            player_to_combos[player_id] = []
                        player_to_combos[player_id].append(combo)
                
                # Set current value
                if current_player_id:
                    for i in range(combo.count()):
                        if combo.itemData(i) == current_player_id:
                            combo.setCurrentIndex(i)
                            break
                
                return combo
            
            def on_combo_changed(combo, position_dict):
                """Handle combo box change with auto-swap logic"""
                selected_player_id = combo.currentData()
                if not selected_player_id:
                    return
                
                # Find which position was changed
                changed_team = None
                changed_idx = None
                for team_name, combos in team_combos.items():
                    for idx, c in enumerate(combos):
                        if c is combo:
                            changed_team = team_name
                            changed_idx = idx
                            break
                    if changed_team:
                        break
                
                if not changed_team:
                    return
                
                # Get the previously selected player in this position
                previous_player = position_dict.get((changed_team, changed_idx))
                
                # Find if this player is already selected in another position
                duplicate_found = False
                for team_name, combos in team_combos.items():
                    for idx, other_combo in enumerate(combos):
                        if other_combo is combo:
                            continue
                        
                        other_player_id = other_combo.currentData()
                        if other_player_id == selected_player_id:
                            # Found duplicate: swap them
                            # The other combo should get what was in this position
                            if previous_player:
                                for i in range(other_combo.count()):
                                    if other_combo.itemData(i) == previous_player:
                                        other_combo.blockSignals(True)
                                        other_combo.setCurrentIndex(i)
                                        other_combo.blockSignals(False)
                                        # Update position dict for the swapped combo
                                        position_dict[(team_name, idx)] = previous_player
                                        duplicate_found = True
                                        break
                            if duplicate_found:
                                break
                    if duplicate_found:
                        break
                
                # Update position dict for the changed position
                position_dict[(changed_team, changed_idx)] = selected_player_id
            
            # Track current positions for swap logic
            position_dict = {}
            
            # Team 1 section
            team1_label = QLabel("Team 1:")
            team1_label.setStyleSheet("QLabel { color: #ff9999; font-weight: bold; }")
            layout.addWidget(team1_label)
            
            team1_layout = QVBoxLayout()
            for i in range(num_per_team):
                player_id = match.team1[i] if i < len(match.team1) else None
                position_label = QLabel(f"  Position {i + 1}:")
                position_label.setStyleSheet("QLabel { color: #ddd; }")
                team1_layout.addWidget(position_label)
                
                combo = create_player_combo(player_id)
                team_combos['team1'].append(combo)
                position_dict[('team1', i)] = player_id
                
                # Connect change signal with position tracking
                combo.currentIndexChanged.connect(lambda _, c=combo: on_combo_changed(c, position_dict))
                
                team1_layout.addWidget(combo)
                team1_layout.addSpacing(5)
            
            layout.addLayout(team1_layout)
            layout.addSpacing(10)
            
            # Team 2 section
            team2_label = QLabel("Team 2:")
            team2_label.setStyleSheet("QLabel { color: #99ccff; font-weight: bold; }")
            layout.addWidget(team2_label)
            
            team2_layout = QVBoxLayout()
            for i in range(num_per_team):
                player_id = match.team2[i] if i < len(match.team2) else None
                position_label = QLabel(f"  Position {i + 1}:")
                position_label.setStyleSheet("QLabel { color: #ddd; }")
                team2_layout.addWidget(position_label)
                
                combo = create_player_combo(player_id)
                team_combos['team2'].append(combo)
                position_dict[('team2', i)] = player_id
                
                # Connect change signal with position tracking
                combo.currentIndexChanged.connect(lambda _, c=combo: on_combo_changed(c, position_dict))
                
                team2_layout.addWidget(combo)
                team2_layout.addSpacing(5)
            
            layout.addLayout(team2_layout)
            layout.addSpacing(10)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            save_btn = QPushButton("Save Changes")
            save_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; border-radius: 3px; }")
            button_layout.addWidget(save_btn)
            
            swap_btn = QPushButton("Swap Teams")
            swap_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px; border-radius: 3px; }")
            button_layout.addWidget(swap_btn)
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; border-radius: 3px; }")
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            def save_changes():
                team1_ids = [combo.currentData() for combo in team_combos['team1'] if combo.currentData()]
                team2_ids = [combo.currentData() for combo in team_combos['team2'] if combo.currentData()]
                
                if len(team1_ids) != num_per_team or len(team2_ids) != num_per_team:
                    QMessageBox.warning(dialog, "Error", f"Each team must have exactly {num_per_team} player(s)")
                    return
                
                # Check for overlapping players
                if set(team1_ids) & set(team2_ids):
                    QMessageBox.warning(dialog, "Error", "A player cannot be on both teams")
                    return
                
                # Update match
                if update_match_teams(self.session, match_id, team1_ids, team2_ids):
                    self.refresh_display()
                    dialog.accept()
                else:
                    QMessageBox.critical(dialog, "Error", "Failed to update court")
            
            def swap_teams():
                # Swap the current selections
                team1_current = [combo.currentData() for combo in team_combos['team1']]
                team2_current = [combo.currentData() for combo in team_combos['team2']]
                
                # Swap by updating combo boxes
                for i, combo in enumerate(team_combos['team1']):
                    if i < len(team2_current):
                        player_id = team2_current[i]
                        combo.blockSignals(True)
                        for j in range(combo.count()):
                            if combo.itemData(j) == player_id:
                                combo.setCurrentIndex(j)
                                break
                        combo.blockSignals(False)
                
                for i, combo in enumerate(team_combos['team2']):
                    if i < len(team1_current):
                        player_id = team1_current[i]
                        combo.blockSignals(True)
                        for j in range(combo.count()):
                            if combo.itemData(j) == player_id:
                                combo.setCurrentIndex(j)
                                break
                        combo.blockSignals(False)
                
                # Update position dict
                for i in range(num_per_team):
                    position_dict[('team1', i)] = team_combos['team1'][i].currentData()
                    position_dict[('team2', i)] = team_combos['team2'][i].currentData()
            
            save_btn.clicked.connect(save_changes)
            swap_btn.clicked.connect(swap_teams)
            cancel_btn.clicked.connect(dialog.reject)
            
            dialog.exec()
        
        except Exception as e:
            error_msg = f"Error editing court:\n{str(e)}"
            print(f"EDIT COURT ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def end_session(self):
        """End the session"""
        reply = QMessageBox.question(
            self, "Confirm",
            "End session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.update_timer.stop()
            self.close()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.session: Optional[Session] = None
        self.init_ui()
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("🎾 Pickleball Session Manager")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Buttons
        button_layout = QVBoxLayout()
        
        new_session_btn = QPushButton("New Session")
        new_session_btn.setMinimumHeight(50)
        new_session_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        new_session_btn.clicked.connect(self.new_session)
        button_layout.addWidget(new_session_btn)
        
        # Check if we have a saved session
        from python.session_persistence import has_saved_session, load_player_history
        
        if has_saved_session():
            resume_btn = QPushButton("Resume Last Session")
            resume_btn.setMinimumHeight(50)
            resume_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            resume_btn.clicked.connect(self.resume_last_session)
            button_layout.addWidget(resume_btn)
        
        # Check if we have player history
        player_history = load_player_history()
        if player_history:
            previous_players_btn = QPushButton("New Session with Previous Players")
            previous_players_btn.setMinimumHeight(50)
            previous_players_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            previous_players_btn.clicked.connect(self.new_session_with_previous_players)
            button_layout.addWidget(previous_players_btn)
        
        layout.addLayout(button_layout)
        
        # Info
        info_label = QLabel("Select an option to begin")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        central_widget.setLayout(layout)
        
        # Apply dark theme
        dark_stylesheet = """
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; }
            QLabel { color: white; background-color: #1e1e1e; }
            QPushButton { 
                color: white; 
                background-color: #0d47a1;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton:pressed { background-color: #0d47a1; }
        """
        self.setStyleSheet(dark_stylesheet)
        
        self.setWindowTitle("Pickleball Session Manager")
        self.resize(600, 400)
    
    def new_session(self):
        """Create a new session"""
        try:
            setup = SetupDialog(self)
            if setup.exec() == QDialog.DialogCode.Accepted:
                self.session = setup.session
                try:
                    # Pass self as parent and keep reference
                    self.session_window = SessionWindow(self.session, parent_window=self)
                    self.session_window.show()
                    # Hide main window but keep it alive in memory
                    self.hide()
                except Exception as e:
                    error_msg = f"Error creating session window:\n{str(e)}\n\nType: {type(e).__name__}"
                    print(f"SESSION WINDOW ERROR: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(self, "Session Window Error", error_msg)
        except Exception as e:
            error_msg = f"Error in new_session:\n{str(e)}"
            print(f"NEW SESSION ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def load_session(self):
        """Load a session from file"""
        QMessageBox.information(self, "Info", "Session loading not yet implemented")
    
    def resume_last_session(self):
        """Resume the last saved session"""
        try:
            from python.session_persistence import load_last_session
            
            session = load_last_session()
            if not session:
                QMessageBox.warning(self, "Error", "Could not load last session")
                return
            
            self.session = session
            try:
                self.session_window = SessionWindow(self.session, parent_window=self)
                self.session_window.show()
                self.hide()
            except Exception as e:
                error_msg = f"Error creating session window:\n{str(e)}"
                print(f"SESSION WINDOW ERROR: {error_msg}")
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Session Window Error", error_msg)
        except Exception as e:
            error_msg = f"Error resuming session:\n{str(e)}"
            print(f"RESUME SESSION ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)
    
    def new_session_with_previous_players(self):
        """Create a new session with players from previous sessions"""
        try:
            from python.session_persistence import load_player_history
            
            player_history = load_player_history()
            
            if not player_history:
                QMessageBox.warning(self, "Error", "No player history available")
                return
            
            setup = SetupDialog(self, previous_players=player_history)
            if setup.exec() == QDialog.DialogCode.Accepted:
                self.session = setup.session
                try:
                    self.session_window = SessionWindow(self.session, parent_window=self)
                    self.session_window.show()
                    self.hide()
                except Exception as e:
                    error_msg = f"Error creating session window:\n{str(e)}"
                    print(f"SESSION WINDOW ERROR: {error_msg}")
                    import traceback
                    traceback.print_exc()
                    QMessageBox.critical(self, "Session Window Error", error_msg)
        except Exception as e:
            error_msg = f"Error in new_session_with_previous_players:\n{str(e)}"
            print(f"NEW SESSION ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
