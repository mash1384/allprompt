#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Settings Dialog Module
UI components for managing application settings.
"""

import logging
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QGroupBox, QFormLayout, QStyle
)
from PySide6.QtCore import Qt, Signal

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Application Settings Dialog"""
    
    # Settings change signal
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None, current_settings=None):
        """
        Initialize settings dialog
        
        Args:
            parent: Parent widget
            current_settings: Current settings dictionary
        """
        super().__init__(parent)
        
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        
        # Default settings
        self.default_settings = {
            "show_hidden_files": False,
            "follow_symlinks": False,
            "apply_gitignore_rules": True,
            "copy_file_tree_only": False,
        }
        
        # Current settings
        self.current_settings = current_settings or self.default_settings.copy()
        
        # Initialize UI
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # ===== File Scanning Settings Group =====
        scan_group = QGroupBox("File Scanning")
        scan_group.setObjectName("settingsGroup")
        scan_layout = QVBoxLayout(scan_group)
        scan_layout.setContentsMargins(12, 18, 12, 12)
        scan_layout.setSpacing(8)
        
        # Show hidden files checkbox
        self.show_hidden_files_cb = QCheckBox("Show hidden files/folders")
        self.show_hidden_files_cb.setChecked(self.current_settings.get("show_hidden_files", False))
        self.show_hidden_files_cb.setObjectName("settingsCheckbox")
        scan_layout.addWidget(self.show_hidden_files_cb)
        
        # Follow symlinks checkbox
        self.follow_symlinks_cb = QCheckBox("Follow symbolic links (may be unsafe)")
        self.follow_symlinks_cb.setChecked(self.current_settings.get("follow_symlinks", False))
        self.follow_symlinks_cb.setObjectName("settingsCheckbox")
        scan_layout.addWidget(self.follow_symlinks_cb)
        
        # Apply gitignore rules checkbox
        self.apply_gitignore_rules_cb = QCheckBox("Apply .gitignore rules")
        self.apply_gitignore_rules_cb.setChecked(self.current_settings.get("apply_gitignore_rules", True))
        self.apply_gitignore_rules_cb.setToolTip("Filter files according to rules defined in .gitignore")
        self.apply_gitignore_rules_cb.setObjectName("settingsCheckbox")
        scan_layout.addWidget(self.apply_gitignore_rules_cb)
        
        layout.addWidget(scan_group)
        
        # ===== Output Settings Group =====
        output_group = QGroupBox("Output Settings")
        output_group.setObjectName("settingsGroup")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 18, 12, 12)
        output_layout.setSpacing(8)
        
        # Copy file tree only checkbox
        self.copy_file_tree_only_cb = QCheckBox("Copy file tree only (exclude file contents)")
        self.copy_file_tree_only_cb.setChecked(self.current_settings.get("copy_file_tree_only", False))
        self.copy_file_tree_only_cb.setToolTip("When checked, only file structure will be copied without contents")
        self.copy_file_tree_only_cb.setObjectName("settingsCheckbox")
        output_layout.addWidget(self.copy_file_tree_only_cb)
        
        layout.addWidget(output_group)
        
        # ===== Button Area =====
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Default button
        reset_button = QPushButton("Reset to Default")
        reset_button.setObjectName("resetButton")
        reset_button.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        # Add stretch (space between buttons)
        button_layout.addStretch()
        
        # Cancel/Save buttons
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        save_button = QPushButton("Save")
        save_button.setObjectName("saveButton")
        save_button.clicked.connect(self._save_settings)
        save_button.setDefault(True)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
    
    def _reset_to_defaults(self):
        """Reset settings to default values"""
        # Checkboxes
        self.show_hidden_files_cb.setChecked(self.default_settings["show_hidden_files"])
        self.follow_symlinks_cb.setChecked(self.default_settings["follow_symlinks"])
        self.apply_gitignore_rules_cb.setChecked(self.default_settings["apply_gitignore_rules"])
        self.copy_file_tree_only_cb.setChecked(self.default_settings["copy_file_tree_only"])
    
    def _save_settings(self):
        """Save settings and emit change signal"""
        settings = {
            "show_hidden_files": self.show_hidden_files_cb.isChecked(),
            "follow_symlinks": self.follow_symlinks_cb.isChecked(),
            "apply_gitignore_rules": self.apply_gitignore_rules_cb.isChecked(),
            "copy_file_tree_only": self.copy_file_tree_only_cb.isChecked(),
        }
        
        # Check if settings have changed
        if settings != self.current_settings:
            logger.info("Settings changed: %s", settings)
            self.current_settings = settings
            self.settings_changed.emit(settings)
        
        self.accept()
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Return current settings
        
        Returns:
            Current settings dictionary
        """
        return self.current_settings 