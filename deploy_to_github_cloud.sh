#!/bin/bash

# Deploy Agent Leader to GitHub Cloud
# Tämä scripti automaattistaa GitHub Actions -deploymentin

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}☁️ Agent Leader GitHub Cloud Deployment${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if git is available
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git not found. Please install git.${NC}"
    exit 1
fi

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Not in a git repository. Please run from project root.${NC}"
    exit 1
fi

# Check if GitHub remote is configured
if ! git remote get-url origin | grep -q "github.com"; then
    echo -e "${RED}❌ GitHub remote not configured. Please add GitHub remote:${NC}"
    echo -e "${YELLOW}git remote add origin https://github.com/username/repository.git${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Pre-deployment checks...${NC}"

# Check required files
required_files=(
    "cloud_agent_leader.py"
    "agent_leader.py"
    "github_agent.py"
    "hybrid_agent.py"
    ".github/workflows/agent-leader-cloud.yml"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Required file not found: $file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All required files found${NC}"

# Check if there are uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}📝 Uncommitted changes detected. Committing...${NC}"
    
    git add .
    git commit -m "Deploy Agent Leader to GitHub cloud

- Added Cloud Agent Leader for multi-agent management
- Added GitHub Agent for Actions monitoring  
- Added GitHub Actions workflows for deployment
- Integrated Telegram notifications
- Added comprehensive monitoring and logging

Agents managed:
- Hybrid Trading Agent (token scanning)
- GitHub Agent (workflow monitoring)
- Future: Discord, Slack, Email agents

Features:
- Real-time Telegram notifications
- GitHub Actions health monitoring
- Multi-repository support
- Auto-scaling capabilities
- Comprehensive logging"
    
    echo -e "${GREEN}✅ Changes committed${NC}"
else
    echo -e "${GREEN}✅ No uncommitted changes${NC}"
fi

# Push to GitHub
echo -e "${YELLOW}🚀 Pushing to GitHub...${NC}"

if git push origin main; then
    echo -e "${GREEN}✅ Successfully pushed to GitHub${NC}"
else
    echo -e "${RED}❌ Failed to push to GitHub${NC}"
    exit 1
fi

# Show deployment info
echo -e "${BLUE}📊 Deployment Information${NC}"
echo -e "${BLUE}========================${NC}"
echo -e "Repository: $(git remote get-url origin)"
echo -e "Branch: main"
echo -e "Commit: $(git rev-parse HEAD)"
echo -e ""

echo -e "${YELLOW}🔗 Next Steps:${NC}"
echo -e "1. Go to GitHub Actions: $(git remote get-url origin | sed 's/\.git$//')/actions"
echo -e "2. Check 'Agent Leader Cloud Deployment' workflow"
echo -e "3. Monitor deployment progress"
echo -e "4. Check Telegram for notifications"
echo -e ""

echo -e "${YELLOW}📱 Telegram Notifications:${NC}"
echo -e "Bot Token: 8468877865:AAFrap3-U3fv2vacVI_yhXm6-hCHbB7SX54"
echo -e "Chat ID: 7939379291"
echo -e ""

echo -e "${YELLOW}🤖 Agents Deployed:${NC}"
echo -e "• Hybrid Trading Agent (token scanning)"
echo -e "• GitHub Agent (workflow monitoring)"
echo -e "• Future: Discord, Slack, Email agents"
echo -e ""

echo -e "${YELLOW}📊 Monitoring:${NC}"
echo -e "• GitHub Actions: Real-time workflow monitoring"
echo -e "• Telegram: Instant alerts and reports"
echo -e "• Logs: Comprehensive logging and error tracking"
echo -e ""

echo -e "${GREEN}🎉 Agent Leader deployed to GitHub cloud!${NC}"
echo -e "${GREEN}📈 Your agents are now being monitored and managed in the cloud!${NC}"

# Optional: Open GitHub Actions in browser
if command -v open &> /dev/null; then
    echo -e "${YELLOW}🌐 Opening GitHub Actions in browser...${NC}"
    open "$(git remote get-url origin | sed 's/\.git$//')/actions"
elif command -v xdg-open &> /dev/null; then
    echo -e "${YELLOW}🌐 Opening GitHub Actions in browser...${NC}"
    xdg-open "$(git remote get-url origin | sed 's/\.git$//')/actions"
fi
