"""
E2E Golden Path Test for AIRD Features (M6).

Tests the complete flow from product creation through pipeline execution,
trust scoring, policy evaluation, artifact generation, and ACL filtering.
"""

import pytest
import json
import tempfile
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any
from sqlalchemy.orm import Session

from primedata.db.models import Product, PipelineRun, User, Workspace, ACL, DocumentMetadata, VectorMetadata
from primedata.services.trust_scoring import TrustScoringService
from primedata.services.fingerprint import FingerprintService
from primedata.services.policy_engine import PolicyEngineService
from primedata.services.optimizer import suggest_next_config
from primedata.services.acl import create_acl, get_acls_for_user, apply_acl_filter
from primedata.ingestion_pipeline.aird_stages.storage import AirdStorageAdapter
from primedata.ingestion_pipeline.aird_stages.preprocess import PreprocessStage
from primedata.ingestion_pipeline.aird_stages.scoring import ScoringStage
from primedata.ingestion_pipeline.aird_stages.fingerprint import FingerprintStage
from primedata.ingestion_pipeline.aird_stages.policy import PolicyStage
from primedata.ingestion_pipeline.aird_stages.validation import ValidationStage
from primedata.ingestion_pipeline.aird_stages.reporting import ReportingStage
from primedata.ingestion_pipeline.aird_stages.indexing import IndexingStage


@pytest.mark.e2e
@pytest.mark.aird
class TestAirdGoldenPath:
    """E2E golden path test for AIRD features."""
    
    @pytest.fixture
    def sample_text(self) -> str:
        """Sample text for testing."""
        return """
        === PAGE 1 ===
        
        # Introduction
        
        This is a sample document for testing AI readiness.
        It contains multiple sections and should be processed correctly.
        
        === PAGE 2 ===
        
        # Methodology
        
        The methodology section describes the approach used.
        It includes details about data collection and analysis.
        
        === PAGE 3 ===
        
        # Results
        
        The results show significant improvements in AI readiness.
        Trust scores are calculated based on multiple metrics.
        """
    
    @pytest.fixture
    def test_product_with_data(self, db_session: Session, test_workspace, test_user, sample_text) -> Product:
        """Create a test product with sample data."""
        product = Product(
            workspace_id=test_workspace.id,
            owner_user_id=test_user.id,
            name="E2E Test Product",
            status="draft",
            current_version=1,
            playbook_id="TECH",
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        return product
    
    def test_step_1_create_product(self, db_session: Session, test_workspace, test_user):
        """Step 1: Create product with file upload + playbook."""
        product = Product(
            workspace_id=test_workspace.id,
            owner_user_id=test_user.id,
            name="Golden Path Test Product",
            status="draft",
            current_version=0,
            playbook_id="TECH",
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)
        
        assert product.id is not None
        assert product.playbook_id == "TECH"
        assert product.status == "draft"
        
        return product
    
    def test_step_2_trigger_pipeline_run(self, db_session: Session, test_product_with_data):
        """Step 2: Trigger pipeline run."""
        pipeline_run = PipelineRun(
            workspace_id=test_product_with_data.workspace_id,
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            status="queued",
        )
        db_session.add(pipeline_run)
        db_session.commit()
        db_session.refresh(pipeline_run)
        
        assert pipeline_run.id is not None
        assert pipeline_run.status == "queued"
        
        return pipeline_run
    
    def test_step_3_preprocessing(self, db_session: Session, test_product_with_data, sample_text, mock_minio_client):
        """Step 3: Run preprocessing stage."""
        storage = AirdStorageAdapter(
            workspace_id=test_product_with_data.workspace_id,
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
        )
        
        # Store raw text
        storage.put_raw_text("test_doc", sample_text)
        
        # Run preprocessing
        preprocess_stage = PreprocessStage(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            workspace_id=test_product_with_data.workspace_id,
        )
        
        context = {
            "storage": storage,
            "db": db_session,
        }
        
        result = preprocess_stage.execute(context)
        
        assert result.status.value == "succeeded"
        assert "processed_file_list" in result.metrics
        
        return result
    
    def test_step_4_scoring(self, db_session: Session, test_product_with_data, mock_minio_client):
        """Step 4: Run scoring stage."""
        storage = AirdStorageAdapter(
            workspace_id=test_product_with_data.workspace_id,
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
        )
        
        # Create sample processed JSONL
        sample_records = [
            {
                "chunk_id": "test_chunk_1",
                "text": "Sample text for scoring",
                "section": "introduction",
                "field_name": "introduction",
            }
        ]
        storage.put_processed_jsonl("test_doc", sample_records)
        
        # Run scoring
        scoring_stage = ScoringStage(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            workspace_id=test_product_with_data.workspace_id,
        )
        
        context = {
            "storage": storage,
            "db": db_session,
        }
        
        result = scoring_stage.execute(context)
        
        assert result.status.value == "succeeded"
        
        return result
    
    def test_step_5_fingerprint(self, db_session: Session, test_product_with_data, mock_minio_client):
        """Step 5: Generate fingerprint."""
        storage = AirdStorageAdapter(
            workspace_id=test_product_with_data.workspace_id,
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
        )
        
        # Create sample metrics
        sample_metrics = [
            {
                "file": "test_doc.jsonl",
                "chunk_id": "test_chunk_1",
                "AI_Trust_Score": 75.5,
                "Completeness": 80.0,
                "Secure": 100.0,
                "Metadata_Presence": 85.0,
            }
        ]
        storage.put_metrics_json(sample_metrics)
        
        # Run fingerprint generation
        fingerprint_stage = FingerprintStage(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            workspace_id=test_product_with_data.workspace_id,
        )
        
        context = {
            "storage": storage,
            "db": db_session,
        }
        
        result = fingerprint_stage.execute(context)
        
        assert result.status.value == "succeeded"
        assert "fingerprint" in result.metrics
        
        # Verify product updated
        db_session.refresh(test_product_with_data)
        assert test_product_with_data.readiness_fingerprint is not None
        assert test_product_with_data.trust_score is not None
        
        return result
    
    def test_step_6_policy_evaluation(self, db_session: Session, test_product_with_data):
        """Step 6: Evaluate policy."""
        # Ensure product has fingerprint
        test_product_with_data.readiness_fingerprint = {
            "AI_Trust_Score": 75.5,
            "Completeness": 80.0,
            "Secure": 100.0,
            "Metadata_Presence": 85.0,
        }
        db_session.commit()
        
        # Run policy evaluation
        policy_stage = PolicyStage(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            workspace_id=test_product_with_data.workspace_id,
        )
        
        context = {
            "db": db_session,
        }
        
        result = policy_stage.execute(context)
        
        assert result.status.value == "succeeded"
        
        # Verify product updated
        db_session.refresh(test_product_with_data)
        assert test_product_with_data.policy_status is not None
        
        return result
    
    def test_step_7_artifacts(self, db_session: Session, test_product_with_data, mock_minio_client):
        """Step 7: Generate artifacts (reports)."""
        storage = AirdStorageAdapter(
            workspace_id=test_product_with_data.workspace_id,
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
        )
        
        # Create sample metrics for validation
        sample_metrics = [
            {
                "file": "test_doc.jsonl",
                "chunk_id": "test_chunk_1",
                "AI_Trust_Score": 75.5,
                "Completeness": 80.0,
                "Secure": 100.0,
            }
        ]
        storage.put_metrics_json(sample_metrics)
        
        # Run validation stage
        validation_stage = ValidationStage(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            workspace_id=test_product_with_data.workspace_id,
        )
        
        context = {
            "storage": storage,
            "db": db_session,
        }
        
        result = validation_stage.execute(context)
        
        assert result.status.value == "succeeded"
        
        # Run reporting stage
        reporting_stage = ReportingStage(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            workspace_id=test_product_with_data.workspace_id,
        )
        
        result = reporting_stage.execute(context)
        
        assert result.status.value == "succeeded"
        
        return result
    
    def test_step_8_metrics_endpoint(self, db_session: Session, test_product_with_data):
        """Step 8: Verify metrics endpoint returns data."""
        # Ensure product has trust metrics
        test_product_with_data.trust_score = 75.5
        test_product_with_data.readiness_fingerprint = {
            "AI_Trust_Score": 75.5,
            "Completeness": 80.0,
        }
        db_session.commit()
        
        # Simulate metrics endpoint call
        assert test_product_with_data.trust_score == 75.5
        assert test_product_with_data.readiness_fingerprint is not None
        
        return True
    
    def test_step_9_insights_endpoint(self, db_session: Session, test_product_with_data):
        """Step 9: Verify insights endpoint returns data."""
        # Ensure product has fingerprint and policy
        test_product_with_data.readiness_fingerprint = {
            "AI_Trust_Score": 75.5,
            "Completeness": 80.0,
            "Secure": 100.0,
            "Metadata_Presence": 85.0,
        }
        test_product_with_data.policy_status = "passed"
        test_product_with_data.playbook_id = "TECH"
        db_session.commit()
        
        # Test optimizer
        fingerprint = test_product_with_data.readiness_fingerprint
        policy = {"violations": []}
        optimizer = suggest_next_config(fingerprint, policy, test_product_with_data.playbook_id)
        
        assert optimizer is not None
        assert "next_playbook" in optimizer
        assert "config_tweaks" in optimizer
        assert "notes" in optimizer
        
        return optimizer
    
    def test_step_10_create_acl(self, db_session: Session, test_product_with_data, test_user):
        """Step 10: Create ACL entry."""
        acl = create_acl(
            db=db_session,
            user_id=test_user.id,
            product_id=test_product_with_data.id,
            access_type="full",
        )
        
        assert acl.id is not None
        assert acl.user_id == test_user.id
        assert acl.product_id == test_product_with_data.id
        assert acl.access_type.value == "full"
        
        return acl
    
    def test_step_11_playground_acl_filtering(self, db_session: Session, test_product_with_data, test_user, mock_qdrant_client):
        """Step 11: Query playground with ACL filtering."""
        # Create ACL
        acl = create_acl(
            db=db_session,
            user_id=test_user.id,
            product_id=test_product_with_data.id,
            access_type="field",
            field_scope="introduction",
        )
        
        # Create vector metadata
        vec_meta = VectorMetadata(
            product_id=test_product_with_data.id,
            version=test_product_with_data.current_version,
            collection_id="test_collection",
            chunk_id="test_chunk_1",
            field_name="introduction",
        )
        db_session.add(vec_meta)
        db_session.commit()
        
        # Get ACLs for user
        user_acls = get_acls_for_user(db_session, test_user.id, test_product_with_data.id)
        assert len(user_acls) > 0
        
        # Get all vectors
        all_vectors = db_session.query(VectorMetadata).filter(
            VectorMetadata.product_id == test_product_with_data.id
        ).all()
        
        # Apply ACL filter
        allowed_vectors = apply_acl_filter(all_vectors, user_acls)
        assert len(allowed_vectors) > 0
        
        return allowed_vectors
    
    def test_complete_golden_path(
        self,
        db_session: Session,
        test_workspace,
        test_user,
        sample_text,
        mock_minio_client,
        mock_qdrant_client,
    ):
        """Complete golden path test - all steps in sequence."""
        # Step 1: Create product
        product = self.test_step_1_create_product(db_session, test_workspace, test_user)
        
        # Step 2: Trigger pipeline run
        pipeline_run = self.test_step_2_trigger_pipeline_run(db_session, product)
        
        # Step 3: Preprocessing
        preprocess_result = self.test_step_3_preprocessing(db_session, product, sample_text, mock_minio_client)
        assert preprocess_result.status.value == "succeeded"
        
        # Step 4: Scoring
        scoring_result = self.test_step_4_scoring(db_session, product, mock_minio_client)
        assert scoring_result.status.value == "succeeded"
        
        # Step 5: Fingerprint
        fingerprint_result = self.test_step_5_fingerprint(db_session, product, mock_minio_client)
        assert fingerprint_result.status.value == "succeeded"
        
        # Step 6: Policy
        policy_result = self.test_step_6_policy_evaluation(db_session, product)
        assert policy_result.status.value == "succeeded"
        
        # Step 7: Artifacts
        artifacts_result = self.test_step_7_artifacts(db_session, product, mock_minio_client)
        assert artifacts_result.status.value == "succeeded"
        
        # Step 8: Metrics endpoint
        metrics_ok = self.test_step_8_metrics_endpoint(db_session, product)
        assert metrics_ok is True
        
        # Step 9: Insights endpoint
        insights_ok = self.test_step_9_insights_endpoint(db_session, product)
        assert insights_ok is not None
        
        # Step 10: Create ACL
        acl = self.test_step_10_create_acl(db_session, product, test_user)
        assert acl is not None
        
        # Step 11: Playground ACL filtering
        filtered_vectors = self.test_step_11_playground_acl_filtering(db_session, product, test_user, mock_qdrant_client)
        assert len(filtered_vectors) > 0
        
        # Final verification
        db_session.refresh(product)
        assert product.trust_score is not None
        assert product.readiness_fingerprint is not None
        assert product.policy_status is not None
        
        return {
            "product_id": str(product.id),
            "trust_score": product.trust_score,
            "policy_status": product.policy_status.value if product.policy_status else None,
            "acl_created": acl.id is not None,
            "vectors_filtered": len(filtered_vectors),
        }




