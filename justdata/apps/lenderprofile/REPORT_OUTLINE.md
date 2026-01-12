# LenderProfile Report Outline

Complete structure for comprehensive lender intelligence reports.

## Report Structure (13 Sections)

### Section 1: Executive Summary
**Data Sources:** FDIC, GLEIF, CourtListener (recent cases), CFPB (recent enforcement), Federal Reserve

**Content:**
- Institution name, HQ, regulator, asset size
- Ownership structure summary
- Key findings (3-5 bullets on strengths/weaknesses)
- Risk indicators (enforcement, litigation, merger status)
- Recommendation flag (partnership/monitor/oppose)

**AI Integration:** AI-generated summary using `LenderProfileAnalyzer.generate_executive_summary()`

---

### Section 2: Corporate Structure
**Data Sources:** GLEIF (legal), TheOrg (operational), SEC Edgar (subsidiaries), Federal Reserve NIC

**Content:**
- Legal entity hierarchy (D3.js interactive tree)
- Parent-subsidiary relationships with ownership %
- Recent structural changes (mergers, divestitures)
- International entities
- **Operational org chart** (if TheOrg data available)

**Visualization:** D3.js tree diagram

---

### Section 3: Financial Profile
**Data Sources:** FDIC/NCUA Call Reports, SEC Edgar (10-K XBRL), Federal Reserve (Y-9C), FRED (economic context)

**Content:**
- 5-year financial trends (assets, ROA, ROE) - Chart.js visualizations
- Balance sheet composition (loan mix, funding sources)
- Income statement highlights
- Capital ratios
- Peer comparison (same asset quartile)
- Business model classification (mortgage specialist, commercial, diversified)

**Visualization:** Chart.js line/bar charts

---

### Section 4: Branch Network and Market Presence
**Data Sources:** FDIC Summary of Deposits, NCUA branches, Census (MSA definitions, LMI tracts)

**Content:**
- Total branches, 5-year trend
- Geographic distribution by state/MSA
- Market share in top markets
- Branch openings/closures timeline
- LMI tract coverage vs peers
- HHI calculations for key markets

**Visualization:** Leaflet maps, Chart.js trend charts

---

### Section 5: CRA Performance
**Data Sources:** FFIEC CRA evaluations (PDF parsing)

**Content:**
- Current rating and exam date
- 10-year rating history
- Test-level ratings (lending, investment, service)
- Examiner findings (strengths/weaknesses extracted from PDF)
- Community development loan/investment totals
- Service test performance
- Peer comparison

**AI Integration:** AI summary of examiner findings

---

### Section 6: Regulatory and Legal History
**Data Sources:** CourtListener, CFPB Enforcement, OCC/Fed/FDIC enforcement pages, DOJ press releases, SEC Litigation

**Content:**
- Federal enforcement actions (10 years): CFPB, OCC, Fed, FDIC, HUD/DOJ
- Significant litigation (fair lending, consumer protection, securities)
- Violation categorization (fair lending, UDAAP, BSA, safety & soundness)
- Timeline visualization of actions
- Severity scoring
- Pattern detection (repeat violations)

**Visualization:** Timeline chart, categorized action list

---

### Section 7: Strategic Positioning
**Data Sources:** SEC Edgar (10-K, DEF 14A, 8-K), NewsAPI, TheOrg

**Content:**
- Mission statement and strategic priorities (from 10-K MD&A)
- Business strategy summary (AI-generated from 10-K)
- Recent strategic initiatives
- Merger/acquisition activity (last 5 years)
- **Executive Leadership Profiles:**
  - C-Suite from SEC proxy: CEO, CFO, CLO, CRO, CCO
  - Background, tenure, prior institutions
  - Compensation structure and incentives
  - Litigation history (from CourtListener)
  - Prior employer issues during tenure
  - Risk scoring
- **Senior Leadership from TheOrg** (if available):
  - SVPs, VPs below C-suite
  - Work histories
  - Department heads
- Board composition (public companies)
- Key risk factors (top 5 from 10-K)

**AI Integration:** AI summarization of 10-K business descriptions and risk factors

---

### Section 7B: Organizational Analysis (NEW - TheOrg data)
**Data Sources:** TheOrg API

**Content:**
- Interactive org chart visualization
- Department sizing analysis:
  - Compliance team size vs assets
  - Fair lending staffing
  - Community development personnel
- Reporting structure assessment:
  - Does compliance report to CEO or buried?
  - Risk management independence
- Recent organizational changes (hires, departures, reorganizations)
- Prior institution concentration analysis
- Staffing adequacy vs peers
- Strategic implications from org structure

**Note:** Only shown if TheOrg data available (skip gracefully if not)

**Visualization:** D3.js org chart

---

### Section 8: Merger and Acquisition Activity
**Data Sources:** Federal Reserve NIC Transformations, SEC Edgar (merger proxies), Federal Register (applications), FDIC

**Content:**
- Historical acquisitions (10 years): target, date, value, rationale
- Pending merger applications: status, comment deadlines, regulatory approval stage
- Divestitures
- Market impact analysis (HHI changes in affected markets)
- Expected branch closures from overlap
- Timeline visualization

**Visualization:** Timeline chart, merger details table

---

### Section 9: Market Context and Competitive Position
**Data Sources:** FDIC Summary of Deposits, Census (MSA data)

**Content:**
- Asset size ranking (national and regional)
- Deposit market share (top 10 MSAs)
- Peer group identification (asset size peers, geographic competitors)
- Competitive positioning
- Market concentration metrics (HHI)
- Performance vs peers (ROA, efficiency ratio, growth rates)

**Visualization:** Comparison charts, ranking tables

---

### Section 10: Recent Developments and News
**Data Sources:** NewsAPI (30 days), Federal Register, Regulations.gov

**Content:**
- News coverage (last 6 months, limited to 30 days on free NewsAPI tier)
- Timeline visualization (article volume by week - spikes = major events)
- Major events callout
- Article feed with sentiment tags
- Category filtering (enforcement, merger, strategic, controversy)
- Relevant regulatory proposals affecting institution
- Upcoming regulatory deadlines (merger comments, CRA exam windows)

**Visualization:** Timeline chart, article feed

**AI Integration:** Sentiment analysis and categorization

---

### Section 11: Regulatory Engagement and Policy Positions
**Data Sources:** Regulations.gov, Federal Register, trade association websites (manual)

**Content:**
- Comment letters on proposed regulations (last 3 years)
  - Topics: CRA reform, capital rules, fair lending, Dodd-Frank
  - Positions taken (support/oppose/modify)
  - Key arguments
- Trade association memberships
- Advocacy priorities
- Congressional testimony (if any)
- Positions on community reinvestment issues

**AI Integration:** AI summary of policy positions from comment letters

---

### Section 12: Advocacy Intelligence Summary
**Data Sources:** Synthesis of all above sections

**Content:**
- Overall assessment (partner/monitor/oppose)
- **CBA Opportunity Evaluation:**
  - Existing CBA status and expiration
  - Performance against commitments
  - Renewal likelihood
  - Negotiation leverage points
  - Score (0-100)
- **Merger Opposition Decision Framework:**
  - Pending applications requiring action
  - CRA weaknesses to cite
  - Fair lending concerns
  - Market concentration arguments
  - Priority score (0-100)
- **Partnership Opportunities:**
  - Strong CRA performers with capacity
  - Geographic alignment with NCRC members
  - Collaborative potential
  - Partnership score (0-100)
- **Priority Concerns Summary:**
  - Top 3 regulatory/compliance issues
  - Top 3 CRA weaknesses
  - Top 3 leverage points
- **Recommended Engagement Approach:**
  - Initial contact strategy
  - Key decision-makers
  - Timing considerations
  - Specific talking points from data
- **Data Gaps:** What requires manual research

**AI Integration:** AI-generated advocacy intelligence using `LenderProfileAnalyzer.generate_advocacy_intelligence()`

---

## Report Generation Flow

1. **Data Collection Phase:**
   - Identifier resolution
   - Parallel API calls (with caching)
   - Data aggregation

2. **Analysis Phase:**
   - Financial trend calculations
   - Peer comparisons
   - Pattern detection
   - Scoring algorithms

3. **AI Summarization Phase:**
   - Executive summary generation
   - Section summaries
   - Key findings extraction
   - Advocacy intelligence synthesis

4. **Report Assembly Phase:**
   - Section builders combine data + AI summaries
   - Visualizations generated
   - PDF export (optional)

5. **Delivery Phase:**
   - HTML report display
   - PDF download option
   - Shareable URL

---

## Section Builders

Each section will have a dedicated builder function in `report_builder/section_builders.py`:

- `build_executive_summary()` - Section 1
- `build_corporate_structure()` - Section 2
- `build_financial_profile()` - Section 3
- `build_branch_network()` - Section 4
- `build_cra_performance()` - Section 5
- `build_regulatory_history()` - Section 6
- `build_strategic_positioning()` - Section 7
- `build_organizational_analysis()` - Section 7B
- `build_merger_activity()` - Section 8
- `build_market_context()` - Section 9
- `build_recent_developments()` - Section 10
- `build_regulatory_engagement()` - Section 11
- `build_advocacy_intelligence()` - Section 12

---

## Report Focus Integration

When a user provides an optional report focus (250-character field), the AI summarization will:
- Prioritize sections relevant to the focus
- Ensure focus areas receive appropriate attention
- Maintain objectivity while addressing user priorities

Example focuses:
- "Focus on CRA performance and recent enforcement actions"
- "Emphasize merger activity and market concentration"
- "Highlight executive leadership and organizational structure"

