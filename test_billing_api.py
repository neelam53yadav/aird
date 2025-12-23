#!/usr/bin/env python3
"""
Test billing API endpoints.
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1/billing"
WORKSPACE_ID = "550e8400-e29b-41d4-a716-446655440001"  # Default workspace ID
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer dev-token"  # Assuming DISABLE_AUTH is true
}

def test_get_billing_limits():
    """Test getting billing limits."""
    print("Testing billing limits endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/limits?workspace_id={WORKSPACE_ID}", headers=HEADERS)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Plan: {data.get('plan')}")
            print(f"Limits: {json.dumps(data.get('limits'), indent=2)}")
            print(f"Usage: {json.dumps(data.get('usage'), indent=2)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_create_checkout_session(plan: str):
    """Test creating checkout session."""
    print(f"Testing checkout session endpoint for {plan} plan...")
    try:
        payload = {
            "workspace_id": WORKSPACE_ID,
            "plan": plan
        }
        response = requests.post(f"{BASE_URL}/checkout-session", headers=HEADERS, data=json.dumps(payload))
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Checkout URL: {data.get('checkout_url')}")
            print(f"Session ID: {data.get('session_id')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_create_customer_portal():
    """Test creating customer portal session."""
    print("Testing customer portal endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/portal?workspace_id={WORKSPACE_ID}", headers=HEADERS)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Portal URL: {data.get('portal_url')}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all billing API tests."""
    print("🧪 Testing Billing API Endpoints")
    print("=" * 50)
    
    # Test billing limits
    print("\n1. Testing billing limits...")
    limits_success = test_get_billing_limits()
    
    # Test checkout sessions (these will likely fail without real Stripe keys)
    print("\n2. Testing checkout sessions...")
    checkout_pro_success = test_create_checkout_session("pro")
    checkout_enterprise_success = test_create_checkout_session("enterprise")
    
    # Test customer portal
    print("\n3. Testing customer portal...")
    portal_success = test_create_customer_portal()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Billing Limits: {'PASS' if limits_success else 'FAIL'}")
    print(f"🔄 Checkout Pro: {'PASS' if checkout_pro_success else 'FAIL'}")
    print(f"🔄 Checkout Enterprise: {'PASS' if checkout_enterprise_success else 'FAIL'}")
    print(f"🔄 Customer Portal: {'PASS' if portal_success else 'FAIL'}")
    
    if limits_success:
        print("\n🎉 Billing API is working! The limits endpoint is functional.")
        print("💡 Note: Checkout and portal endpoints require valid Stripe keys to work properly.")
    else:
        print("\n❌ Billing API has issues. Check the backend server and database connection.")

if __name__ == "__main__":
    main()