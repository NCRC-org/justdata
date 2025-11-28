# Landing Page Update Summary

**Date:** 2025-01-27  
**Changes:** Restructure access control and application organization

---

## Key Changes Made

### 1. **Removed Applications**
- ❌ **MergerMeter** - Deprecated (replaced by DataExplorer)

### 2. **Added Applications**
- ✅ **DataExplorer** - Interactive dashboard for HMDA, Small Business, and Branch data
- ✅ **CommentMaker** - Tool to help users file comments to federal rulemakings

### 3. **Application Categorization**

#### **AI-Driven Reports** 🤖
- LendSight
- BranchSeeker
- BizSight

#### **Interactive Tools** 🛠️
- BranchMapper
- CommentMaker
- DataExplorer

### 4. **New User Types**

**Old User Types:**
- Public User
- Just Economy Club Member
- NCRC Organizational Member
- NCRC Partner
- NCRC Staff
- NCRC Developer

**New User Types:**
- **Public** - Free login
- **Just Economy Club** - Just Economy Club members
- **Member** - 1 login for all NCRC members
- **Member Plus** - Expanded DataExplorer options (extra price)
- **Institutional** - Banks/for-profit businesses
- **Staff** - NCRC staff members
- **Admin** - Maintenance and analytics

### 5. **Access Matrix Updates**

| Application | Public | Just Economy Club | Member | Member Plus | Institutional | Staff | Admin |
|------------|--------|-------------------|--------|-------------|---------------|-------|-------|
| **AI-Driven Reports** |
| LendSight | Limited | Limited | Full | Full | Full | Full | Full |
| BranchSeeker | Locked | Locked | Full | Full | Full | Full | Full |
| BizSight | Locked | Locked | Full | Full | Full | Full | Full |
| **Interactive Tools** |
| BranchMapper | Locked | Locked | Full | Full | Full | Full | Full |
| CommentMaker | Limited | Limited | Full | Full | Full | Full | Full |
| DataExplorer | Locked | Locked | Standard | **Enhanced** | Standard | Full | Full |

### 6. **DataExplorer Access Levels**

- **Member:** Standard features (basic filtering, standard exports)
- **Member Plus:** Enhanced features (advanced filtering, bulk exports, custom reports)
- **Institutional:** Standard features (same as Member)
- **Staff/Admin:** Full access (all features including API access)

---

## Implementation Checklist

- [ ] Update user type selector dropdown
- [ ] Update app access configuration object
- [ ] Add application category sections
- [ ] Remove MergerMeter card
- [ ] Add DataExplorer card
- [ ] Add CommentMaker card
- [ ] Update access matrix modal
- [ ] Update feature permissions object
- [ ] Add category badges to app cards
- [ ] Update JavaScript switchUserType function
- [ ] Update app launch handlers
- [ ] Test all user type views
- [ ] Update CSS for new categories

---

## Files to Update

1. `justdata_landing_page.html` - Main landing page
2. `status-dashboard.html` - Update user type references
3. `admin-dashboard.html` - Update user type references
4. Backend authentication - Update user type checks
5. Database schema - Update user type enum

---

**Status:** Ready for implementation

