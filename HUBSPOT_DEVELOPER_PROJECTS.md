# HubSpot Developer Projects - Modern Integration Approach

## 🚀 Why Developer Projects?

HubSpot is **deprecating legacy apps** and moving to **Developer Projects** as the modern standard for integrations. Here's why you should use them:

### Key Benefits

✅ **Future-Proof**
- Legacy apps are being phased out
- Developer projects are the officially recommended approach
- Long-term support and updates

✅ **CI/CD Integration**
- Native GitHub integration
- Automated deployment workflows
- Version control built-in

✅ **Better Development Workflow**
- Bundle source code, apps, and extensions together
- Single deployable package
- Consistent deployment process

✅ **Modern Architecture**
- Supports modern development practices
- Better tooling and CLI support
- Improved debugging and logging

## 📊 Comparison: Legacy Apps vs Developer Projects

| Feature | Legacy Apps | Developer Projects |
|---------|-------------|-------------------|
| **Status** | ⚠️ Being deprecated | ✅ Actively supported |
| **GitHub Integration** | ❌ Manual | ✅ Built-in |
| **CI/CD Support** | ❌ Limited | ✅ Native |
| **Deployment** | 🔧 Manual process | 🚀 Automated |
| **Version Control** | 📝 Separate | 🔗 Integrated |
| **Future Updates** | ❌ Limited | ✅ Regular updates |
| **Recommended** | ❌ No | ✅ Yes |

## 🛠️ Creating a Developer Project

### Step 1: Install HubSpot CLI

```bash
# Local installation (recommended)
npm install --save-dev @hubspot/cli

# Or global installation
sudo npm install -g @hubspot/cli
```

### Step 2: Initialize HubSpot (Required First)

Before creating a project, you need to initialize HubSpot and authenticate:

```bash
# If installed locally:
npx hs init

# If installed globally:
hs init
```

This creates the `hubspot.config.yml` file needed for project creation.

### Step 3: Create the Developer Project

After initialization, create your developer project:

```bash
# If installed locally:
npx hs project create

# If installed globally:
hs project create
```

### Step 4: Interactive Setup

The CLI will guide you through:

**1. Project Name**
```
? Enter project name: justdata-hubspot
```

**2. Project Template**
```
? Choose a template:
  ❯ None (blank project) - for API integrations
    React app
    Serverless functions
    CMS theme
```
→ Choose **"None"** for JustData (API-only integration)

**3. Authentication**
```
? How would you like to authenticate?
  ❯ Personal Access Key (recommended for development)
    OAuth (for production apps)
```

**4. GitHub Integration (Optional but Recommended)**
```
? Would you like to set up GitHub integration? (Y/n)
```
→ Say **Yes** to enable CI/CD workflows

**5. Portal Selection**
```
? Which HubSpot account would you like to use?
  ❯ Your Company (portal ID: 12345678)
    Add new account
```

## 📁 Developer Project Structure

After creation, you'll have:

```
justdata/
├── hubspot.config.yml          # HubSpot configuration
├── .husbpot/                   # HubSpot CLI cache
├── src/                        # Source code (if using templates)
└── public/                     # Public assets (if applicable)
```

### hubspot.config.yml Example

```yaml
name: justdata-hubspot
portalId: 12345678
auth:
  tokenInfo:
    accessToken: pat-na1-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    expiresAt: '2024-12-31T23:59:59.999Z'
```

## 🔗 GitHub Integration

### Benefits of GitHub Integration

1. **Automated Deployments**
   - Push to GitHub → Automatically deploy to HubSpot
   - No manual upload needed

2. **Version Control**
   - Track all changes
   - Easy rollbacks
   - Collaboration-friendly

3. **CI/CD Workflows**
   - Automated testing before deployment
   - Staging environments
   - Production safeguards

### Setting Up GitHub Integration

During project creation, choose "Yes" for GitHub integration. Then:

```bash
# Link your GitHub repository
npx hs project github-actions setup

# This will:
# 1. Create GitHub Actions workflows
# 2. Set up deployment secrets
# 3. Configure automatic deployments
```

## 🚢 Deploying Your Project

### Manual Deployment

```bash
# Deploy to HubSpot
npx hs project deploy

# Deploy to specific environment
npx hs project deploy --to=production
```

### Automated Deployment (with GitHub)

Once GitHub integration is set up:

```bash
# Simply push to your main branch
git add .
git commit -m "Update integration"
git push origin main

# GitHub Actions will automatically deploy to HubSpot
```

## 📝 Common Developer Project Commands

```bash
# Create new project
npx hs project create

# Deploy project
npx hs project deploy

# Upload specific files
npx hs project upload src/

# Watch for changes and auto-deploy
npx hs project watch

# View project status
npx hs project info

# List all projects
npx hs project list

# Setup GitHub Actions
npx hs project github-actions setup
```

## 🔄 Migrating from Legacy Apps

If you already started with `hs init`:

1. **Create a new developer project:**
   ```bash
   npx hs project create
   ```

2. **Copy your existing configuration:**
   - Your authentication will be preserved
   - Portal connections remain the same

3. **Use developer project commands going forward:**
   ```bash
   npx hs project deploy  # Instead of manual uploads
   ```

## 🎯 Best Practices for JustData Integration

### 1. Project Organization

```
justdata/
├── justdata/
│   └── apps/
│       └── hubspot/              # Python integration code
│           ├── client.py
│           ├── services.py
│           └── sync.py
├── hubspot.config.yml            # HubSpot CLI config
└── .github/
    └── workflows/
        └── hubspot-deploy.yml    # GitHub Actions (optional)
```

### 2. Environment Management

Keep separate HubSpot configurations for different environments:

```yaml
# hubspot.config.yml
environments:
  development:
    portalId: 12345678
  staging:
    portalId: 87654321
  production:
    portalId: 11223344
```

### 3. Deployment Strategy

```bash
# Development
npx hs project deploy --to=development

# Staging (test thoroughly)
npx hs project deploy --to=staging

# Production (after approval)
npx hs project deploy --to=production
```

### 4. Version Control

Add to `.gitignore`:
```
# HubSpot
hubspot.config.yml      # Contains sensitive tokens
.hubspot/               # CLI cache
```

Store sensitive values in environment variables:
```bash
HUBSPOT_ACCESS_TOKEN=xxx
HUBSPOT_PORTAL_ID=xxx
```

## 🔐 Security Considerations

### Never Commit Secrets

```bash
# Add to .gitignore
echo "hubspot.config.yml" >> .gitignore
echo ".hubspot/" >> .gitignore
```

### Use Environment Variables

In your Python code:
```python
import os
from apps.hubspot import HubSpotClient

# Read from environment
client = HubSpotClient(
    access_token=os.getenv("HUBSPOT_ACCESS_TOKEN")
)
```

In your `.env`:
```bash
HUBSPOT_ACCESS_TOKEN=pat-na1-xxxxx
HUBSPOT_PORTAL_ID=12345678
```

## 📚 Resources

### Official Documentation
- [HubSpot Developer Projects](https://developers.hubspot.com/docs/cms/developer-projects)
- [CLI Reference](https://developers.hubspot.com/docs/cms/guides/cli)
- [GitHub Integration](https://developers.hubspot.com/docs/cms/developer-projects/github-integration)

### CLI Help
```bash
npx hs project --help
npx hs project create --help
npx hs project deploy --help
```

### JustData Specific
- See `HUBSPOT_SETUP.md` for complete integration guide
- See `HUBSPOT_QUICKSTART.md` for quick commands
- API docs: http://localhost:8000/docs

## ✅ Quick Start Checklist

- [ ] Install HubSpot CLI: `npm install --save-dev @hubspot/cli`
- [ ] Create developer project: `npx hs project create`
- [ ] Choose "None" template (for API integration)
- [ ] Set up GitHub integration (optional)
- [ ] Get Private App access token from HubSpot
- [ ] Add to `.env`: `HUBSPOT_ACCESS_TOKEN=xxx`
- [ ] Test integration: `curl http://localhost:8000/api/v1/hubspot/test`
- [ ] Deploy updates: `npx hs project deploy`

## 🎉 You're Ready!

Developer projects give you:
- ✅ Modern, future-proof integration
- ✅ CI/CD workflows
- ✅ Easy deployments
- ✅ Better version control
- ✅ Peace of mind (no deprecation worries)

Start with: `npx hs project create`

---

**Remember**: Legacy apps are being deprecated. Always use `hs project create` for new integrations!

