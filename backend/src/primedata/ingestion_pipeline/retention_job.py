"""
Artifact Retention Job - Phase 3

Background worker to enforce retention policies on pipeline artifacts.
Archives or deletes artifacts based on their retention policy and age.

Enterprise best practices:
- Soft delete first (mark as DELETED)
- Hard delete after grace period (mark as PURGED)
- Archive to cold storage (optional)
- Cost optimization
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from loguru import logger
from primedata.db.database import get_db
from primedata.db.models import (
    ArtifactStatus,
    ArtifactType,
    PipelineArtifact,
    PipelineRun,
    PipelineRunStatus,
    Product,
    RetentionPolicy,
)
from primedata.indexing.qdrant_client import QdrantClient
from primedata.storage.minio_client import minio_client
from sqlalchemy.orm import Session


def apply_retention_policies(
    db: Session,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Apply retention policies to artifacts.

    Phase 3: Retention policy enforcement

    Args:
        db: Database session
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dictionary with statistics on what was processed
    """
    stats = {
        "archived": 0,
        "deleted": 0,
        "purged": 0,
        "errors": 0,
        "total_processed": 0,
        "total_size_freed_bytes": 0,
    }

    cutoff_dates = {
        RetentionPolicy.DAYS_30: datetime.utcnow() - timedelta(days=30),
        RetentionPolicy.DAYS_90: datetime.utcnow() - timedelta(days=90),
        RetentionPolicy.DAYS_365: datetime.utcnow() - timedelta(days=365),
        RetentionPolicy.ON_FAILURE_KEEP_90: datetime.utcnow() - timedelta(days=90),
    }

    # Process each retention policy
    for policy, cutoff_date in cutoff_dates.items():
        artifacts = (
            db.query(PipelineArtifact)
            .filter(
                PipelineArtifact.retention_policy == policy,
                PipelineArtifact.status == ArtifactStatus.ACTIVE,
                PipelineArtifact.created_at < cutoff_date,
            )
            .all()
        )

        for artifact in artifacts:
            try:
                stats["total_processed"] += 1

                if policy == RetentionPolicy.DELETE_ON_PROMOTE:
                    # Special handling: check if product is promoted
                    # If promoted, delete artifacts from older versions
                    # For now, skip (would need product context)
                    continue

                if dry_run:
                    logger.info(f"[DRY RUN] Would archive artifact {artifact.id} ({artifact.artifact_name})")
                    stats["archived"] += 1
                    stats["total_size_freed_bytes"] += artifact.file_size
                    continue

                # Archive artifact (soft delete)
                artifact.status = ArtifactStatus.DELETED
                artifact.deleted_at = datetime.utcnow()
                db.commit()

                stats["archived"] += 1
                stats["total_size_freed_bytes"] += artifact.file_size
                logger.info(f"Archived artifact {artifact.id} ({artifact.artifact_name}) from {artifact.stage_name}")

            except Exception as e:
                logger.error(f"Error processing artifact {artifact.id}: {e}", exc_info=True)
                stats["errors"] += 1

    # Hard delete artifacts marked as DELETED for more than 7 days
    purge_cutoff = datetime.utcnow() - timedelta(days=7)
    deleted_artifacts = (
        db.query(PipelineArtifact)
        .filter(
            PipelineArtifact.status == ArtifactStatus.DELETED,
            PipelineArtifact.deleted_at < purge_cutoff,
        )
        .all()
    )

    for artifact in deleted_artifacts:
        try:
            # Optionally delete from MinIO (if not already deleted)
            if artifact.storage_bucket != "none" and artifact.storage_bucket != "qdrant":
                try:
                    minio_client.client.remove_object(artifact.storage_bucket, artifact.storage_key)
                    logger.info(f"Deleted artifact from MinIO: {artifact.storage_bucket}/{artifact.storage_key}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete artifact from MinIO {artifact.storage_bucket}/{artifact.storage_key}: {e}"
                    )

            # Mark as purged (hard delete from DB)
            artifact.status = ArtifactStatus.PURGED
            db.commit()

            stats["purged"] += 1
            logger.info(f"Purged artifact {artifact.id} ({artifact.artifact_name})")

        except Exception as e:
            logger.error(f"Error purging artifact {artifact.id}: {e}", exc_info=True)
            stats["errors"] += 1

    return stats


def enforce_keep_last_n_runs_per_product(
    db: Session,
    keep_last_n: int = 5,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Keep full artifact/vector details for only the last N pipeline runs per product.

    - Preserves promoted_version (if any), regardless of age.
    - Preserves current_version (if any), regardless of age.
    - Marks older artifacts as DELETED and attempts to remove their objects from MinIO.
    - Deletes old Qdrant collections when we can identify the collection name from artifacts.

    This reduces storage and keeps UI responsive while retaining recent operational history.
    """
    stats: Dict[str, Any] = {
        "products_processed": 0,
        "artifacts_marked_deleted": 0,
        "minio_objects_removed": 0,
        "qdrant_collections_deleted": 0,
        "errors": 0,
    }

    keep_last_n = max(1, int(keep_last_n))

    qdrant = QdrantClient()

    products = db.query(Product).all()
    for product in products:
        try:
            stats["products_processed"] += 1

            # Determine versions to keep: last N runs + promoted + current
            runs = (
                db.query(PipelineRun)
                .filter(PipelineRun.product_id == product.id)
                .order_by(PipelineRun.created_at.desc())
                .limit(keep_last_n)
                .all()
            )
            keep_versions = {int(r.version) for r in runs if r and r.version is not None}
            if product.promoted_version:
                keep_versions.add(int(product.promoted_version))
            if product.current_version:
                keep_versions.add(int(product.current_version))

            # Mark older artifacts as deleted (but do not hard-delete DB rows)
            old_artifacts = (
                db.query(PipelineArtifact)
                .filter(
                    PipelineArtifact.product_id == product.id,
                    PipelineArtifact.status == ArtifactStatus.ACTIVE,
                    ~PipelineArtifact.version.in_(list(keep_versions)),
                )
                .all()
            )

            for artifact in old_artifacts:
                try:
                    if dry_run:
                        stats["artifacts_marked_deleted"] += 1
                        continue

                    # Attempt to delete underlying object for non-qdrant buckets
                    if artifact.storage_bucket not in ("none", "qdrant"):
                        try:
                            # Use underlying client (MinIO mode). Best-effort.
                            minio_client.client.remove_object(artifact.storage_bucket, artifact.storage_key)
                            stats["minio_objects_removed"] += 1
                        except Exception:
                            # Don't fail retention job on object delete issues
                            pass

                    artifact.status = ArtifactStatus.DELETED
                    artifact.deleted_at = datetime.utcnow()
                    stats["artifacts_marked_deleted"] += 1
                except Exception:
                    stats["errors"] += 1

            # Delete old Qdrant collections for versions not kept (best-effort)
            # We only delete when we can confidently identify the collection name.
            if qdrant.is_connected():
                vector_artifacts = (
                    db.query(PipelineArtifact)
                    .filter(
                        PipelineArtifact.product_id == product.id,
                        PipelineArtifact.artifact_type == ArtifactType.VECTOR,
                        PipelineArtifact.status.in_([ArtifactStatus.ACTIVE, ArtifactStatus.DELETED]),
                        ~PipelineArtifact.version.in_(list(keep_versions)),
                    )
                    .order_by(PipelineArtifact.created_at.desc())
                    .all()
                )
                seen = set()
                for va in vector_artifacts:
                    meta = va.artifact_metadata or {}
                    collection_name = meta.get("collection_name") if isinstance(meta, dict) else None
                    if not collection_name or collection_name in seen:
                        continue
                    seen.add(collection_name)
                    if dry_run:
                        stats["qdrant_collections_deleted"] += 1
                        continue
                    try:
                        if qdrant.delete_collection(collection_name):
                            stats["qdrant_collections_deleted"] += 1
                    except Exception:
                        stats["errors"] += 1

            # Prune DB-heavy pipeline run metrics for older runs (keep row, keep minimal dict)
            old_runs = (
                db.query(PipelineRun)
                .filter(
                    PipelineRun.product_id == product.id,
                    ~PipelineRun.version.in_(list(keep_versions)),
                )
                .all()
            )
            for r in old_runs:
                try:
                    if dry_run:
                        continue
                    if r.metrics is None:
                        r.metrics = {}
                    r.metrics = {"archived": True, "archived_at": datetime.utcnow().isoformat()}
                    r.stage_metrics = None
                except Exception:
                    stats["errors"] += 1

            if not dry_run:
                db.commit()
        except Exception:
            stats["errors"] += 1
            try:
                db.rollback()
            except Exception:
                pass

    return stats


def run_retention_job(dry_run: bool = False) -> Dict[str, Any]:
    """
    Main entry point for retention job.

    Can be called as:
    - Standalone script
    - Cron job
    - Airflow DAG
    - Scheduled task

    Args:
        dry_run: If True, only report without making changes

    Returns:
        Statistics dictionary
    """
    logger.info(f"Starting artifact retention job (dry_run={dry_run})")

    db = next(get_db())
    try:
        # Optional: storage optimization by keeping only last N runs per product (default 5)
        keep_last_n = int(os.getenv("RETAIN_LAST_N_PIPELINE_RUNS", "5"))
        extra = enforce_keep_last_n_runs_per_product(db, keep_last_n=keep_last_n, dry_run=dry_run)
        logger.info(f"Keep-last-N retention completed: {extra}")

        stats = apply_retention_policies(db, dry_run=dry_run)

        logger.info(
            f"Retention job completed: "
            f"processed={stats['total_processed']}, "
            f"archived={stats['archived']}, "
            f"purged={stats['purged']}, "
            f"errors={stats['errors']}, "
            f"size_freed={stats['total_size_freed_bytes']} bytes"
        )

        return stats

    finally:
        db.close()


if __name__ == "__main__":
    # Allow running as standalone script
    import sys

    dry_run = "--dry-run" in sys.argv
    stats = run_retention_job(dry_run=dry_run)
    print(f"Retention job stats: {stats}")
