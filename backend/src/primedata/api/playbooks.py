"""
Playbooks API router.

Provides endpoints for listing and retrieving playbook configurations.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from primedata.ingestion_pipeline.aird_stages.playbooks import list_playbooks, load_playbook_yaml, refresh_index

router = APIRouter(prefix="/api/v1/playbooks", tags=["Playbooks"])


class PlaybookInfo(BaseModel):
    """Playbook information."""
    id: str
    description: str
    path: str


class PlaybookResponse(BaseModel):
    """Full playbook configuration response."""
    id: str
    description: str
    config: Dict[str, Any]


@router.get("/", response_model=List[PlaybookInfo])
async def list_available_playbooks():
    """
    List all available playbooks.
    
    Returns all playbooks found in the configured playbook directory,
    including TECH, SCANNED, REGULATORY, and any other playbooks.
    """
    try:
        # Refresh the playbook index to ensure we have the latest playbooks
        refresh_index()
        playbook_map = list_playbooks()
        
        if not playbook_map:
            logger.warning("No playbooks found in configured directory")
            return []
        
        playbooks = []
        
        # Sort by playbook ID (case-insensitive) for consistent ordering
        sorted_items = sorted(playbook_map.items(), key=lambda x: x[0].lower())
        
        for playbook_id, path in sorted_items:
            try:
                # Load playbook to get description and actual ID from YAML
                config = load_playbook_yaml(playbook_id)
                # Use the ID from the YAML file, or fallback to uppercase version of the key
                playbook_id_from_yaml = config.get("id", playbook_id.upper())
                playbooks.append(PlaybookInfo(
                    id=playbook_id_from_yaml,
                    description=config.get("description", "No description"),
                    path=str(path),
                ))
            except Exception as e:
                logger.warning(f"Failed to load playbook {playbook_id}: {e}")
                # Still include it with minimal info using the filename as ID
                playbooks.append(PlaybookInfo(
                    id=playbook_id.upper(),
                    description="Playbook available but failed to load",
                    path=str(path),
                ))
        
        return playbooks
    except Exception as e:
        logger.error(f"Failed to list playbooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list playbooks"
        )


@router.get("/{playbook_id}", response_model=PlaybookResponse)
async def get_playbook(playbook_id: str):
    """
    Get playbook configuration by ID.
    """
    try:
        config = load_playbook_yaml(playbook_id)
        return PlaybookResponse(
            id=config.get("id", playbook_id.upper()),
            description=config.get("description", "No description"),
            config=config,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook '{playbook_id}' not found"
        )
    except Exception as e:
        logger.error(f"Failed to load playbook {playbook_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load playbook: {str(e)}"
        )



