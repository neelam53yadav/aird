"""
Database models for PrimeData.

This file contains placeholder models that will be expanded as the application grows.
"""

import uuid
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, ForeignKey, Enum as SQLEnum, UniqueConstraint, Index, Float, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from primedata.db.database import Base

# Import enterprise models
from .models_enterprise import (
    DataQualityRule, DataQualityRuleAudit, DataQualityRuleSet,
    DataQualityRuleAssignment, DataQualityComplianceReport,
    RuleSeverity, RuleStatus, AuditAction
)


class AuthProvider(str, Enum):
    """Authentication provider enum."""
    GOOGLE = "google"
    SIMPLE = "simple"
    NONE = "none"


class WorkspaceRole(str, Enum):
    """Workspace role enum."""
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class ProductStatus(str, Enum):
    """Product status enum."""
    DRAFT = "draft"
    RUNNING = "running"
    READY = "ready"
    FAILED = "failed"
    FAILED_POLICY = "failed_policy"  # M2: Policy evaluation failed
    READY_WITH_WARNINGS = "ready_with_warnings"  # M2: Policy passed but with warnings


class DataSourceType(str, Enum):
    """Data source type enum."""
    WEB = "web"
    DB = "db"
    CONFLUENCE = "confluence"
    SHAREPOINT = "sharepoint"
    FOLDER = "folder"


class BillingPlan(str, Enum):
    """Billing plan enum."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class PipelineRunStatus(str, Enum):
    """Pipeline run status enum."""
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    READY_WITH_WARNINGS = "ready_with_warnings"  # M0: Pipeline completed with warnings
    FAILED_POLICY = "failed_policy"  # M0: Pipeline failed policy evaluation


class PolicyStatus(str, Enum):
    """Policy evaluation status enum (M2)."""
    PASSED = "passed"
    FAILED = "failed"
    WARNINGS = "warnings"
    UNKNOWN = "unknown"


class RawFileStatus(str, Enum):
    """Raw file processing status enum."""
    INGESTED = "ingested"  # File uploaded to MinIO and recorded in DB
    PROCESSING = "processing"  # Currently being processed by pipeline
    PROCESSED = "processed"  # Successfully processed by pipeline
    FAILED = "failed"  # Processing failed
    DELETED = "deleted"  # Soft deleted


class ArtifactType(str, Enum):
    """Pipeline artifact type enum."""
    JSONL = "jsonl"  # Processed chunks
    JSON = "json"  # Metrics, fingerprint, etc.
    CSV = "csv"  # Validation summaries
    PDF = "pdf"  # Trust reports
    VECTOR = "vector"  # Qdrant vectors
    TEXT = "text"  # Plain text files
    BINARY = "binary"  # Other binary files


class ArtifactStatus(str, Enum):
    """Artifact status enum for lifecycle management."""
    ACTIVE = "active"  # Currently in use
    ARCHIVED = "archived"  # Moved to cold storage
    DELETED = "deleted"  # Soft deleted
    PURGED = "purged"  # Hard deleted (after retention period)


class RetentionPolicy(str, Enum):
    """Artifact retention policy enum."""
    KEEP_FOREVER = "keep_forever"  # Never delete (production artifacts)
    DAYS_30 = "30_days"  # Keep for 30 days
    DAYS_90 = "90_days"  # Keep for 90 days
    DAYS_365 = "365_days"  # Keep for 1 year
    DELETE_ON_PROMOTE = "delete_on_promote"  # Delete when product is promoted
    ON_FAILURE_KEEP_90 = "on_failure_keep_90"  # Keep failed runs for 90 days


class ACLAccessType(str, Enum):
    """ACL access type enum (M5)."""
    FULL = "full"
    INDEX = "index"
    DOCUMENT = "document"
    FIELD = "field"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    timezone = Column(String(50), nullable=True, default='UTC')
    picture_url = Column(String(500), nullable=True)
    auth_provider = Column(SQLEnum(AuthProvider), nullable=False, default=AuthProvider.NONE)
    google_sub = Column(String(255), unique=True, nullable=True, index=True)
    roles = Column(JSON, nullable=False, default=list)  # List of roles
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspace_memberships = relationship("WorkspaceMember", back_populates="user")
    owned_products = relationship("Product", back_populates="owner")
    acls = relationship("ACL", back_populates="user")  # M5


class Workspace(Base):
    """Workspace model."""
    __tablename__ = "workspaces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    members = relationship("WorkspaceMember", back_populates="workspace")
    products = relationship("Product", back_populates="workspace")
    data_quality_rules = relationship("DataQualityRule", back_populates="workspace")
    billing_profile = relationship("BillingProfile", back_populates="workspace", uselist=False)


class WorkspaceMember(Base):
    """Workspace membership model."""
    __tablename__ = "workspace_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(SQLEnum(WorkspaceRole), nullable=False, default=WorkspaceRole.VIEWER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", back_populates="workspace_memberships")
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('workspace_id', 'user_id', name='unique_workspace_user'),
    )


class Product(Base):
    """Product model."""
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(ProductStatus), nullable=False, default=ProductStatus.DRAFT)
    current_version = Column(Integer, nullable=False, default=0)
    promoted_version = Column(Integer, nullable=True, default=None)
    # AIRD playbook configuration (M1)
    playbook_id = Column(String(50), nullable=True, default=None)  # e.g., "TECH", "SCANNED", "REGULATORY"
    # Preprocessing statistics (M1)
    preprocessing_stats = Column(JSON, nullable=True, default=None)  # sections, chunks, mid_sentence_boundary_rate
    # Trust scoring and policy (M2)
    trust_score = Column(Float, nullable=True, default=None)  # Aggregated AI Trust Score
    readiness_fingerprint = Column(JSON, nullable=True, default=None)  # Readiness fingerprint (all 13 metrics)
    policy_status = Column(SQLEnum(PolicyStatus), nullable=True, default=PolicyStatus.UNKNOWN)  # M2: Policy evaluation status
    policy_violations = Column(JSON, nullable=True, default=list)  # List of violation strings
    chunk_metrics = Column(JSON, nullable=True, default=list)  # Per-chunk metrics (optional, can use metrics.json instead)
    # Artifacts and reports (M3)
    validation_summary_path = Column(String(500), nullable=True, default=None)  # MinIO path to validation CSV
    trust_report_path = Column(String(500), nullable=True, default=None)  # MinIO path to trust report PDF
    # Chunking configuration
    chunking_config = Column(JSON, nullable=True, default=lambda: {
        "mode": "auto",  # "auto" or "manual"
        "auto_settings": {
            "content_type": "general",
            "model_optimized": True,
            "confidence_threshold": 0.7
        },
        "manual_settings": {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "min_chunk_size": 100,
            "max_chunk_size": 2000,
            "chunking_strategy": "fixed_size"
        },
        "last_analyzed": None,
        "analysis_confidence": 0.0
    })
    # Embedding configuration
    embedding_config = Column(JSON, nullable=True, default=lambda: {
        "embedder_name": "minilm",
        "embedding_dimension": 384
    })
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="products")
    owner = relationship("User", back_populates="owned_products")
    data_sources = relationship("DataSource", back_populates="product")
    data_quality_rules = relationship("DataQualityRule", back_populates="product")
    document_metadata = relationship("DocumentMetadata", back_populates="product")  # M4
    raw_files = relationship("RawFile", back_populates="product")  # Track ingested raw files
    vector_metadata = relationship("VectorMetadata", back_populates="product")  # M4
    acls = relationship("ACL", back_populates="product")  # M5
    pipeline_artifacts = relationship("PipelineArtifact", back_populates="product")  # Track pipeline artifacts
    
    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint('workspace_id', 'name', name='unique_workspace_product_name'),
        Index('idx_products_workspace_id', 'workspace_id'),
        Index('idx_products_owner_user_id', 'owner_user_id'),
    )


class DataSource(Base):
    """Data source model."""
    __tablename__ = "data_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, default="Unnamed Data Source")
    type = Column(SQLEnum(DataSourceType), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    last_cursor = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace")
    product = relationship("Product", back_populates="data_sources")
    
    # Indexes
    __table_args__ = (
        Index('idx_data_sources_workspace_id', 'workspace_id'),
        Index('idx_data_sources_product_id', 'product_id'),
    )


class RawFileStatus(str, Enum):
    """Raw file processing status enum."""
    INGESTED = "ingested"  # File uploaded to MinIO and recorded in DB
    PROCESSING = "processing"  # Currently being processed by pipeline
    PROCESSED = "processed"  # Successfully processed by pipeline
    FAILED = "failed"  # Processing failed
    DELETED = "deleted"  # Soft deleted


class RawFile(Base):
    """Raw file model for tracking ingested files in MinIO.
    
    Enterprise-grade metadata catalog for object storage files.
    Follows the metadata catalog pattern (DB for queries, MinIO for storage).
    """
    __tablename__ = "raw_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    data_source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=0)
    filename = Column(String(500), nullable=False)  # Original filename
    file_stem = Column(String(500), nullable=False, index=True)  # Filename without extension (for preprocessing)
    minio_key = Column(String(1000), nullable=False, unique=True)  # Full MinIO object key
    minio_bucket = Column(String(255), nullable=False, default="primedata-raw")
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String(255), nullable=True)  # MIME type
    status = Column(SQLEnum(RawFileStatus), nullable=False, default=RawFileStatus.INGESTED)  # Processing status
    file_checksum = Column(String(64), nullable=True)  # MD5 or SHA256 checksum for integrity validation
    minio_etag = Column(String(255), nullable=True)  # MinIO ETag for validation
    ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)  # When processing completed
    error_message = Column(Text, nullable=True)  # Error message if processing failed
    
    # Relationships
    workspace = relationship("Workspace")
    product = relationship("Product")
    data_source = relationship("DataSource")
    
    # Indexes
    __table_args__ = (
        Index('idx_raw_files_product_version', 'product_id', 'version'),
        Index('idx_raw_files_file_stem', 'file_stem'),
        Index('idx_raw_files_data_source', 'data_source_id'),
        Index('idx_raw_files_status', 'status'),  # For querying by status
        UniqueConstraint('product_id', 'version', 'file_stem', name='uq_raw_file_product_version_stem'),
    )


class DocumentMetadata(Base):
    """Document metadata model for tracking chunk-level information (M4)."""
    __tablename__ = "document_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=0)
    chunk_id = Column(String(255), nullable=False, index=True)
    score = Column(Float, nullable=True)  # AI_Trust_Score for chunk
    source_file = Column(String(500), nullable=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    field_name = Column(String(255), nullable=True)
    extra_tags = Column(JSON, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="document_metadata")
    
    # Indexes
    __table_args__ = (
        Index('idx_document_metadata_product_version', 'product_id', 'version'),
        Index('idx_document_metadata_chunk_id', 'chunk_id'),
        Index('idx_document_metadata_field_name', 'field_name'),
    )


class VectorMetadata(Base):
    """Vector metadata model for tracking Qdrant vector information (M4)."""
    __tablename__ = "vector_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=0)
    collection_id = Column(String(255), nullable=False)  # Qdrant collection name
    chunk_id = Column(String(255), nullable=False, index=True)
    page_number = Column(Integer, nullable=True)
    section = Column(String(255), nullable=True)
    field_name = Column(String(255), nullable=True, index=True)  # For ACL field_scope
    tags = Column(JSON, nullable=True, default=None)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="vector_metadata")
    
    # Indexes
    __table_args__ = (
        Index('idx_vector_metadata_product_version', 'product_id', 'version'),
        Index('idx_vector_metadata_chunk_id', 'chunk_id'),
        Index('idx_vector_metadata_field_name', 'field_name'),
        Index('idx_vector_metadata_collection', 'collection_id'),
    )


class ACL(Base):
    """Access Control List model (M5)."""
    __tablename__ = "acls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    access_type = Column(SQLEnum(ACLAccessType), nullable=False, index=True)
    index_scope = Column(String(500), nullable=True)  # Comma-separated index IDs or null
    doc_scope = Column(String(500), nullable=True)  # Comma-separated document IDs or null
    field_scope = Column(String(500), nullable=True)  # Comma-separated field names or null
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="acls")
    product = relationship("Product", back_populates="acls")
    
    # Indexes
    __table_args__ = (
        Index('idx_acls_user_id', 'user_id'),
        Index('idx_acls_product_id', 'product_id'),
        Index('idx_acls_access_type', 'access_type'),
        Index('idx_acls_user_product', 'user_id', 'product_id'),
    )


class PipelineRun(Base):
    """Pipeline run model."""
    __tablename__ = "pipeline_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(SQLEnum(PipelineRunStatus), nullable=False, default=PipelineRunStatus.QUEUED)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    dag_run_id = Column(String(255), nullable=True, index=True)
    metrics = Column(JSON, nullable=False, default=dict)
    # AIRD stage tracking fields (M0)
    stage_metrics = Column(JSON, nullable=True, default=None)  # Per-stage metrics (deprecated, use metrics.aird_stages)
    aird_stages_completed = Column(JSON, nullable=True, default=None)  # List of completed stage names (deprecated, use metrics.aird_stages_completed)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace")
    product = relationship("Product")
    artifacts = relationship("PipelineArtifact", back_populates="pipeline_run", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_pipeline_runs_product_version', 'product_id', 'version'),
        Index('idx_pipeline_runs_workspace_id', 'workspace_id'),
        Index('idx_pipeline_runs_dag_run_id', 'dag_run_id'),
    )


class PipelineArtifact(Base):
    """Pipeline artifact registry for enterprise traceability.
    
    Tracks all artifacts generated during pipeline execution:
    - Location (MinIO bucket/key)
    - Integrity (size, checksum)
    - Lineage (input artifacts)
    - Metadata (stage-specific info)
    - Retention (lifecycle management)
    
    Enables full data lineage, audit trails, and cost optimization.
    """
    __tablename__ = "pipeline_artifacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    pipeline_run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False, index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    
    # Artifact identification
    stage_name = Column(String(100), nullable=False, index=True)  # "preprocess", "scoring", "fingerprint", etc.
    artifact_type = Column(SQLEnum(ArtifactType), nullable=False)  # "jsonl", "json", "csv", "pdf", "vector"
    artifact_name = Column(String(255), nullable=False)  # "processed_chunks", "metrics", "fingerprint", etc.
    
    # Storage location
    minio_bucket = Column(String(255), nullable=False)  # "primedata-clean", "primedata-embed", etc.
    minio_key = Column(String(1000), nullable=False, index=True)  # Full MinIO object key
    file_size = Column(BigInteger, nullable=False)  # Size in bytes
    checksum = Column(String(64), nullable=True)  # MD5 or SHA256 for integrity verification
    minio_etag = Column(String(255), nullable=True)  # MinIO ETag for validation
    
    # Data lineage (Phase 2)
    input_artifacts = Column(JSON, nullable=True, default=list)  # List of artifact IDs this depends on
    # Format: [{"artifact_id": "uuid", "stage": "preprocess", "artifact_name": "processed_chunks"}]
    
    # Stage-specific metadata (renamed from 'metadata' as it's reserved in SQLAlchemy)
    artifact_metadata = Column(JSON, nullable=True, default=dict)  # Stage-specific metadata:
    # - chunks_count, files_processed, playbook_id, thresholds, embedding_model, etc.
    
    # Lifecycle management (Phase 3)
    status = Column(SQLEnum(ArtifactStatus), nullable=False, default=ArtifactStatus.ACTIVE, index=True)
    retention_policy = Column(SQLEnum(RetentionPolicy), nullable=False, default=RetentionPolicy.DAYS_90)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Optional: Track who/what created it (for audit)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # If user-triggered
    
    # Relationships
    pipeline_run = relationship("PipelineRun", back_populates="artifacts")
    workspace = relationship("Workspace")
    product = relationship("Product")
    creator = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_artifacts_product_version', 'product_id', 'version'),
        Index('idx_artifacts_stage_type', 'stage_name', 'artifact_type'),
        Index('idx_artifacts_status_created', 'status', 'created_at'),
        Index('idx_artifacts_retention', 'retention_policy', 'created_at'),
        Index('idx_artifacts_minio_key', 'minio_key'),  # For quick lookup by MinIO key
    )


class Pipeline(Base):
    """Data pipeline model (placeholder)."""
    __tablename__ = "pipelines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    config = Column(Text)  # JSON configuration
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DqViolationSeverity(str, Enum):
    """Data quality violation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DqViolation(Base):
    """Data quality violation model."""
    __tablename__ = "dq_violations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    pipeline_run_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Violation details
    rule_name = Column(String(255), nullable=False)
    rule_type = Column(String(100), nullable=False)
    severity = Column(SQLEnum(DqViolationSeverity), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True, default=dict)
    
    # Statistics
    affected_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)
    violation_rate = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product")
    
    # Indexes
    __table_args__ = (
        Index('idx_dq_violations_product_version', 'product_id', 'version'),
        Index('idx_dq_violations_severity', 'severity'),
        Index('idx_dq_violations_created_at', 'created_at'),
    )


class BillingProfile(Base):
    """Billing profile for workspace."""
    __tablename__ = "billing_profiles"
    
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), primary_key=True)
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    plan = Column(SQLEnum(BillingPlan), default=BillingPlan.FREE, nullable=False)
    default_payment_method_id = Column(String(255), nullable=True)
    usage = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    workspace = relationship("Workspace", back_populates="billing_profile")
    
    # Indexes
    __table_args__ = (
        Index('idx_billing_profiles_stripe_customer', 'stripe_customer_id'),
        Index('idx_billing_profiles_plan', 'plan'),
    )
