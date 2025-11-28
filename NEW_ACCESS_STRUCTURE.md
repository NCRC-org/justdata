# JustData Platform - New Access Structure

**Date:** 2025-01-27  
**Status:** Proposed Structure

---

## Overview

This document outlines the new access control structure for the JustData platform, including application categorization, user types, and access levels.

---

## Application Categories

### 1. **AI-Driven Reports** 🤖
These applications generate comprehensive written reports with AI-powered insights:

- **BranchSeeker** - Bank branch location analysis with AI-generated narratives
- **BizSight** - Small business lending analysis with AI insights
- **LendSight** - Mortgage lending analysis with AI-powered summaries

**Features:**
- AI-generated executive summaries
- Narrative reports with key findings
- Demographic context and analysis
- Export options: Excel, PDF, PowerPoint
- Social media sharing

### 2. **Interactive Tools** 🛠️
These applications provide interactive dashboards and data exploration:

- **BranchMapper** - Interactive map visualization of bank branch locations
- **CommentMaker** - Tool to help users file comments to federal rulemakings
- **DataExplorer** - Interactive dashboard for HMDA, Small Business, and Branch data (replaces MergerMeter)

**Features:**
- Interactive filtering and exploration
- Real-time data visualization
- Export options: Excel, PDF, PowerPoint
- Social media sharing
- No AI-generated narratives (user-driven analysis)

---

## User Types

### 1. **Public** (Free Login)
- **Price:** **Free**
- **Access Level:** Basic
- **Geographic Limits:** Own county only
- **Export:** View-only (no exports)
- **AI Reports:** Limited access (own county) - LendSight only
- **Interactive Tools:** Limited access (own county) - CommentMaker only
- **DataExplorer:** Locked

### 2. **Just Economy Club Member**
- **Price:** **Free** (with Just Economy Club membership)
- **Access Level:** Basic Plus
- **Geographic Limits:** Own county only
- **Export:** View-only (no exports)
- **AI Reports:** Limited access (own county) - LendSight only
- **Interactive Tools:** Limited access (own county) - CommentMaker only
- **DataExplorer:** Locked
- **Note:** Similar to Public but with Just Economy Club membership benefits

### 3. **Member** (1 login for all NCRC members)
- **Price:** **Included with $900/year NCRC membership** (no additional cost)
- **Access Level:** Standard
- **Geographic Limits:** Up to 3 counties/metro areas
- **Export:** Excel, PDF, PowerPoint
- **AI Reports:** Full access (LendSight, BranchSeeker, BizSight)
- **Interactive Tools:** Full access (BranchMapper, CommentMaker)
- **DataExplorer:** 🔒 **LOCKED** (premium feature - requires Member Plus upgrade)

### 4. **Member Plus** (Expanded DataExplorer - Extra Price)
- **Price:** **$500-750/year** (add-on to Member tier)
- **Access Level:** Enhanced
- **Geographic Limits:** 5+ counties or unlimited
- **Export:** Excel, PDF, PowerPoint
- **AI Reports:** Full access
- **Interactive Tools:** Full access
- **DataExplorer:** ✅ **Full access with enhanced features**
  - Advanced filtering options
  - Bulk export capabilities
  - Custom report builder
  - Historical data access
  - Priority support

### 5. **Institutional** (Banks/For-Profit Businesses)
- **Price:** **$5,000-15,000/year**
  - **Base Tier:** $5,000/year (standard DataExplorer features)
  - **Premium Tier:** $10,000-15,000/year (enhanced DataExplorer features)
- **Access Level:** Professional
- **Geographic Limits:** Unlimited
- **Export:** Excel, PDF, PowerPoint, CSV
- **AI Reports:** Full access
- **Interactive Tools:** Full access
- **DataExplorer:** 
  - Base tier: Standard features
  - Premium tier: Enhanced features (advanced filtering, bulk exports, custom reports, historical data)

### 6. **Staff** (NCRC Staff Members)
- **Price:** **Included with NCRC employment** (no cost)
- **Access Level:** Full
- **Geographic Limits:** Unlimited
- **Export:** All formats (Excel, PDF, PowerPoint, CSV, JSON)
- **AI Reports:** Full access
- **Interactive Tools:** Full access
- **DataExplorer:** Full access (all features)
- **Additional:** Access to Analytics dashboard

### 7. **Admin** (Maintenance and Analytics)
- **Price:** **N/A** (internal only, no cost)
- **Access Level:** System
- **Geographic Limits:** Unlimited
- **Export:** All formats
- **AI Reports:** Full access
- **Interactive Tools:** Full access
- **DataExplorer:** Full access
- **Additional:** 
  - Access to Analytics dashboard
  - Access to Administration dashboard
  - System maintenance tools

---

## Access Matrix

| Application | Public (Free) | Just Economy Club (Free) | Member ($900/yr*) | Member Plus ($500-750/yr) | Institutional ($5K-15K/yr) | Staff (Free) | Admin (Free) |
|------------|---------------|--------------------------|-------------------|---------------------------|----------------------------|--------------|-------------|
| **AI-Driven Reports** |
| LendSight | ✅ Limited | ✅ Limited | ✅ Full (up to 3 counties) | ✅ Full (5+ counties) | ✅ Full (unlimited) | ✅ Full | ✅ Full |
| BranchSeeker | 🔒 Locked | 🔒 Locked | ✅ Full (up to 3 counties) | ✅ Full (5+ counties) | ✅ Full (unlimited) | ✅ Full | ✅ Full |
| BizSight | 🔒 Locked | 🔒 Locked | ✅ Full (up to 3 counties) | ✅ Full (5+ counties) | ✅ Full (unlimited) | ✅ Full | ✅ Full |
| **Interactive Tools** |
| BranchMapper | 🔒 Locked | 🔒 Locked | ✅ Full (up to 3 counties) | ✅ Full (5+ counties) | ✅ Full (unlimited) | ✅ Full | ✅ Full |
| CommentMaker | ✅ Limited | ✅ Limited | ✅ Full | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| DataExplorer | 🔒 Locked | 🔒 Locked | 🔒 **Locked** | ✅ **Full** | ✅ Standard (Base) / Enhanced (Premium) | ✅ Full | ✅ Full |
| **Administrative** |
| Analytics | ❌ Hidden | ❌ Hidden | ❌ Hidden | ❌ Hidden | ❌ Hidden | ✅ Full | ✅ Full |
| Administration | ❌ Hidden | ❌ Hidden | ❌ Hidden | ❌ Hidden | ❌ Hidden | ❌ Hidden | ✅ Full |

*Member tier price: Included with $900/year NCRC membership (no additional cost)

### Legend
- ✅ **Full** - Complete access with all features
- ✅ **Standard** - Standard features (for DataExplorer: basic filtering, standard exports)
- ✅ **Enhanced** - Enhanced features (for DataExplorer: advanced filtering, bulk exports, custom reports)
- ✅ **Limited** - Limited access (own county only, view-only)
- 🔒 **Locked** - Visible but requires membership to access
- ❌ **Hidden** - Not visible to this user type

---

## Feature Permissions by User Type

### Geographic Limits

| User Type | Price | Geographic Selection |
|-----------|-------|---------------------|
| Public | Free | Own county only |
| Just Economy Club | Free | Own county only |
| Member | Included with $900/yr NCRC membership | Up to 3 counties/metro areas |
| Member Plus | $500-750/year (add-on) | 5+ counties or unlimited |
| Institutional | $5,000-15,000/year | Unlimited (any geographic combination) |
| Staff | Included with employment | Unlimited |
| Admin | N/A (internal) | Unlimited |

### Export Capabilities

| User Type | Price | Excel | PDF | PowerPoint | CSV | JSON | Social Share |
|-----------|-------|-------|-----|------------|-----|------|--------------|
| Public | Free | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Just Economy Club | Free | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Member | Included with $900/yr | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Member Plus | $500-750/year | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| Institutional | $5,000-15,000/year | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| Staff | Included with employment | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Admin | N/A (internal) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### DataExplorer Feature Comparison

| Feature | Public | Just Economy Club | Member | Member Plus | Institutional | Staff/Admin |
|---------|--------|-------------------|--------|-------------|---------------|-------------|
| Access to DataExplorer | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Basic filtering | N/A | N/A | ✅ | ✅ | ✅ | ✅ |
| Standard exports | N/A | N/A | ✅ | ✅ | ✅ | ✅ |
| Advanced filtering | N/A | N/A | ❌ | ✅ | ❌ | ✅ |
| Bulk exports | N/A | N/A | ❌ | ✅ | ❌ | ✅ |
| Custom report builder | N/A | N/A | ❌ | ✅ | ❌ | ✅ |
| API access | N/A | N/A | ❌ | ❌ | ❌ | ✅ |
| Historical data access | N/A | N/A | ❌ | ✅ | ❌ | ✅ |

---

## Application Details

### Deprecated Applications

- **MergerMeter** - **DEPRECATED** - Replaced by DataExplorer
  - MergerMeter functionality is now available in DataExplorer
  - Two-bank merger analysis can be done using DataExplorer's lender targeting features

### New Applications

- **CommentMaker** - New application for filing comments to federal rulemakings
  - Helps users prepare and submit regulatory comments
  - Export options: PDF, Word, Excel
  - Social media sharing for comment campaigns

---

## Landing Page Organization

### Section 1: AI-Driven Reports
- **LendSight** - Mortgage lending analysis
- **BranchSeeker** - Bank branch analysis
- **BizSight** - Small business lending analysis

### Section 2: Interactive Tools
- **BranchMapper** - Interactive branch map
- **CommentMaker** - Federal rulemaking comments
- **DataExplorer** - Comprehensive data dashboard

### Visual Differentiation
- AI-Driven Reports: Icon badge with "AI" indicator
- Interactive Tools: Icon badge with "Interactive" indicator
- Each section has a clear header explaining the category

---

## Implementation Notes

### User Type Migration
- **Old "Public User"** → **New "Public"**
- **Old "Just Economy Club Member"** → **New "Just Economy Club"** (kept as separate type)
- **Old "NCRC Organizational Member"** → **New "Member"**
- **Old "NCRC Partner"** → **New "Institutional"** (for banks) or **"Member"** (for nonprofits)
- **Old "NCRC Staff"** → **New "Staff"**
- **Old "NCRC Developer"** → **New "Admin"**

### DataExplorer Access Levels & Pricing
- **DataExplorer is a premium feature** - locked for Member tier
- **Member Plus:** $500-750/year unlocks DataExplorer with enhanced features
- **Institutional Base:** $5,000/year includes standard DataExplorer features
- **Institutional Premium:** $10,000-15,000/year includes enhanced DataExplorer features
- **Enhanced features include:**
  - Advanced filtering options
  - Bulk export capabilities
  - Custom report builder
  - Historical data access
  - Priority support
- **Rationale:** Higher operating costs (real-time queries, large data pulls) require premium pricing for cost recovery

### Authentication & Pricing
- All users require login (no anonymous access)
- **Public/Just Economy Club:** Free accounts
- **Member:** Included with $900/year NCRC membership (no additional cost)
- **Member Plus:** $500-750/year add-on to Member tier
- **Institutional:** $5,000-15,000/year (custom pricing available)
- **Staff/Admin:** Included with NCRC employment (no cost)

---

## Next Steps

1. **Update Landing Page HTML** - Implement new structure
2. **Update Access Control Logic** - Modify user type checks
3. **Create Member Plus Pricing** - Determine pricing structure
4. **Update DataExplorer** - Add enhanced features for Member Plus
5. **Migrate Existing Users** - Map old user types to new types
6. **Update Documentation** - Reflect new access structure

---

**Last Updated:** 2025-01-27

