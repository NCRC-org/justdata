# AREA ANALYSIS STRUCTURE - LOCKED

**Status:** ✅ LOCKED - DO NOT MODIFY WITHOUT USER APPROVAL

**Date Locked:** 2024-12-19

## Protected Components

The Area Analysis wizard flow is **locked and working correctly**. Any changes that affect these components require **user approval and warning** before implementation.

### Locked Steps (Area Analysis Flow)

1. **Step 1**: Choose Analysis Type (area vs lender)
2. **Step 2A**: Select Metro Area
   - Metro dropdown with search
   - Buttons in upper corners
   - Pre-loading optimization
3. **Step 3A**: Select Counties
   - Chip/tag interface for county selection
   - Scrollable container within feature card
   - Buttons in upper corners
   - State abbreviation mapping
4. **Step 4A**: Data Filters
5. **Step 5A**: Disclaimer

### Protected Files and Functions

**Files:**
- `apps/dataexplorer/static/js/wizard-steps.js`
  - `step2A` definition (lines ~43-85)
  - `step3A` definition (lines ~86-123)
  - `step4A` definition (lines ~189-236)
  - `step5A` definition (lines ~278-305)
  - `loadMetros()` function
  - `setupMetroDropdown()` function
  - `showMetroDropdown()` / `hideMetroDropdown()` functions
  - `loadCountiesByMetro()` function
  - `removeCounty()` function
  - `selectAllCounties()` / `deselectAllCounties()` functions

- `apps/dataexplorer/templates/wizard.html`
  - CSS for `.step-card[data-step="step2A"]`
  - CSS for `.step-card[data-step="step3A"]`
  - CSS for `.county-tiles-container`
  - CSS for `.county-chip` and `.remove-chip`
  - CSS for `.metro-select-button` and `.metro-dropdown-wrapper`

- `apps/dataexplorer/static/js/wizard.js`
  - `stepPaths.area` array definition

### Key Features (DO NOT BREAK)

1. **Metro Selection (Step 2A)**
   - Buttons in upper left/right corners
   - Custom searchable dropdown
   - Pre-loading from static JSON
   - Fixed positioning overlay

2. **County Selection (Step 3A)**
   - Chip/tag UI (not checkboxes)
   - Format: "County, StateAbbr" (e.g., "Warren, NJ")
   - Remove button (×) on each chip
   - Scrollable container (180px height)
   - Buttons in upper corners
   - All counties selected by default

3. **Layout**
   - Fixed card height (350px)
   - No page scrolling
   - Internal scrolling only
   - Buttons always visible in corners

### Warning Protocol

**Before making ANY changes that affect:**
- Step definitions (step2A, step3A, step4A, step5A)
- Metro dropdown functionality
- County selection UI/UX
- Button positioning
- Step flow/paths
- Related CSS styling

**YOU MUST:**
1. Warn the user that the change will affect locked Area Analysis code
2. Explain what will be modified
3. Get explicit approval before proceeding
4. If user approves, proceed with caution and test thoroughly

### Example Warning Message

```
⚠️ WARNING: This change will affect the LOCKED Area Analysis structure.

The Area Analysis flow (steps 2A-5A) is currently locked and working correctly.
Your requested change will modify:
- [List specific components that will be affected]

Do you want to proceed? This may break the working Area Analysis flow.
```

---

**Last Updated:** 2024-12-19
**Commit Hash:** 850839f (before locking)
