"""
Configuration resolver with precedence-based resolution.

Implements resolve_effective_config with the following precedence order:
1. run_conf overrides (highest priority)
2. force_product_chunking_config
3. product manual settings
4. playbook defaults
5. global defaults (lowest priority)
"""

from typing import Any, Dict, Optional

from loguru import logger

from primedata.analysis.content_analyzer import ContentType, content_analyzer
from primedata.config.models import (
    ChunkingConfig,
    EffectiveConfig,
    PlaybookConfig,
    ResolutionTrace,
)
from primedata.ingestion_pipeline.aird_stages.playbooks.loader import load_playbook_yaml

# Global defaults
DEFAULT_MANUAL_SETTINGS: Dict[str, Any] = {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "min_chunk_size": 100,
    "max_chunk_size": 2000,
    "chunking_strategy": "fixed_size",
}

DEFAULT_AUTO_SETTINGS: Dict[str, Any] = {
    "content_type": "general",
    "model_optimized": True,
    "confidence_threshold": 0.7,
}


def _ensure_dict(value: Any) -> Dict[str, Any]:
    """Ensure value is a dictionary."""
    return value if isinstance(value, dict) else {}


def _get_playbook_chunking_defaults(playbook_config: Optional[PlaybookConfig]) -> Dict[str, Any]:
    """Extract chunking defaults from playbook configuration."""
    if not playbook_config or not playbook_config.chunking:
        return {}

    chunking = playbook_config.chunking
    defaults = {}

    # Map playbook chunking config to our format
    if "max_tokens" in chunking:
        defaults["chunk_size"] = chunking["max_tokens"]
    if "hard_overlap_chars" in chunking:
        defaults["chunk_overlap"] = chunking["hard_overlap_chars"]
    if "strategy" in chunking:
        strategy = chunking["strategy"]
        # Map playbook strategies to our enum values
        if strategy == "sentence":
            defaults["chunking_strategy"] = "semantic"
        elif strategy == "fixed_size":
            defaults["chunking_strategy"] = "fixed_size"
        else:
            defaults["chunking_strategy"] = "fixed_size"  # Default fallback

    return defaults


def _get_content_type_defaults(content_type: Optional[str]) -> Dict[str, Any]:
    """Get defaults from content analyzer for a given content type."""
    if not content_type:
        return {}

    try:
        content_type_enum = ContentType(content_type)
        default_config = content_analyzer.optimal_configs.get(content_type_enum)
        if default_config:
            return {
                "chunk_size": default_config["chunk_size"],
                "chunk_overlap": default_config["chunk_overlap"],
                "min_chunk_size": default_config["min_chunk_size"],
                "max_chunk_size": default_config["max_chunk_size"],
                "chunking_strategy": default_config["strategy"].value,
            }
    except (ValueError, KeyError):
        pass

    return {}


def resolve_effective_config(
    run_conf: Optional[Dict[str, Any]],
    product_row: Any,
    detected_playbook: Optional[str] = None,
) -> EffectiveConfig:
    """
    Resolve effective configuration with precedence-based resolution.

    Precedence order (highest to lowest):
    1. run_conf overrides
    2. force_product_chunking_config
    3. product manual settings
    4. playbook defaults
    5. global defaults

    Args:
        run_conf: Runtime configuration overrides (from DAG run config)
        product_row: Product database row/model instance
        detected_playbook: Detected playbook ID (optional)

    Returns:
        EffectiveConfig with resolved configuration and ResolutionTrace
    """
    run_conf = run_conf or {}
    trace = ResolutionTrace(
        chunk_size="",
        chunk_overlap="",
        min_chunk_size="",
        max_chunk_size="",
        chunking_strategy="",
        content_type="",
        playbook_id="",
    )

    # Extract product configuration
    product_chunking = _ensure_dict(getattr(product_row, "chunking_config", None))
    product_playbook_id = getattr(product_row, "playbook_id", None)
    product_manual_settings = _ensure_dict(product_chunking.get("manual_settings"))
    product_auto_settings = _ensure_dict(product_chunking.get("auto_settings"))

    # Determine playbook ID (precedence: run_conf > detected > product)
    playbook_id = (
        run_conf.get("playbook_id")
        or detected_playbook
        or product_playbook_id
        or "TECH"  # Global default
    )
    trace.playbook_id = (
        "run_conf"
        if run_conf.get("playbook_id")
        else ("detected_playbook" if detected_playbook else ("product" if product_playbook_id else "global_default"))
    )

    # Load playbook configuration
    playbook_config: Optional[PlaybookConfig] = None
    try:
        workspace_id = getattr(product_row, "workspace_id", None)
        db_session = getattr(product_row, "__session__", None)  # Try to get session if available
        playbook_dict = load_playbook_yaml(playbook_id, str(workspace_id) if workspace_id else None, db_session)
        if playbook_dict:
            playbook_config = PlaybookConfig(**playbook_dict)
    except Exception as e:
        logger.warning(f"Failed to load playbook {playbook_id}: {e}")

    # Get playbook chunking defaults
    playbook_defaults = _get_playbook_chunking_defaults(playbook_config)

    # Get content type defaults
    content_type = product_auto_settings.get("content_type") or playbook_defaults.get("content_type") or "general"
    content_type_defaults = _get_content_type_defaults(content_type)
    trace.content_type = (
        "product_auto_settings"
        if product_auto_settings.get("content_type")
        else ("playbook" if playbook_defaults.get("content_type") else "global_default")
    )

    # Start with global defaults
    resolved = {
        "chunk_size": DEFAULT_MANUAL_SETTINGS["chunk_size"],
        "chunk_overlap": DEFAULT_MANUAL_SETTINGS["chunk_overlap"],
        "min_chunk_size": DEFAULT_MANUAL_SETTINGS["min_chunk_size"],
        "max_chunk_size": DEFAULT_MANUAL_SETTINGS["max_chunk_size"],
        "chunking_strategy": DEFAULT_MANUAL_SETTINGS["chunking_strategy"],
        "content_type": content_type,
    }

    # Apply precedence (lowest to highest, so later overrides earlier)

    # 5. Global defaults (already set above)
    trace.chunk_size = "global_default"
    trace.chunk_overlap = "global_default"
    trace.min_chunk_size = "global_default"
    trace.max_chunk_size = "global_default"
    trace.chunking_strategy = "global_default"

    # 4. Playbook defaults
    for key, value in playbook_defaults.items():
        if value is not None and key in resolved:
            resolved[key] = value
            if key == "chunk_size":
                trace.chunk_size = "playbook_defaults"
            elif key == "chunk_overlap":
                trace.chunk_overlap = "playbook_defaults"
            elif key == "min_chunk_size":
                trace.min_chunk_size = "playbook_defaults"
            elif key == "max_chunk_size":
                trace.max_chunk_size = "playbook_defaults"
            elif key == "chunking_strategy":
                trace.chunking_strategy = "playbook_defaults"

    # 4b. Content type defaults (can override playbook if more specific)
    for key, value in content_type_defaults.items():
        if value is not None and key in resolved:
            resolved[key] = value
            if key == "chunk_size":
                trace.chunk_size = "content_type_defaults"
            elif key == "chunk_overlap":
                trace.chunk_overlap = "content_type_defaults"
            elif key == "min_chunk_size":
                trace.min_chunk_size = "content_type_defaults"
            elif key == "max_chunk_size":
                trace.max_chunk_size = "content_type_defaults"
            elif key == "chunking_strategy":
                trace.chunking_strategy = "content_type_defaults"

    # 3. Product manual settings
    for key, value in product_manual_settings.items():
        if value is not None and key in resolved:
            resolved[key] = value
            if key == "chunk_size":
                trace.chunk_size = "product_manual_settings"
            elif key == "chunk_overlap":
                trace.chunk_overlap = "product_manual_settings"
            elif key == "min_chunk_size":
                trace.min_chunk_size = "product_manual_settings"
            elif key == "max_chunk_size":
                trace.max_chunk_size = "product_manual_settings"
            elif key == "chunking_strategy":
                trace.chunking_strategy = "product_manual_settings"

    # 2. force_product_chunking_config (if set in run_conf)
    if run_conf.get("force_product_chunking_config"):
        for key, value in product_chunking.items():
            if value is not None and key in resolved:
                resolved[key] = value
                if key == "chunk_size":
                    trace.chunk_size = "force_product_chunking_config"
                elif key == "chunk_overlap":
                    trace.chunk_overlap = "force_product_chunking_config"
                elif key == "min_chunk_size":
                    trace.min_chunk_size = "force_product_chunking_config"
                elif key == "max_chunk_size":
                    trace.max_chunk_size = "force_product_chunking_config"
                elif key == "chunking_strategy":
                    trace.chunking_strategy = "force_product_chunking_config"

    # 1. run_conf overrides (highest priority)
    run_chunking = _ensure_dict(run_conf.get("chunking_config"))
    for key, value in run_chunking.items():
        if value is not None and key in resolved:
            resolved[key] = value
            if key == "chunk_size":
                trace.chunk_size = "run_conf"
            elif key == "chunk_overlap":
                trace.chunk_overlap = "run_conf"
            elif key == "min_chunk_size":
                trace.min_chunk_size = "run_conf"
            elif key == "max_chunk_size":
                trace.max_chunk_size = "run_conf"
            elif key == "chunking_strategy":
                trace.chunking_strategy = "run_conf"

    # Also check for direct overrides in run_conf
    for key in ["chunk_size", "chunk_overlap", "min_chunk_size", "max_chunk_size", "chunking_strategy"]:
        if key in run_conf and run_conf[key] is not None:
            resolved[key] = run_conf[key]
            if key == "chunk_size":
                trace.chunk_size = "run_conf"
            elif key == "chunk_overlap":
                trace.chunk_overlap = "run_conf"
            elif key == "min_chunk_size":
                trace.min_chunk_size = "run_conf"
            elif key == "max_chunk_size":
                trace.max_chunk_size = "run_conf"
            elif key == "chunking_strategy":
                trace.chunking_strategy = "run_conf"

    # Build ChunkingConfig
    chunking_config = ChunkingConfig(
        mode=product_chunking.get("mode", "auto"),
        chunk_size=resolved["chunk_size"],
        chunk_overlap=resolved["chunk_overlap"],
        min_chunk_size=resolved["min_chunk_size"],
        max_chunk_size=resolved["max_chunk_size"],
        chunking_strategy=resolved["chunking_strategy"],
        content_type=resolved["content_type"],
        confidence=product_auto_settings.get("confidence"),
    )

    return EffectiveConfig(
        chunking_config=chunking_config,
        playbook_id=playbook_id,
        playbook_config=playbook_config,
        resolution_trace=trace,
    )
