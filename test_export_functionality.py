#!/usr/bin/env python3
"""
Test script for PrimeData export functionality.

This script tests the export bundle creation and download functionality.
"""

import requests
import json
import zipfile
import tempfile
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
PRODUCT_ID = "dd1816f0-e757-4a18-85c7-0a721b8fa2c1"  # Replace with your product ID

def test_export_creation():
    """Test creating an export bundle."""
    print("🧪 Testing Export Bundle Creation...")
    
    # Create export bundle
    create_url = f"{API_BASE_URL}/api/v1/exports/{PRODUCT_ID}/create"
    create_payload = {
        "version": None  # Use current version
    }
    
    try:
        response = requests.post(create_url, json=create_payload)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Export created successfully!")
            print(f"Bundle ID: {data['bundle_id']}")
            print(f"Bundle Name: {data['bundle_name']}")
            print(f"Size: {data['size_bytes']} bytes")
            print(f"Download URL: {data['download_url']}")
            return data
        else:
            print(f"❌ Failed to create export: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating export: {e}")
        return None

def test_export_listing():
    """Test listing export bundles."""
    print("\n🧪 Testing Export Bundle Listing...")
    
    list_url = f"{API_BASE_URL}/api/v1/exports?product_id={PRODUCT_ID}"
    
    try:
        response = requests.get(list_url)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {len(data)} export bundles")
            for bundle in data:
                print(f"  - {bundle['bundle_name']} ({bundle['size_bytes']} bytes)")
            return data
        else:
            print(f"❌ Failed to list exports: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error listing exports: {e}")
        return []

def test_export_download(export_data):
    """Test downloading and verifying export bundle."""
    if not export_data:
        print("❌ No export data to download")
        return False
        
    print("\n🧪 Testing Export Bundle Download...")
    
    try:
        # Download the bundle
        download_url = export_data['download_url']
        response = requests.get(download_url)
        
        if response.status_code == 200:
            print("✅ Export bundle downloaded successfully!")
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            print(f"Bundle saved to: {temp_path}")
            print(f"Bundle size: {len(response.content)} bytes")
            
            # Verify ZIP contents
            print("\n📦 Verifying ZIP contents...")
            with zipfile.ZipFile(temp_path, 'r') as zip_file:
                file_list = zip_file.namelist()
                print(f"Files in bundle: {file_list}")
                
                # Check for required files
                required_files = ['chunks.jsonl', 'embeddings.json', 'provenance.json']
                missing_files = [f for f in required_files if f not in file_list]
                
                if missing_files:
                    print(f"⚠️  Missing files: {missing_files}")
                else:
                    print("✅ All required files present!")
                
                # Check provenance.json
                if 'provenance.json' in file_list:
                    provenance_data = json.loads(zip_file.read('provenance.json').decode('utf-8'))
                    print(f"📋 Provenance info:")
                    print(f"  - Product ID: {provenance_data['export_info']['product_id']}")
                    print(f"  - Version: {provenance_data['export_info']['version']}")
                    print(f"  - Exported at: {provenance_data['export_info']['exported_at']}")
                
                # Check chunks.jsonl
                if 'chunks.jsonl' in file_list:
                    chunks_content = zip_file.read('chunks.jsonl').decode('utf-8')
                    chunk_count = len([line for line in chunks_content.split('\n') if line.strip()])
                    print(f"📄 Chunks: {chunk_count} entries")
                
                # Check embeddings.json
                if 'embeddings.json' in file_list:
                    embeddings_content = zip_file.read('embeddings.json').decode('utf-8')
                    embeddings_data = json.loads(embeddings_content)
                    print(f"🧠 Embeddings: {len(embeddings_data)} entries")
            
            # Clean up
            os.unlink(temp_path)
            print("🧹 Temporary file cleaned up")
            
            return True
        else:
            print(f"❌ Failed to download bundle: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error downloading bundle: {e}")
        return False

def main():
    """Run all export tests."""
    print("🚀 Starting PrimeData Export Functionality Tests")
    print("=" * 50)
    
    # Test 1: Create export bundle
    export_data = test_export_creation()
    
    # Test 2: List export bundles
    exports_list = test_export_listing()
    
    # Test 3: Download and verify bundle
    if export_data:
        download_success = test_export_download(export_data)
    else:
        download_success = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"  ✅ Export Creation: {'PASS' if export_data else 'FAIL'}")
    print(f"  ✅ Export Listing: {'PASS' if exports_list else 'FAIL'}")
    print(f"  ✅ Export Download: {'PASS' if download_success else 'FAIL'}")
    
    if export_data and exports_list and download_success:
        print("\n🎉 All tests passed! Export functionality is working correctly.")
    else:
        print("\n❌ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
