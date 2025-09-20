#!/bin/bash

# Integrated Agent Leader Deployment Script
# Deploys the integrated Agent Leader with Hybrid Agent

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_NAME="integrated-agent-leader"
DOCKER_REGISTRY="your-registry.com"
IMAGE_TAG="latest"
ENVIRONMENT=${1:-"production"}

echo -e "${BLUE}🚀 Integrated Agent Leader Deployment${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"

# Check requirements
check_requirements() {
    echo -e "${YELLOW}📋 Checking requirements...${NC}"
    
    required_files=(
        "integrated_agent_leader.py"
        "hybrid_agent.py"
        "agent_leader.py"
        "Dockerfile.agent_leader"
        "docker-compose.integrated.yml"
        ".env.agent_leader"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo -e "${RED}❌ $file not found${NC}"
            exit 1
        fi
    done
    
    echo -e "${GREEN}✅ All required files found${NC}"
}

# Build and deploy
deploy_local() {
    echo -e "${YELLOW}🐳 Building and deploying locally...${NC}"
    
    # Build image
    docker build -f Dockerfile.agent_leader -t ${PROJECT_NAME}:${IMAGE_TAG} .
    
    # Stop existing containers
    docker-compose -f docker-compose.integrated.yml down || true
    
    # Start new containers
    docker-compose -f docker-compose.integrated.yml --env-file .env.agent_leader up -d
    
    echo -e "${GREEN}✅ Local deployment successful${NC}"
}

# Health check
health_check() {
    echo -e "${YELLOW}🏥 Performing health check...${NC}"
    
    sleep 10
    
    if docker-compose -f docker-compose.integrated.yml ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Integrated Agent Leader is running${NC}"
    else
        echo -e "${RED}❌ Integrated Agent Leader is not running${NC}"
        docker-compose -f docker-compose.integrated.yml logs integrated-agent-leader
        exit 1
    fi
}

# Show info
show_info() {
    echo -e "${BLUE}📊 Integrated Agent Leader Information${NC}"
    echo -e "${BLUE}=====================================${NC}"
    echo -e "Project: ${PROJECT_NAME}"
    echo -e "Environment: ${ENVIRONMENT}"
    echo -e ""
    echo -e "${YELLOW}🔗 Useful Commands:${NC}"
    echo -e "View logs: docker-compose -f docker-compose.integrated.yml logs -f integrated-agent-leader"
    echo -e "Stop: docker-compose -f docker-compose.integrated.yml down"
    echo -e "Restart: docker-compose -f docker-compose.integrated.yml restart integrated-agent-leader"
    echo -e "Shell: docker-compose -f docker-compose.integrated.yml exec integrated-agent-leader bash"
    echo -e ""
    echo -e "${YELLOW}📊 Monitoring URLs:${NC}"
    echo -e "Grafana: http://localhost:3000 (admin/admin123)"
    echo -e "Prometheus: http://localhost:9090"
    echo -e ""
    echo -e "${GREEN}🎉 Integrated Agent Leader deployed!${NC}"
}

# Main deployment
main() {
    check_requirements
    deploy_local
    health_check
    show_info
}

# Handle arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        docker-compose -f docker-compose.integrated.yml down
        echo -e "${GREEN}✅ Integrated Agent Leader stopped${NC}"
        ;;
    "logs")
        docker-compose -f docker-compose.integrated.yml logs -f integrated-agent-leader
        ;;
    "status")
        docker-compose -f docker-compose.integrated.yml ps
        ;;
    "restart")
        docker-compose -f docker-compose.integrated.yml restart integrated-agent-leader
        echo -e "${GREEN}✅ Integrated Agent Leader restarted${NC}"
        ;;
    *)
        echo -e "${YELLOW}Usage: $0 {deploy|stop|logs|status|restart}${NC}"
        exit 1
        ;;
esac
