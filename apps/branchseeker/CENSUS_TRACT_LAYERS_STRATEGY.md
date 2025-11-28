# Census Tract Demographic Layers Strategy
## For BranchMapper Interactive Map

## Overview
Add toggleable census tract layers showing demographic data (income, race/ethnicity) with dynamic shading based on relative percentages compared to the metro area baseline.

---

## Strategy Options

### Strategy 1: Relative Percentage Index (Recommended)
**Concept**: Compare tract percentages to metro area percentages using a ratio or index.

**Formula Options**:
- **Ratio Method**: `Tract % / Metro %`
  - Ratio > 1.5 = "High" (tract has 50%+ more than metro average)
  - Ratio 1.0-1.5 = "Above Average"
  - Ratio 0.67-1.0 = "Average"
  - Ratio < 0.67 = "Below Average"
  
- **Index Method**: `(Tract % - Metro %) / Metro %`
  - Positive = Above metro average
  - Negative = Below metro average
  - Scale: -1.0 to +2.0 (or higher)

**Example**:
- Metro area: 20% Black
- Tract A: 5% Black → Ratio = 0.25 (Below Average - not highlighted)
- Tract B: 40% Black → Ratio = 2.0 (High - highlighted)
- Tract C: 25% Black → Ratio = 1.25 (Above Average - highlighted)

**Pros**: 
- Contextual - accounts for regional demographics
- Highlights areas that stand out relative to their region
- Prevents false positives in diverse metros

**Cons**:
- Requires metro area baseline data
- More complex calculation

---

### Strategy 2: Percentile-Based Shading
**Concept**: Rank tracts within the metro area and shade by percentile.

**Method**:
1. Calculate percentage for each tract
2. Rank all tracts in metro area
3. Shade by percentile (top 25%, top 50%, etc.)

**Pros**:
- Automatically adapts to metro demographics
- Easy to understand (top quartile, etc.)

**Cons**:
- Doesn't show absolute percentages
- Requires all tract data for ranking

---

### Strategy 3: Standard Deviation from Mean
**Concept**: Use statistical standard deviation to identify outliers.

**Method**:
- Calculate metro mean and standard deviation
- Shade tracts based on how many standard deviations they are from the mean
- +2σ = Very High
- +1σ to +2σ = High
- -1σ to +1σ = Average
- <-1σ = Low

**Pros**:
- Statistically sound
- Identifies true outliers

**Cons**:
- More complex for users to understand
- Requires statistical calculations

---

## Recommended Approach: Hybrid Strategy

### Primary Method: Relative Percentage Index with Thresholds

**For each demographic group (Black, Hispanic, Asian, All Non-White)**:

1. **Calculate Metro Baseline**:
   - Get metro area (CBSA) demographic percentages
   - Use this as the comparison standard

2. **Calculate Tract Ratios**:
   ```
   Ratio = (Tract Percentage) / (Metro Percentage)
   ```

3. **Categorize Tracts**:
   - **Very High**: Ratio ≥ 2.0 (tract has 2x+ metro average)
   - **High**: Ratio 1.5-2.0 (tract has 50-100% more than metro)
   - **Above Average**: Ratio 1.2-1.5 (tract has 20-50% more)
   - **Average**: Ratio 0.8-1.2 (within 20% of metro)
   - **Below Average**: Ratio < 0.8 (below metro average)

4. **Color Scheme**:
   - Very High: Dark color (e.g., dark blue for Black, dark green for Hispanic)
   - High: Medium-dark color
   - Above Average: Medium color
   - Average: Light color or no fill
   - Below Average: Very light or transparent

---

## Data Requirements

### 1. Census Tract Boundaries
**Source Options**:
- **Census TIGER/Line Shapefiles**: Free, official boundaries
  - URL: https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html
  - Format: Shapefile or GeoJSON
  - Year: 2020 (most recent)

- **Census Bureau API**: Can fetch GeoJSON directly
  - Endpoint: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer`
  - Requires: State FIPS + County FIPS

- **BigQuery**: If you have tract boundaries in your database

### 2. Demographic Data
**Source Options**:
- **Census API (ACS 5-Year Estimates)**: 
  - Variables needed:
    - B02001_001E: Total population
    - B02001_002E: White alone
    - B02001_003E: Black/African American alone
    - B03001_003E: Hispanic or Latino
    - B02001_005E: Asian alone
    - B19013_001E: Median household income
  
- **BigQuery**: If you already have census data stored
  - Check if you have tract-level demographic tables

- **Your Existing Data**: 
  - You already have LMI and MMCT flags at the branch level
  - May need to aggregate to tract level or join with tract boundaries

### 3. Metro Area (CBSA) Baseline Data
**Source Options**:
- **Census API**: Aggregate tract data to CBSA level
- **BigQuery**: Query existing metro area demographics
- **Calculate on-the-fly**: Sum all tracts in the metro area

---

## Implementation Plan

### Phase 1: Data Preparation
1. **Identify Data Sources**:
   - Check if BigQuery has census tract boundaries
   - Check if BigQuery has tract-level demographic data
   - Determine if Census API is needed

2. **Create API Endpoints**:
   - `/api/census-tracts/<county>` - Get tract boundaries and demographics
   - `/api/metro-demographics/<cbsa>` - Get metro area baseline percentages

3. **Data Processing**:
   - Calculate relative percentages
   - Categorize tracts into shading levels
   - Generate GeoJSON with demographic properties

### Phase 2: Map Integration
1. **Add Layer Control**:
   - Use Leaflet's `L.control.layers()` for toggling
   - Separate controls for each demographic group

2. **Create Choropleth Layers**:
   - Use `L.geoJSON()` with style function
   - Color polygons based on relative percentage category
   - Add popups showing absolute and relative percentages

3. **Performance Optimization**:
   - Load tract data only when layer is enabled
   - Use simplified GeoJSON for faster rendering
   - Consider clustering or simplification for large counties

### Phase 3: UI/UX
1. **Layer Toggle Panel**:
   - Checkboxes for each demographic group
   - Legend showing color scale
   - Info about metro baseline

2. **Interactive Features**:
   - Click tract to see detailed demographics
   - Show both absolute % and relative ratio
   - Highlight metro average for context

---

## Technical Implementation Details

### Leaflet Layer Structure
```javascript
// Example layer structure
const blackPopulationLayer = L.geoJSON(tractData, {
    style: function(feature) {
        const ratio = feature.properties.blackRatio;
        return {
            fillColor: getColorForRatio(ratio),
            fillOpacity: 0.6,
            color: '#333',
            weight: 1
        };
    },
    onEachFeature: function(feature, layer) {
        layer.bindPopup(`
            <strong>${feature.properties.tractName}</strong><br>
            Black Population: ${feature.properties.blackPercent}%<br>
            Metro Average: ${feature.properties.metroBlackPercent}%<br>
            Ratio: ${feature.properties.blackRatio.toFixed(2)}x
        `);
    }
});
```

### Color Scale Function
```javascript
function getColorForRatio(ratio) {
    if (ratio >= 2.0) return '#034ea0';      // Very High - Dark Blue
    if (ratio >= 1.5) return '#2fade3';      // High - Medium Blue
    if (ratio >= 1.2) return '#87ceeb';     // Above Average - Light Blue
    if (ratio >= 0.8) return '#e6f2ff';     // Average - Very Light Blue
    return '#f0f0f0';                         // Below Average - Gray
}
```

---

## Data Source Recommendations

### Option A: Use Census API (Recommended for Start)
**Pros**:
- Always up-to-date
- No need to store large datasets
- Free (with API key)

**Cons**:
- Requires API calls (rate limits)
- Slower initial load
- Need to handle API failures

**Implementation**:
- Create endpoint that calls Census API
- Cache results in session or database
- Fallback to BigQuery if available

### Option B: Use BigQuery (If Available)
**Pros**:
- Fast queries
- Already integrated
- Can pre-calculate ratios

**Cons**:
- Need to ensure data is current
- May need to join multiple tables

**Implementation**:
- Query existing census tables
- Join with tract boundaries if available
- Calculate ratios in SQL

### Option C: Hybrid Approach (Best)
**Pros**:
- Fast for common queries (cached in BigQuery)
- Fresh data when needed (Census API)
- Resilient to failures

**Implementation**:
1. Check BigQuery first for tract data
2. If missing, fetch from Census API
3. Store in BigQuery for future use
4. Calculate ratios on-the-fly

---

## Suggested Next Steps

1. **Check Existing Data**:
   - Does BigQuery have census tract boundaries?
   - Does BigQuery have tract-level demographic data?
   - What's the structure of your existing census data?

2. **Create Proof of Concept**:
   - Start with one county (e.g., Hillsborough, FL)
   - Add one demographic layer (e.g., Black population)
   - Test the relative percentage calculation
   - Verify the shading looks correct

3. **Expand**:
   - Add more demographic groups
   - Add income layer
   - Optimize performance
   - Add user controls

---

## Questions to Answer Before Implementation

1. **Data Availability**:
   - Do you have census tract boundaries in BigQuery?
   - Do you have tract-level demographic data?
   - What years of data are available?

2. **Scope**:
   - Start with one demographic group or all at once?
   - Which groups are priority? (Black, Hispanic, Asian, All Non-White, Income)

3. **Performance**:
   - How many tracts per county? (affects rendering speed)
   - Should we simplify boundaries for performance?

4. **User Experience**:
   - Should layers be on by default or all off?
   - How many layers can be active at once?
   - Should there be a legend panel?

---

## Example API Endpoint Structure

```python
@app.route('/api/census-tracts/<county>')
def get_census_tracts(county):
    """
    Returns GeoJSON of census tracts with demographic data
    and relative percentage calculations
    """
    # 1. Get county FIPS code
    # 2. Get metro area (CBSA) for this county
    # 3. Fetch tract boundaries (from Census API or BigQuery)
    # 4. Fetch tract demographics (from Census API or BigQuery)
    # 5. Calculate metro baseline percentages
    # 6. Calculate relative ratios for each tract
    # 7. Return GeoJSON with all properties
```

---

## Color Scheme Suggestions

### Black Population Layer:
- Very High (2.0x+): #034ea0 (NCRC Dark Blue)
- High (1.5-2.0x): #2fade3 (NCRC Sky Blue)
- Above Average (1.2-1.5x): #87ceeb (Light Blue)
- Average (0.8-1.2x): #e6f2ff (Very Light Blue)
- Below Average (<0.8x): #f0f0f0 (Light Gray)

### Hispanic Population Layer:
- Use green shades (different from blue to distinguish)

### Asian Population Layer:
- Use purple shades

### All Non-White Layer:
- Use orange/red shades

### Income Layer (LMI):
- Use yellow/amber shades (already have this concept)

---

## Would you like me to:

1. **Check your existing data** to see what's available in BigQuery?
2. **Create a proof of concept** with one demographic layer?
3. **Set up the API endpoints** for fetching tract data?
4. **Implement the full layer system** with all demographic groups?

Let me know which approach you'd prefer, and I can start implementing!

