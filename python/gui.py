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
        self.player_count_label.setStyleSheet("font-weight: bold; font-size: 12px;")
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
        self.default_title = f"Court {self.court_number}"
        self.custom_title = None
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
        
        # Right sidebar section (waiting list + queue)
        right_section = QVBoxLayout()
        
        # Waiting list section
        waiting_label = QLabel("⏳ Waitlist")
        waiting_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        waiting_label.setStyleSheet("QLabel { color: white; background-color: black; padding: 8px; border-radius: 3px; }")
        right_section.addWidget(waiting_label)
        
        self.waiting_list = QListWidget()
        self.waiting_list.setMinimumWidth(250)
        self.waiting_list.setMaximumHeight(150)
        right_section.addWidget(self.waiting_list)
        
        self.waiting_count = QLabel("0 players waiting")
        self.waiting_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.waiting_count.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
        right_section.addWidget(self.waiting_count)
        
        # Queue section
        queue_label = QLabel("📋 Match Queue")
        queue_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        queue_label.setStyleSheet("QLabel { color: white; background-color: black; padding: 8px; border-radius: 3px; }")
        right_section.addWidget(queue_label)
        
        self.queue_list = QListWidget()
        self.queue_list.setMinimumWidth(250)
        right_section.addWidget(self.queue_list, 1)
        
        self.queue_count = QLabel("0 matches queued")
        self.queue_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.queue_count.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
        right_section.addWidget(self.queue_count)
        
        # History section
        history_label = QLabel("📜 Match History")
        history_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        history_label.setStyleSheet("QLabel { color: white; background-color: black; padding: 8px; border-radius: 3px; }")
        right_section.addWidget(history_label)
        
        self.history_list = QListWidget()
        self.history_list.setMinimumWidth(250)
        self.history_list.itemDoubleClicked.connect(self.edit_match_history)
        right_section.addWidget(self.history_list, 1)
        
        self.history_count = QLabel("0 matches completed")
        self.history_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_count.setStyleSheet("QLabel { color: #666; font-weight: bold; }")
        right_section.addWidget(self.history_count)
        
        content_layout.addLayout(right_section, 1)
        main_layout.addLayout(content_layout, 1)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        players_btn = QPushButton("👥 Add/Remove Players")
        players_btn.setStyleSheet("QPushButton { background-color: #9C27B0; color: white; font-weight: bold; padding: 8px 16px; border-radius: 3px; }")
        players_btn.clicked.connect(self.manage_players)
        button_layout.addWidget(players_btn)
        
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
                get_waiting_players, get_queued_matches_for_display
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
            
            # Player statistics
            export_lines.append("PLAYER STATISTICS:")
            export_lines.append("-" * 70)
            export_lines.append(f"{'Player':<25} {'W-L':<10} {'Games Played':<15} {'Win %':<10}")
            export_lines.append("-" * 70)
            
            for player in self.session.config.players:
                if player.id in self.session.active_players:
                    stats = self.session.player_stats[player.id]
                    record = f"{stats.wins}-{stats.losses}"
                    win_pct = (stats.wins / stats.games_played * 100) if stats.games_played > 0 else 0
                    win_pct_str = f"{win_pct:.1f}%" if stats.games_played > 0 else "N/A"
                    
                    export_lines.append(
                        f"{player.name:<25} {record:<10} {stats.games_played:<15} {win_pct_str:<10}"
                    )
            
            export_lines.append("")
            
            # Match History (most recent first)
            completed_matches = [m for m in self.session.matches if m.status == 'completed']
            if completed_matches:
                export_lines.append("MATCH HISTORY:")
                export_lines.append("-" * 70)
                
                for match in reversed(completed_matches):
                    team1_names = [get_player_name(self.session, pid) for pid in match.team1]
                    team2_names = [get_player_name(self.session, pid) for pid in match.team2]
                    
                    if match.score:
                        team1_score = match.score.get('team1_score', 0)
                        team2_score = match.score.get('team2_score', 0)
                        
                        # Format: Higher score on top
                        if team1_score >= team2_score:
                            export_lines.append(f"{', '.join(team1_names)}: {team1_score} beat {', '.join(team2_names)}: {team2_score}")
                        else:
                            export_lines.append(f"{', '.join(team2_names)}: {team2_score} beat {', '.join(team1_names)}: {team1_score}")
                
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
                        
                        # Remove from active players and config
                        self.session.active_players.discard(player_id)
                        self.session.config.players = [p for p in self.session.config.players if p.id != player_id]
                    
                    # Add players
                    for player_name in players_to_add:
                        new_player = Player(id=f"player_{datetime.now().timestamp()}", name=player_name)
                        self.session.config.players.append(new_player)
                        self.session.active_players.add(new_player.id)
                        
                        # Initialize stats - set games_waited to max + 1
                        max_wait = max([self.session.player_stats[p.id].games_waited for p in self.session.config.players if p.id != new_player.id], default=0)
                        
                        from python.types import PlayerStats
                        self.session.player_stats[new_player.id] = PlayerStats(
                            player_id=new_player.id,
                            wins=0,
                            losses=0,
                            games_played=0,
                            games_waited=max_wait + 1,
                            partners_played=set(),
                            opponents_played=set(),
                            total_points_for=0,
                            total_points_against=0
                        )
                    
                    # Regenerate match queue once at the end
                    if players_to_add or players_to_remove:
                        from python.roundrobin import generate_round_robin_queue
                        from python.queue_manager import populate_empty_courts, get_waiting_players
                        
                        self.session.match_queue = generate_round_robin_queue(
                            [p for p in self.session.config.players if p.id in self.session.active_players],
                            self.session.config.session_type,
                            self.session.config.banned_pairs,
                            player_stats=self.session.player_stats,
                            active_matches=self.session.matches
                        )
                        
                        # Prioritize matches with waiting players at the front of the queue
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
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 5px; }")
            button_layout.addWidget(cancel_btn)
            
            layout.addLayout(button_layout)
            
            dialog.setLayout(layout)
            
            def save_changes():
                t1_score = team1_spin.value()
                t2_score = team2_spin.value()
                
                if t1_score == t2_score:
                    QMessageBox.warning(dialog, "Error", "Scores must be different")
                    return
                
                match.score = {'team1_score': t1_score, 'team2_score': t2_score}
                dialog.accept()
                self.refresh_display()
            
            save_btn.clicked.connect(save_changes)
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
                    "Player", "ELO", "W-L", "Games", "Waited", "Win %", 
                    "Partners", "Opponents", "Avg Pt Diff", "Pts For", "Pts Against"
                ]
                num_columns = 11
            else:
                column_labels = [
                    "Player", "W-L", "Games", "Waited", "Win %", 
                    "Partners", "Opponents", "Avg Pt Diff", "Pts For", "Pts Against"
                ]
                num_columns = 10
            
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
                
                player_data.append((
                    player.name,
                    elo,
                    stats.wins,
                    stats.losses,
                    stats.games_played,
                    stats.games_waited,
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
                player_data.sort(key=lambda x: (-x[2], x[3], -x[9]))
            
            # Populate table
            for row, data in enumerate(player_data):
                table.insertRow(row)
                
                if is_competitive_variety:
                    items = [
                        data[0],  # name
                        f"{data[1]:.0f}",  # ELO
                        f"{data[2]}-{data[3]}",  # W-L
                        str(data[4]),  # games
                        str(data[5]),  # waited
                        f"{data[6]:.1f}%",  # win %
                        str(data[7]),  # partners
                        str(data[8]),  # opponents
                        f"{data[9]:.1f}",  # avg pt diff
                        str(data[10]),  # pts for
                        str(data[11])  # pts against
                    ]
                else:
                    items = [
                        data[0],  # name
                        f"{data[2]}-{data[3]}",  # W-L
                        str(data[4]),  # games
                        str(data[5]),  # waited
                        f"{data[6]:.1f}%",  # win %
                        str(data[7]),  # partners
                        str(data[8]),  # opponents
                        f"{data[9]:.1f}",  # avg pt diff
                        str(data[10]),  # pts for
                        str(data[11])  # pts against
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
