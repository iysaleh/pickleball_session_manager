"""
PyQt6 GUI for Pickleball Session Manager
"""

import sys
import json
import os
from typing import Optional, List, Dict
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QSpinBox, QComboBox, QLabel, QListWidget,
    QListWidgetItem, QDialog, QTabWidget, QTableWidget, QTableWidgetItem,
    QMessageBox, QInputDialog, QSpinBox, QGroupBox, QCheckBox, QFrame, QScrollArea,
    QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QRect, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QBrush, QPen

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
        
        input_layout.addWidget(self.player_input)
        input_layout.addWidget(add_btn)
        layout.addLayout(input_layout)
        
        # Player list
        self.player_list = QListWidget()
        layout.addWidget(self.player_list)
        
        self.setLayout(layout)
    
    def add_player(self):
        """Add a player to the list"""
        name = self.player_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a player name")
            return
        
        player = Player(id=f"player_{len(self.players)}_{datetime.now().timestamp()}", name=name)
        self.players.append(player)
        
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, player.id)
        self.player_list.addItem(item)
        
        self.player_input.clear()
        self.player_input.setFocus()
    
    def remove_selected_player(self):
        """Remove selected player from list"""
        current_item = self.player_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a player to remove")
            return
        
        player_id = current_item.data(Qt.ItemDataRole.UserRole)
        self.players = [p for p in self.players if p.id != player_id]
        self.player_list.takeItem(self.player_list.row(current_item))
    
    def get_players(self) -> List[Player]:
        """Get current player list"""
        return self.players.copy()
    
    def clear(self):
        """Clear all players"""
        self.players = []
        self.player_list.clear()


class SetupDialog(QDialog):
    """Dialog for session setup"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session: Optional[Session] = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Game Mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Game Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Round Robin", "King of the Court"])
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
        
        # Players
        layout.addWidget(QLabel("Players:"))
        self.player_widget = PlayerListWidget()
        layout.addWidget(self.player_widget)
        
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
        self.setWindowTitle("Session Setup")
        self.resize(600, 500)
    
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
    
    def start_session(self):
        """Create and start a session"""
        try:
            players = self.player_widget.get_players()
            
            if len(players) < 2:
                QMessageBox.warning(self, "Error", "At least 2 players are required")
                return
            
            mode_text = self.mode_combo.currentText()
            mode: GameMode = 'round-robin' if mode_text == "Round Robin" else 'king-of-court'
            
            type_text = self.type_combo.currentText()
            session_type: SessionType = 'doubles' if type_text == "Doubles" else 'singles'
            
            config = SessionConfig(
                mode=mode,
                session_type=session_type,
                players=players,
                courts=self.courts_spin.value(),
                banned_pairs=[],
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
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Court header
        header = QHBoxLayout()
        self.title = QLabel(f"Court {self.court_number}")
        self.title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.title.setStyleSheet("QLabel { color: black; }")
        header.addWidget(self.title)
        header.addStretch()
        layout.addLayout(header)
        
        # Court visual area
        self.court_area = QFrame()
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
        self.current_match = match
        
        if not match:
            self.team1_label.setText("Waiting for\nplayers...")
            self.team2_label.setText("Waiting for\nplayers...")
            self.team1_score.setValue(0)
            self.team2_score.setValue(0)
            self.court_area.setStyleSheet("QFrame { background-color: #e0e0e0; border: 2px dashed #999; border-radius: 5px; }")
            return
        
        self.court_area.setStyleSheet("QFrame { background-color: #c4d76d; border: 2px solid #333; border-radius: 5px; }")
        
        # Get player names
        team1_names = [get_player_name(self.session, pid) for pid in match.team1]
        team2_names = [get_player_name(self.session, pid) for pid in match.team2]
        
        self.team1_label.setText("\n".join(team1_names))
        self.team2_label.setText("\n".join(team2_names))
        
        if match.score:
            self.team1_score.setValue(match.score.get('team1_score', 0))
            self.team2_score.setValue(match.score.get('team2_score', 0))
    
    def complete_match_clicked(self):
        """Handle complete match button"""
        if not self.current_match:
            QMessageBox.warning(self, "Error", "No match to complete")
            return
        
        team1_score = self.team1_score.value()
        team2_score = self.team2_score.value()
        
        if team1_score == team2_score:
            QMessageBox.warning(self, "Error", "Scores must be different (winner must have higher score)")
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
            if complete_match(self.session, self.current_match.id, team1_score, team2_score):
                self.team1_score.setValue(0)
                self.team2_score.setValue(0)
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
                pass
            else:
                QMessageBox.warning(self, "Error", "Failed to forfeit match")


class SessionWindow(QMainWindow):
    """Main window for active session"""
    
    def __init__(self, session: Session, parent_window=None):
        super().__init__()
        try:
            self.session = session
            self.parent_window = parent_window
            self.court_widgets: Dict[int, CourtDisplayWidget] = {}
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
        self.title.setStyleSheet("QLabel { color: white; background-color: black; padding: 10px; border-radius: 3px; }")
        main_layout.addWidget(self.title)
        
        # Main content area (courts + waiting list)
        content_layout = QHBoxLayout()
        
        # Courts section
        courts_section = QVBoxLayout()
        courts_label = QLabel("Active Courts")
        courts_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        courts_label.setStyleSheet("QLabel { color: white; background-color: black; padding: 8px; border-radius: 3px; }")
        courts_section.addWidget(courts_label)
        
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
        
        # Waiting list section
        waiting_section = QVBoxLayout()
        waiting_label = QLabel("⏳ Waitlist")
        waiting_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        waiting_label.setStyleSheet("QLabel { color: white; background-color: black; padding: 8px; border-radius: 3px; }")
        waiting_section.addWidget(waiting_label)
        
        self.waiting_list = QListWidget()
        self.waiting_list.setMinimumWidth(200)
        waiting_section.addWidget(self.waiting_list, 1)
        
        self.waiting_count = QLabel("0 players waiting")
        self.waiting_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.waiting_count.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
        waiting_section.addWidget(self.waiting_count)
        
        content_layout.addLayout(waiting_section, 1)
        main_layout.addLayout(content_layout, 1)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        end_btn = QPushButton("End Session")
        end_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        end_btn.clicked.connect(self.end_session)
        button_layout.addWidget(end_btn)
        
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        central_widget.setLayout(main_layout)
        self.setWindowTitle("Pickleball Session Manager")
        self.resize(1400, 800)
    
    def update_title(self, summary: Dict):
        """Update title with session info"""
        info = f"{self.session.config.mode.title()} - {self.session.config.session_type.title()} | "
        info += f"Courts: {summary['active_matches']}/{summary['total_courts']} | "
        info += f"Queued: {summary['queued_matches']} | "
        info += f"Completed: {summary['completed_matches']}"
        
        self.title.setText(info)
    
    def refresh_display(self):
        """Refresh court displays"""
        try:
            from python.queue_manager import (
                populate_empty_courts, get_match_for_court, get_session_summary,
                get_waiting_players
            )
            populate_empty_courts(self.session)
            
            # Update court displays
            for court_num in range(1, self.session.config.courts + 1):
                widget = self.court_widgets.get(court_num)
                if widget is None:
                    continue
                match = get_match_for_court(self.session, court_num)
                widget.set_match(match)
            
            # Update waiting players list
            waiting_ids = get_waiting_players(self.session)
            self.waiting_list.clear()
            for player_id in waiting_ids:
                player_name = get_player_name(self.session, player_id)
                self.waiting_list.addItem(player_name)
            
            self.waiting_count.setText(f"{len(waiting_ids)} player{'s' if len(waiting_ids) != 1 else ''} waiting")
            
            # Update summary info
            summary = get_session_summary(self.session)
            self.update_title(summary)
        except Exception as e:
            error_msg = f"Error in refresh_display:\n{str(e)}"
            print(f"REFRESH ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
    
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
        button_layout = QHBoxLayout()
        
        new_session_btn = QPushButton("New Session")
        new_session_btn.clicked.connect(self.new_session)
        button_layout.addWidget(new_session_btn)
        
        load_session_btn = QPushButton("Load Session")
        load_session_btn.clicked.connect(self.load_session)
        button_layout.addWidget(load_session_btn)
        
        layout.addLayout(button_layout)
        
        # Info
        info_label = QLabel("Select 'New Session' to start a new pickleball session")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        layout.addStretch()
        
        central_widget.setLayout(layout)
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


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
