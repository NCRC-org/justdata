# Add Executive User Type - Implementation Guide

## Overview
Add a new user type `executive` to the JustData platform for senior leadership. This tier sits between `admin` and `staff` in the hierarchy, with access to all tools staff can see plus future executive-only features.

## Files to Modify

### 1. `justdata/main/auth.py`

#### A. Update `VALID_USER_TYPES` list (around line 22)
```python
# Change FROM:
VALID_USER_TYPES = ['public', 'economy', 'member', 'member_plus', 'institutional', 'staff', 'admin']

# Change TO:
VALID_USER_TYPES = ['public', 'economy', 'member', 'member_plus', 'institutional', 'staff', 'executive', 'admin']
```

#### B. Update `ACCESS_MATRIX` - add `executive` key to EVERY app (lines ~30-120)
Add `'executive': 'full'` or appropriate access level to each app entry. The executive tier should match staff access for now:

```python
ACCESS_MATRIX = {
    'lendsight': {
        'public': 'partial',
        'economy': 'partial',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'executive': 'full',  # ADD THIS LINE
        'admin': 'full'
    },
    'branchseeker': {
        'public': 'locked',
        'economy': 'locked',
        'member': 'full',
        'member_plus': 'full',
        'institutional': 'full',
        'staff': 'full',
        'executive': 'full',  # ADD THIS LINE
        'admin': 'full'
    },
    # ... repeat for ALL apps in the matrix:
    # bizsight, commentmaker, justpolicy, lenderprofile, mergermeter,
    # branchmapper, dataexplorer, analytics, admin, loantrends, memberview
}
```

**Important:** For each app, copy the `staff` access level to `executive`. For `admin` app specifically:
```python
'admin': {
    'public': 'hidden',
    'economy': 'hidden',
    'member': 'hidden',
    'member_plus': 'hidden',
    'institutional': 'hidden',
    'staff': 'hidden',
    'executive': 'hidden',  # Executives cannot access admin panel
    'admin': 'full'
},
```

#### C. Update `FEATURE_PERMISSIONS` dictionary (around line 130)
Add executive tier between staff and admin:

```python
'executive': {
    'geographic_limit': 'unlimited',
    'max_counties': None,
    'can_export': True,
    'export_formats': ['excel', 'pdf', 'powerpoint', 'csv', 'json'],
    'ai_reports': True,
    'dataexplorer_enhanced': True,
    'internal_tools': True,
    'description': 'Senior Executive - full access to all features including internal tools'
},
```

#### D. Update `TIER_PRICING` dictionary (around line 175)
Add executive tier:

```python
'executive': {'price': 0, 'billing': 'free', 'label': 'Executive', 'internal': True},
```

### 2. `justdata/shared/web/templates/justdata_landing_page.html`

#### A. Update the user type selector dropdown (around line 450)
Add executive option:

```html
<select id="userTypeSelect" onchange="switchUserType(this.value)" aria-label="Select user type to view">
    <option value="public" selected>Public (Free)</option>
    <option value="economy">Just Economy Club (Free)</option>
    <option value="member">Member ($900/yr)</option>
    <option value="member_plus">Member Plus ($500-750/yr)</option>
    <option value="institutional">Institutional ($5K-15K/yr)</option>
    <option value="staff">Staff (Free)</option>
    <option value="executive">Executive (Free)</option>  <!-- ADD THIS LINE -->
    <option value="admin">Admin (Free)</option>
</select>
```

#### B. Update JavaScript `getAppAccess()` function (around line 950)
Add executive to every app's access definition:

```javascript
function getAppAccess(appName, userType) {
    const accessMatrix = {
        'lendsight': { public: 'partial', economy: 'partial', member: 'full', member_plus: 'full', institutional: 'full', staff: 'full', executive: 'full', admin: 'full' },
        'branchseeker': { public: 'locked', economy: 'locked', member: 'full', member_plus: 'full', institutional: 'full', staff: 'full', executive: 'full', admin: 'full' },
        'bizsight': { public: 'locked', economy: 'locked', member: 'full', member_plus: 'full', institutional: 'full', staff: 'full', executive: 'full', admin: 'full' },
        'branchmapper': { public: 'locked', economy: 'locked', member: 'full', member_plus: 'full', institutional: 'full', staff: 'full', executive: 'full', admin: 'full' },
        'dataexplorer': { public: 'locked', economy: 'locked', member: 'locked', member_plus: 'full', institutional: 'full', staff: 'full', executive: 'full', admin: 'full' },
        'mergermeter': { public: 'hidden', economy: 'hidden', member: 'hidden', member_plus: 'hidden', institutional: 'hidden', staff: 'full', executive: 'full', admin: 'full' },
        'lenderprofile': { public: 'hidden', economy: 'hidden', member: 'hidden', member_plus: 'hidden', institutional: 'hidden', staff: 'full', executive: 'full', admin: 'full' },
        'memberview': { public: 'hidden', economy: 'hidden', member: 'hidden', member_plus: 'hidden', institutional: 'hidden', staff: 'full', executive: 'full', admin: 'full' },
        'analytics': { public: 'hidden', economy: 'hidden', member: 'hidden', member_plus: 'hidden', institutional: 'hidden', staff: 'full', executive: 'full', admin: 'full' },
        'admin': { public: 'hidden', economy: 'hidden', member: 'hidden', member_plus: 'hidden', institutional: 'hidden', staff: 'hidden', executive: 'hidden', admin: 'full' }
    };
    
    return accessMatrix[appName]?.[userType] || 'hidden';
}
```

#### C. Update JavaScript `featurePermissions` object (around line 870)
Add executive permissions:

```javascript
const featurePermissions = {
    // ... existing entries ...
    'executive': {
        geographicLimit: 'unlimited',
        canExport: true,
        exportFormats: ['excel', 'powerpoint', 'pdf', 'csv', 'json']
    },
    // ... rest of entries ...
};
```

#### D. Update the User Access Matrix modal table (around line 1150)
Add a new column header and cells for Executive in the access matrix table:

In the `<thead>`:
```html
<tr>
    <th>Application</th>
    <th>Public</th>
    <th>Just Economy Club Member</th>
    <th>NCRC Organizational Member</th>
    <th>NCRC Partner</th>
    <th>NCRC Staff</th>
    <th>Executive</th>  <!-- ADD THIS COLUMN -->
    <th>NCRC Developer</th>
</tr>
```

In each `<tbody>` row, add a cell for Executive access. Example for LendSight:
```html
<tr>
    <td>LendSight</td>
    <td><span class="access-status access-partial">...</span></td>
    <td><span class="access-status access-partial">...</span></td>
    <td><span class="access-status access-full">...</span></td>
    <td><span class="access-status access-full">...</span></td>
    <td><span class="access-status access-full">...</span></td>
    <td><span class="access-status access-full"><i class="fas fa-check access-icon" aria-hidden="true"></i>Full Access</span></td>  <!-- ADD THIS CELL -->
    <td><span class="access-status access-full">...</span></td>
</tr>
```

### 3. Create new decorator function in `justdata/main/auth.py`

Add these new decorator functions after the existing `require_access()` function (around line 220):

```python
def executive_required(f):
    """
    Decorator to require executive or admin access for a route.
    
    Usage:
        @app.route('/executive-only')
        @executive_required
        def executive_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_type = get_user_type()
        if user_type not in ['admin', 'executive']:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Executive access required',
                    'user_type': user_type
                }), 403
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin access for a route.
    
    Usage:
        @app.route('/admin-only')
        @admin_required
        def admin_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_type = get_user_type()
        if user_type != 'admin':
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Admin access required',
                    'user_type': user_type
                }), 403
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function


def staff_or_above_required(f):
    """
    Decorator to require staff, executive, or admin access for a route.
    
    Usage:
        @app.route('/internal-tool')
        @staff_or_above_required
        def internal_route():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_type = get_user_type()
        if user_type not in ['admin', 'executive', 'staff']:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({
                    'error': 'Staff access required',
                    'user_type': user_type
                }), 403
            return redirect(url_for('landing'))
        return f(*args, **kwargs)
    return decorated_function
```

### 4. Update `justdata/shared/web/dashboard_routes.py`

Update the analytics route to allow executives (around line 35):

```python
@dashboard_bp.route('/analytics')
def analytics_dashboard():
    """Serve the analytics dashboard."""
    from justdata.main.auth import get_user_type
    from flask import redirect, url_for
    
    user_type = get_user_type()
    # Analytics requires staff, executive, or admin access
    if user_type not in ['admin', 'executive', 'staff']:
        return redirect(url_for('landing'))
    return render_template('analytics-dashboard.html', landing_url=url_for('landing'))
```

## Testing Checklist

After making changes:

1. [ ] Start the app locally: `python run_justdata.py`
2. [ ] Open browser to homepage
3. [ ] Use the "View as" dropdown to select "Executive"
4. [ ] Verify executive can see: LendSight, BizSight, BranchSight, BranchMapper, MergerMeter, DataExplorer, LenderProfile, MemberView, Analytics
5. [ ] Verify executive CANNOT see: Administration
6. [ ] Navigate to `/analytics` as executive - should load
7. [ ] Navigate to `/admin` as executive - should redirect to homepage
8. [ ] Switch to "Staff" and verify same tools are visible
9. [ ] Switch to "Admin" and verify Administration is now visible
10. [ ] Check User Types modal shows Executive column

## Hierarchy Reference

After this change, the user type hierarchy will be:

```
admin (highest)      - Full access including Administration
executive            - Full access to all tools EXCEPT Administration  
staff                - Full access to internal tools (same as executive for now)
institutional        - Full access to member tools, unlimited geography
member_plus          - Full access including DataExplorer
member               - Standard member access
economy              - Just Economy Club (free tier)
public (lowest)      - Limited/locked access
```

## Future Enhancements

Once executive type is in place, you can:

1. Create executive-only dashboard views
2. Add executive-specific reports or analytics
3. Create executive notification features
4. Add executive-only API endpoints using `@executive_required` decorator
