"""
Playbook system for AIRD preprocessing.

Provides playbook routing and loading functionality.
"""

from .router import route_playbook, list_playbooks, resolve_playbook_file, refresh_index
from .loader import load_playbook_yaml, get_playbook_dir

__all__ = [
    "route_playbook",
    "list_playbooks",
    "resolve_playbook_file",
    "refresh_index",
    "load_playbook_yaml",
    "get_playbook_dir",
]



