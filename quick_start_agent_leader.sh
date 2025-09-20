#!/bin/bash

# Agent Leader Quick Start Script
# Nopea käynnistys Agent Leaderille

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Agent Leader Quick Start${NC}"
echo -e "${BLUE}==========================${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

# Check if required files exist
if [ ! -f "agent_leader.py" ]; then
    echo -e "${RED}❌ agent_leader.py not found${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Available options:${NC}"
echo -e "1. Demo mode (30 seconds test)"
echo -e "2. Local development mode"
echo -e "3. Docker mode (if Docker is available)"
echo -e "4. Show help"
echo ""

read -p "Select option (1-4): " choice

case $choice in
    1)
        echo -e "${GREEN}🎭 Starting demo mode...${NC}"
        python3 agent_leader.py demo
        ;;
    2)
        echo -e "${GREEN}🔧 Starting local development mode...${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        python3 agent_leader.py
        ;;
    3)
        if command -v docker &> /dev/null; then
            echo -e "${GREEN}🐳 Starting Docker mode...${NC}"
            
            # Check if docker-compose is available
            if command -v docker-compose &> /dev/null; then
                echo -e "${YELLOW}Using docker-compose...${NC}"
                docker-compose -f docker-compose.agent_leader.yml up
            else
                echo -e "${YELLOW}Using docker run...${NC}"
                docker build -f Dockerfile.agent_leader -t agent-leader .
                docker run -it --rm agent-leader
            fi
        else
            echo -e "${RED}❌ Docker not found. Please install Docker or use option 1 or 2${NC}"
            exit 1
        fi
        ;;
    4)
        echo -e "${BLUE}📚 Agent Leader Help${NC}"
        echo -e "${BLUE}==================${NC}"
        echo ""
        echo -e "${YELLOW}Files created:${NC}"
        echo -e "• agent_leader.py - Main Agent Leader implementation"
        echo -e "• Dockerfile.agent_leader - Docker container definition"
        echo -e "• docker-compose.agent_leader.yml - Multi-service setup"
        echo -e "• deploy_agent_leader.sh - Deployment script"
        echo -e "• agent_leader_config.yaml - Configuration file"
        echo -e "• monitoring/ - Prometheus & Grafana configs"
        echo ""
        echo -e "${YELLOW}Quick commands:${NC}"
        echo -e "• Demo: python3 agent_leader.py demo"
        echo -e "• Run: python3 agent_leader.py"
        echo -e "• Deploy: ./deploy_agent_leader.sh deploy-local"
        echo -e "• Stop: ./deploy_agent_leader.sh stop"
        echo -e "• Logs: ./deploy_agent_leader.sh logs"
        echo ""
        echo -e "${YELLOW}Configuration:${NC}"
        echo -e "• Copy env_agent_leader_example.txt to .env.agent_leader"
        echo -e "• Edit agent_leader_config.yaml for settings"
        echo -e "• Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
        echo ""
        echo -e "${YELLOW}Monitoring:${NC}"
        echo -e "• Grafana: http://localhost:3000 (admin/admin123)"
        echo -e "• Prometheus: http://localhost:9090"
        echo -e "• Metrics: http://localhost:8080/metrics"
        echo ""
        echo -e "${GREEN}📖 Full documentation: AGENT_LEADER_README.md${NC}"
        ;;
    *)
        echo -e "${RED}❌ Invalid option. Please select 1-4${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}✅ Done!${NC}"
