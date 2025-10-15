# JustData - Financial Data Analysis Platform

A comprehensive data analysis platform providing insights across three key financial domains: banking, mortgage, and small business. Built with modern Python architecture and AI-powered analytics.

## 🎯 Overview

JustData is a unified platform that consolidates three specialized financial analysis modules:

- **BranchSeeker** - Banking market intelligence and branch network analysis ✅ **FULLY FUNCTIONAL**
- **LendSight** - Mortgage lending patterns and market trends 🏗️ *Framework Ready*
- **BizSight** - Small business lending and economic indicators 🏗️ *Framework Ready*

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /Users/jadedlebi/justdata
pip install -r requirements.txt
```

### 2. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
# Required for all apps
AI_PROVIDER=claude
CLAUDE_API_KEY=sk-ant-xxx
GCP_PROJECT_ID=your-gcp-project-here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcp-credentials.json
SECRET_KEY=your-random-secret-key

# Optional
OPENAI_API_KEY=sk-xxx
```

### 3. Run an Application

#### BranchSeeker (FDIC Branch Analyzer) - READY TO USE ✅
```bash
python run_branchseeker.py
```
Then open: http://localhost:8080

**Features:**
- Analyze bank branches by county and year
- AI-powered insights using Claude 4 Sonnet
- Interactive web reports with collapsible tables
- Excel, CSV, JSON, and ZIP export options
- Real-time progress tracking with substeps

#### BizSight (Business Analyzer) - SKELETON 🏗️
```bash
python run_bizsight.py
```
Then open: http://localhost:8081

#### LendSight (Lending Analyzer) - SKELETON 🏗️
```bash
python run_lendsight.py
```
Then open: http://localhost:8082

## 🏗️ Project Structure

```
justdata/
├── run_branchseeker.py       # ← Run this for BranchSeeker
├── run_bizsight.py           # ← Run this for BizSight  
├── run_lendsight.py          # ← Run this for LendSight
├── requirements.txt          # ← Install these packages
├── .env                      # ← Your API keys (create this)
│
├── justdata/
│   ├── shared/               # ← Code used by ALL apps
│   │   ├── analysis/         #    AI analysis (Claude 4 integration)
│   │   ├── reporting/        #    Report generation (Excel, PDF)
│   │   ├── utils/            #    Utilities (BigQuery, progress tracking)
│   │   └── web/              #    Templates, CSS, JS
│   │
│   ├── apps/                 # ← Individual apps
│   │   ├── branchseeker/     #    FDIC analyzer (FULL)
│   │   ├── bizsight/         #    Business (SKELETON)
│   │   └── lendsight/        #    Lending (SKELETON)
│   │
│   └── core/
│       └── config/           # ← App configurations
│
└── data/                     # ← Generated reports go here
    └── reports/
        ├── branchseeker/
        ├── bizsight/
        └── lendsight/
```

## 📊 BranchSeeker Features

### Data Analysis
- **FDIC Summary of Deposits (SOD)** data analysis
- County and year-based filtering
- Market concentration analysis
- LMI (Low-to-Moderate Income) and MMCT (Majority-Minority Census Tract) analysis
- Year-over-year trend analysis

### AI-Powered Insights
- **Executive Summary** - High-level market overview
- **Key Findings** - Bullet-pointed insights
- **Trends Analysis** - Year-over-year patterns
- **Bank Strategies** - Market concentration patterns
- **Community Impact** - LMI/MMCT access patterns

### Reporting & Export
- **Interactive Web Reports** - Primary output format
- **Export Options**: Excel (.xlsx), CSV, JSON, ZIP
- **Print-Friendly** - Optimized for printing
- **Collapsible Tables** - Auto-collapse after 10 rows with preview
- **Real-time Progress** - Detailed substeps for AI generation

### Technical Features
- **Real-time Progress Tracking** - Server-sent events
- **Background Processing** - Non-blocking analysis
- **Error Handling** - Graceful failure recovery
- **Responsive Design** - Mobile-friendly interface

## 🌐 API Endpoints

All applications use consistent routing patterns:

| URL | What It Does |
|-----|--------------|
| `GET /` | Main page with analysis form |
| `POST /analyze` | Start new analysis |
| `GET /progress/<job_id>` | Real-time progress updates |
| `GET /report` | View interactive web report |
| `GET /report-data` | Get report data (JSON) |
| `GET /download` | Download ZIP of reports |
| `GET /download?format=excel` | Download Excel file |
| `GET /download?format=csv` | Download CSV file |
| `GET /download?format=json` | Download JSON file |
| `GET /data` | Get app data (counties, etc.) |
| `GET /health` | Health check |

## 🛠️ Technology Stack

### Backend
- **Python 3.11+** - Core runtime
- **Flask** - Web framework
- **pandas** - Data manipulation
- **BigQuery** - Cloud data warehouse

### AI/ML
- **Anthropic Claude 4 Sonnet** - Primary AI engine
- **OpenAI GPT-4** - Secondary AI engine (fallback)

### Frontend
- **HTML5/CSS3/JavaScript** - Web interface
- **Server-Sent Events** - Real-time updates
- **Responsive Design** - Mobile-friendly

### Infrastructure
- **Docker** - Containerization
- **Google Cloud Platform** - Data and deployment
- **BigQuery** - Data warehouse

## 🔧 Development

### Running Locally
```bash
# Start BranchSeeker
python run_branchseeker.py

# Start BizSight
python run_bizsight.py

# Start LendSight
python run_lendsight.py
```

### Environment Variables
```env
# AI Services
CLAUDE_API_KEY=sk-ant-xxx
OPENAI_API_KEY=sk-xxx

# Data Sources
GCP_PROJECT_ID=hdma1-242116
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Application Settings
SECRET_KEY=your-random-secret-key
DEBUG=True
```

## 🚧 Roadmap

### Completed ✅
- **BranchSeeker** - Fully functional banking analysis
- **Shared Infrastructure** - Common utilities and templates
- **AI Integration** - Claude 4 Sonnet with fallback
- **Web Interface** - Interactive reports with export options
- **Progress Tracking** - Real-time updates with substeps

### In Progress 🏗️
- **LendSight** - HMDA lending data analysis
- **BizSight** - Small business lending analysis

### Future Plans 📋
- **Authentication** - User management and access control
- **Advanced Analytics** - Statistical analysis tools
- **Real-time Data** - Streaming data processing
- **Mobile App** - Native mobile interface

## 🔐 Security Considerations

### Data Protection
- Encrypted data transmission
- Secure API endpoints
- Environment variable management
- Audit logging for all operations

### AI Safety
- Objective, third-person analysis only
- No speculation about strategic implications
- Factual pattern reporting without cause attribution
- Professional, analytical tone enforcement

## 📚 Documentation

### Available Documentation
- **README.md** - This document (project overview and quick start)
- **justdata/AGENTS.md** - HubSpot development guidelines
- **justdata/CLAUDE.md** - Claude AI integration notes

### Code Documentation
- Inline docstrings and type hints throughout
- Consistent naming conventions
- Modular architecture for easy extension

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Standards
- Black for code formatting
- Type hints for all functions
- Comprehensive error handling
- Consistent naming conventions

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 👥 Team

- **Jad Edlebi** - Lead Developer (jedlebi@ncrc.org)
- **Jason Richardson** - Project Lead (jrichardson@ncrc.org)

---

**JustData** - Making financial data analysis accessible and insightful.

*This platform provides a solid foundation for comprehensive financial analysis across banking, mortgage, and small business domains.*