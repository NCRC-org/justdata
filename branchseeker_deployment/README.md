# BranchSeeker Deployment Package

## Quick Start

1. **Extract this package** to your desired location

2. **Install Python dependencies**:
   ```bash
   pip install -r apps/branchseeker/requirements.txt
   playwright install chromium
   ```

3. **Set up credentials**:
   - Place `bigquery_service_account.json` in `credentials/` directory
   - Copy `.env.example` to `.env` and fill in your API keys

4. **Run the application**:
   ```bash
   cd "#JustData_Repo"
   python -m apps.branchseeker.app
   ```

5. **Open your browser** to `http://localhost:8080`

## Full Documentation

See `DEPLOYMENT_PACKAGE.md` for complete installation and configuration instructions.

## Required Credentials

- **BigQuery Service Account JSON**: Place in `credentials/bigquery_service_account.json`
- **AI API Key**: Set `CLAUDE_API_KEY` or `OPENAI_API_KEY` in `.env` file

## Support

For issues or questions, refer to `DEPLOYMENT_PACKAGE.md` or contact the development team.
