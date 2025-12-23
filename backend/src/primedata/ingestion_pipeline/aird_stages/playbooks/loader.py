"""
Playbook YAML loader for AIRD preprocessing.

Loads and parses playbook YAML files from configured directory.
"""

from pathlib import Path
from typing import Dict, Optional
import yaml
from loguru import logger

from primedata.ingestion_pipeline.aird_stages.config import get_aird_config, get_playbook_path


def get_playbook_dir() -> Optional[Path]:
    """Get the playbook directory path.
    
    Returns:
        Path to playbook directory, or None if not configured
    """
    config = get_aird_config()
    if not config.playbook_dir:
        return None
    return Path(config.playbook_dir)


def load_playbook_yaml(playbook_id: Optional[str]) -> Dict:
    """
    Load and parse a playbook YAML by ID (case-insensitive).
    
    Args:
        playbook_id: e.g., 'TECH', 'tech', 'ScAnNeD'; None allowed (uses default)
        
    Returns:
        dict from YAML content
        
    Raises:
        FileNotFoundError: if playbook cannot be found
    """
    playbook_file = get_playbook_path(playbook_id)
    if not playbook_file:
        # Fallback: try to use default from config
        config = get_aird_config()
        if config.default_playbook:
            playbook_file = get_playbook_path(config.default_playbook)
        
        if not playbook_file:
            raise FileNotFoundError(f"Playbook '{playbook_id}' not found and no default available")
    
    try:
        with open(playbook_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load playbook from {playbook_file}: {e}")
        raise




