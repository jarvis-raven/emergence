#!/usr/bin/env python3
"""
Test script for Room Dashboard API
Validates that all endpoints return expected data structure.
"""

import requests
import json

BASE_URL = "http://localhost:8765"

def test_health():
    """Test health endpoint."""
    resp = requests.get(f"{BASE_URL}/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data['status'] == 'ok'
    assert 'components' in data
    print("✓ Health check passed")

def test_nautilus_status():
    """Test Nautilus status endpoint."""
    resp = requests.get(f"{BASE_URL}/api/nautilus/status")
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify top-level structure
    assert 'timestamp' in data
    assert 'gravity' in data
    assert 'chambers' in data
    assert 'doors' in data
    assert 'mirrors' in data
    
    # Verify gravity data
    gravity = data['gravity']
    assert 'total_chunks' in gravity
    assert 'total_accesses' in gravity
    assert 'db_size_bytes' in gravity
    assert 'top_memories' in gravity
    assert isinstance(gravity['top_memories'], list)
    
    # Verify chambers data
    chambers = data['chambers']
    assert 'atrium' in chambers
    assert 'corridor' in chambers
    assert 'vault' in chambers
    assert 'recent_promotions' in chambers
    assert isinstance(chambers['recent_promotions'], list)
    
    # Verify doors data
    doors = data['doors']
    assert 'tagged_files' in doors
    assert 'total_files' in doors
    assert 'coverage_pct' in doors
    assert 'top_contexts' in doors
    
    # Verify mirrors data
    mirrors = data['mirrors']
    assert 'total_events' in mirrors
    assert 'coverage' in mirrors
    
    print("✓ Nautilus status structure valid")
    print(f"  - {gravity['total_chunks']} total memories")
    print(f"  - {chambers['atrium']} in atrium, {chambers['corridor']} in corridor, {chambers['vault']} in vault")
    print(f"  - {doors['coverage_pct']}% tagged ({doors['tagged_files']}/{doors['total_files']})")
    print(f"  - {len(gravity['top_memories'])} top memories")
    print(f"  - {len(chambers['recent_promotions'])} recent promotions")

def main():
    print("Testing Room Dashboard API...\n")
    
    try:
        test_health()
        test_nautilus_status()
        print("\n✅ All tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {BASE_URL}")
        print("Make sure the server is running: python3 server.py")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
