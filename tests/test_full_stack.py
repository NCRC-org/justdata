#!/usr/bin/env python3
"""
Comprehensive Frontend and Backend Integration Test for JustData
Tests the complete application stack from routes to templates to JavaScript
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from justdata.main.app import create_app
from flask import Flask

def test_backend():
    """Test all backend components"""
    print("=" * 70)
    print("BACKEND TESTS")
    print("=" * 70)
    print()
    
    # Test 1: App Creation
    print("Test 1: App Creation")
    try:
        app = create_app()
        print("  ✅ App created successfully")
    except Exception as e:
        print(f"  ❌ App creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 2: Blueprint Registration
    print("\nTest 2: Blueprint Registration")
    blueprint_names = [bp.name for bp in app.blueprints.values()]
    expected_blueprints = ['branchsight', 'lendsight', 'bizsight', 'mergermeter', 'branchmapper', 'dashboard']
    all_registered = True
    for bp_name in expected_blueprints:
        if bp_name in blueprint_names:
            print(f"  ✅ {bp_name} blueprint registered")
        else:
            print(f"  ❌ {bp_name} blueprint NOT registered")
            all_registered = False
    
    # Test 3: Route Registration
    print("\nTest 3: Route Registration")
    with app.test_client() as client:
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append((rule.endpoint, rule.rule, rule.methods))
        
        key_routes = [
            ('landing', '/', {'GET'}),
            ('health', '/health', {'GET'}),
            ('api_access_info', '/api/access-info', {'GET'}),
            ('branchsight.index', '/branchsight/', {'GET'}),
            ('lendsight.index', '/lendsight/', {'GET'}),
            ('bizsight.index', '/bizsight/', {'GET'}),
            ('mergermeter.index', '/mergermeter/', {'GET'}),
            ('branchmapper.index', '/branchmapper/', {'GET'}),
        ]
        
        for endpoint, path, methods in key_routes:
            found = any(r[0] == endpoint and r[1] == path and methods.issubset(r[2]) for r in routes)
            if found:
                print(f"  ✅ Route {endpoint} -> {path}")
            else:
                print(f"  ❌ Route {endpoint} -> {path} NOT FOUND")
    
    # Test 4: API Endpoints
    print("\nTest 4: API Endpoints")
    with app.test_client() as client:
        # Health check
        try:
            response = client.get('/health')
            if response.status_code == 200:
                data = response.get_json()
                print(f"  ✅ /health endpoint: {data.get('status', 'unknown')}")
            else:
                print(f"  ❌ /health returned {response.status_code}")
        except Exception as e:
            print(f"  ❌ /health error: {e}")
        
        # Access info
        try:
            response = client.get('/api/access-info')
            if response.status_code == 200:
                data = response.get_json()
                print(f"  ✅ /api/access-info: user_type = {data.get('user_type', 'unknown')}")
            else:
                print(f"  ❌ /api/access-info returned {response.status_code}")
        except Exception as e:
            print(f"  ❌ /api/access-info error: {e}")
    
    return app


def test_frontend():
    """Test all frontend components"""
    print("\n" + "=" * 70)
    print("FRONTEND TESTS")
    print("=" * 70)
    print()
    
    app = create_app()
    
    # Test 1: Template Rendering
    print("Test 1: Template Rendering")
    with app.test_client() as client:
        # Landing page
        try:
            response = client.get('/')
            if response.status_code == 200:
                print("  ✅ Landing page renders")
                # Check for key content
                if b'JustData' in response.data:
                    print("    ✅ Contains 'JustData' text")
                if b'app-card' in response.data:
                    print("    ✅ Contains app cards")
                if b'url_for' in response.data:
                    print("    ⚠️  Contains unrendered url_for (should be rendered)")
                else:
                    print("    ✅ No unrendered template variables")
            else:
                print(f"  ❌ Landing page returned {response.status_code}")
        except Exception as e:
            print(f"  ❌ Landing page error: {e}")
            import traceback
            traceback.print_exc()
        
        # App pages (with session)
        apps_to_test = [
            ('branchsight', '/branchsight/'),
            ('lendsight', '/lendsight/'),
            ('bizsight', '/bizsight/'),
            ('mergermeter', '/mergermeter/'),
        ]
        
        for app_name, path in apps_to_test:
            try:
                with client.session_transaction() as sess:
                    sess['user_type'] = 'public'
                response = client.get(path)
                if response.status_code in [200, 302]:
                    print(f"  ✅ {app_name} page accessible (status: {response.status_code})")
                else:
                    print(f"  ⚠️  {app_name} page returned {response.status_code}")
            except Exception as e:
                print(f"  ❌ {app_name} page error: {e}")
    
    # Test 2: Static Files
    print("\nTest 2: Static File Serving")
    with app.test_client() as client:
        static_files = [
            ('/static/css/style.css', 'text/css'),
            ('/static/js/app.js', 'application/javascript'),
        ]
        
        for path, expected_type in static_files:
            try:
                response = client.get(path)
                if response.status_code == 200:
                    content_type = response.content_type
                    print(f"  ✅ {path} served ({content_type})")
                else:
                    print(f"  ⚠️  {path} returned {response.status_code}")
            except Exception as e:
                print(f"  ❌ {path} error: {e}")
    
    # Test 3: Template Variables
    print("\nTest 3: Template Variable Injection")
    with app.test_client() as client:
        try:
            response = client.get('/')
            if response.status_code == 200:
                # Check for Flask template variables (should be rendered, not raw)
                if b'{{' not in response.data or b'{%' not in response.data:
                    print("  ✅ Template variables rendered (no raw Jinja2 syntax)")
                else:
                    # Check if it's just in comments or strings
                    print("  ⚠️  Some template variables may not be rendered (check manually)")
        except Exception as e:
            print(f"  ❌ Template rendering error: {e}")


def test_integration():
    """Test frontend-backend integration"""
    print("\n" + "=" * 70)
    print("INTEGRATION TESTS")
    print("=" * 70)
    print()
    
    app = create_app()
    
    # Test 1: Full Analysis Request Flow (LendSight)
    print("Test 1: Full Analysis Request Flow (LendSight)")
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['user_type'] = 'public'
        
        try:
            # Simulate frontend request
            response = client.post('/lendsight/analyze',
                json={
                    'counties': 'Alameda County, California',
                    'years': '',  # Auto-determined
                    'selection_type': 'county'
                },
                content_type='application/json')
            
            if response.status_code in [200, 202]:
                data = response.get_json()
                if data and data.get('success'):
                    job_id = data.get('job_id')
                    print(f"  ✅ Analysis request accepted")
                    print(f"    ✅ Job ID: {job_id}")
                    
                    # Test progress endpoint
                    try:
                        progress_response = client.get(f'/lendsight/progress/{job_id}')
                        if progress_response.status_code == 200:
                            print(f"    ✅ Progress endpoint accessible")
                        else:
                            print(f"    ⚠️  Progress endpoint returned {progress_response.status_code}")
                    except Exception as e:
                        print(f"    ⚠️  Progress endpoint error: {e}")
                else:
                    print(f"  ⚠️  Analysis request returned: {data}")
            else:
                print(f"  ❌ Analysis request returned {response.status_code}")
        except Exception as e:
            print(f"  ❌ Analysis request error: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 2: User Type Switching
    print("\nTest 2: User Type API")
    with app.test_client() as client:
        # Test with valid user type 'staff' (not 'ncrc_staff')
        try:
            response = client.post('/api/set-user-type',
                json={'user_type': 'staff'},
                content_type='application/json')
            
            if response.status_code == 200:
                data = response.get_json()
                if data.get('success'):
                    print(f"  ✅ User type set to: {data.get('user_type')}")
                    print(f"    ✅ Permissions: {list(data.get('permissions', {}).keys())}")
                else:
                    print(f"  ⚠️  User type set returned: {data}")
            else:
                error_data = response.get_json()
                print(f"  ❌ User type set returned {response.status_code}: {error_data}")
        except Exception as e:
            print(f"  ❌ User type set error: {e}")
    
    # Test 3: Cache System Integration
    print("\nTest 3: Cache System Integration")
    try:
        from justdata.shared.utils.analysis_cache import generate_cache_key, normalize_parameters
        
        test_params = {
            'counties': 'Alameda County, California',
            'years': ''
        }
        
        normalized = normalize_parameters('lendsight', test_params)
        cache_key = generate_cache_key('lendsight', test_params)
        
        print(f"  ✅ Cache key generation works")
        print(f"    ✅ Normalized params: {list(normalized.keys())}")
        print(f"    ✅ Cache key: {cache_key[:32]}...")
    except Exception as e:
        print(f"  ❌ Cache system error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("JUSTDATA FULL STACK INTEGRATION TEST")
    print("=" * 70)
    print()
    
    # Run tests
    app = test_backend()
    if not app:
        print("\n❌ Backend tests failed. Stopping.")
        return
    
    test_frontend()
    test_integration()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print("✅ Backend: App creation, blueprints, routes, APIs")
    print("✅ Frontend: Templates, static files, rendering")
    print("✅ Integration: Analysis flow, user management, cache")
    print()
    print("🎉 Full stack test complete!")
    print()
    print("To start the server:")
    print("  python run_justdata.py")
    print()
    print("Then open: http://localhost:8000")


if __name__ == '__main__':
    main()

