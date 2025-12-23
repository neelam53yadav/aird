"""
Billing API endpoints for PrimeData.

This module provides endpoints for Stripe billing integration,
including checkout sessions, customer portal, and webhooks.
"""

import os
import json
import stripe
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.database import get_db
from ..db.models import Workspace, BillingProfile, BillingPlan
from ..core.security import get_current_user

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

router = APIRouter()


class CheckoutSessionRequest(BaseModel):
    """Request model for creating checkout session."""
    workspace_id: str
    plan: str  # "pro" or "enterprise"


class CheckoutSessionResponse(BaseModel):
    """Response model for checkout session."""
    checkout_url: str
    session_id: str


class BillingLimitsResponse(BaseModel):
    """Response model for billing limits."""
    plan: str
    limits: Dict[str, Any]
    usage: Dict[str, Any]


class BillingPortalResponse(BaseModel):
    """Response model for billing portal."""
    portal_url: str


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CheckoutSessionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a Stripe checkout session for plan upgrade.
    
    Args:
        request: Checkout session request with workspace and plan
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Checkout session URL and ID
    """
    try:
        # Get workspace
        workspace = db.query(Workspace).filter(Workspace.id == request.workspace_id).first()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        # Get or create billing profile
        billing_profile = db.query(BillingProfile).filter(
            BillingProfile.workspace_id == request.workspace_id
        ).first()
        
        if not billing_profile:
            billing_profile = BillingProfile(
                workspace_id=request.workspace_id,
                plan=BillingPlan.FREE
            )
            db.add(billing_profile)
            db.commit()
        
        # Create Stripe customer if not exists
        if not billing_profile.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.get('email', ''),
                name=workspace.name,
                metadata={
                    'workspace_id': str(workspace.id)
                }
            )
            billing_profile.stripe_customer_id = customer.id
            db.commit()
        
        # Define plan pricing
        plan_prices = {
            'pro': 'price_1234567890',  # Replace with actual Stripe price ID
            'enterprise': 'price_0987654321'  # Replace with actual Stripe price ID
        }
        
        if request.plan not in plan_prices:
            raise HTTPException(status_code=400, detail="Invalid plan")
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=billing_profile.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan_prices[request.plan],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/app/billing?success=true",
            cancel_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/app/billing?canceled=true",
            metadata={
                'workspace_id': str(workspace.id),
                'plan': request.plan
            }
        )
        
        return CheckoutSessionResponse(
            checkout_url=session.url,
            session_id=session.id
        )
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout session: {str(e)}")


@router.get("/portal", response_model=BillingPortalResponse)
async def get_customer_portal(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Stripe customer portal URL.
    
    Args:
        workspace_id: Workspace ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Customer portal URL
    """
    try:
        # Get billing profile
        billing_profile = db.query(BillingProfile).filter(
            BillingProfile.workspace_id == workspace_id
        ).first()
        
        if not billing_profile or not billing_profile.stripe_customer_id:
            raise HTTPException(status_code=404, detail="No billing profile found")
        
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=billing_profile.stripe_customer_id,
            return_url=f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/app/billing"
        )
        
        return BillingPortalResponse(portal_url=portal_session.url)
        
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create portal session: {str(e)}")


@router.get("/limits", response_model=BillingLimitsResponse)
async def get_billing_limits(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get billing limits and usage for workspace.
    
    Args:
        workspace_id: Workspace ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Billing limits and current usage
    """
    try:
        # Get billing profile
        billing_profile = db.query(BillingProfile).filter(
            BillingProfile.workspace_id == workspace_id
        ).first()
        
        if not billing_profile:
            # Create default billing profile
            billing_profile = BillingProfile(
                workspace_id=workspace_id,
                plan=BillingPlan.FREE
            )
            db.add(billing_profile)
            db.commit()
        
        # Define plan limits
        plan_limits = {
            'free': {
                'max_products': 3,
                'max_data_sources_per_product': 5,
                'max_pipeline_runs_per_month': 10,
                'max_vectors': 10000,
                'schedule_frequency': 'manual'
            },
            'pro': {
                'max_products': 25,
                'max_data_sources_per_product': 50,
                'max_pipeline_runs_per_month': 1000,
                'max_vectors': 1000000,
                'schedule_frequency': 'hourly'
            },
            'enterprise': {
                'max_products': -1,  # Unlimited
                'max_data_sources_per_product': -1,  # Unlimited
                'max_pipeline_runs_per_month': -1,  # Unlimited
                'max_vectors': -1,  # Unlimited
                'schedule_frequency': 'realtime'
            }
        }
        
        current_plan = billing_profile.plan.value
        limits = plan_limits.get(current_plan, plan_limits['free'])
        usage = billing_profile.usage or {}
        
        return BillingLimitsResponse(
            plan=current_plan,
            limits=limits,
            usage=usage
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get billing limits: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks for subscription changes.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Success response
    """
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not webhook_secret:
            raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # Handle different event types
        if event['type'] == 'customer.subscription.created':
            await handle_subscription_created(event)
        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event)
        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event)
        
        return {"status": "success"}
        
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")


async def handle_subscription_created(event: Dict[str, Any]):
    """Handle subscription created event."""
    # Implementation for subscription created
    pass


async def handle_subscription_updated(event: Dict[str, Any]):
    """Handle subscription updated event."""
    # Implementation for subscription updated
    pass


async def handle_subscription_deleted(event: Dict[str, Any]):
    """Handle subscription deleted event."""
    # Implementation for subscription deleted
    pass


def check_billing_limits(workspace_id: str, limit_type: str, current_count: int, db: Session) -> bool:
    """
    Check if workspace is within billing limits.
    
    Args:
        workspace_id: Workspace ID
        limit_type: Type of limit to check
        current_count: Current count of the resource
        db: Database session
        
    Returns:
        True if within limits, False otherwise
    """
    try:
        billing_profile = db.query(BillingProfile).filter(
            BillingProfile.workspace_id == workspace_id
        ).first()
        
        if not billing_profile:
            return True  # No billing profile, assume free tier
        
        # Define limits based on plan
        limits = {
            'free': {
                'max_products': 3,
                'max_data_sources_per_product': 5,
                'max_pipeline_runs_per_month': 10
            },
            'pro': {
                'max_products': 25,
                'max_data_sources_per_product': 50,
                'max_pipeline_runs_per_month': 1000
            },
            'enterprise': {
                'max_products': -1,  # Unlimited
                'max_data_sources_per_product': -1,
                'max_pipeline_runs_per_month': -1
            }
        }
        
        plan_limits = limits.get(billing_profile.plan.value, limits['free'])
        limit = plan_limits.get(limit_type)
        
        if limit is None:
            return True  # No limit defined
        
        if limit == -1:
            return True  # Unlimited
        
        return current_count < limit
        
    except Exception:
        return True  # Default to allowing if check fails