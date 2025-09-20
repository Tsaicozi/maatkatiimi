#!/bin/bash

# Agent Leader Deployment Script
# Deploys Agent Leader to cloud with monitoring and persistence

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="agent-leader"
DOCKER_REGISTRY="your-registry.com"  # Change this to your registry
IMAGE_TAG="latest"
ENVIRONMENT=${1:-"production"}

echo -e "${BLUE}🚀 Agent Leader Deployment Script${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}Image: ${DOCKER_REGISTRY}/${PROJECT_NAME}:${IMAGE_TAG}${NC}"

# Check if required files exist
check_requirements() {
    echo -e "${YELLOW}📋 Checking requirements...${NC}"
    
    if [ ! -f "agent_leader.py" ]; then
        echo -e "${RED}❌ agent_leader.py not found${NC}"
        exit 1
    fi
    
    if [ ! -f "Dockerfile.agent_leader" ]; then
        echo -e "${RED}❌ Dockerfile.agent_leader not found${NC}"
        exit 1
    fi
    
    if [ ! -f "docker-compose.agent_leader.yml" ]; then
        echo -e "${RED}❌ docker-compose.agent_leader.yml not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All required files found${NC}"
}

# Build Docker image
build_image() {
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
    
    docker build -f Dockerfile.agent_leader -t ${PROJECT_NAME}:${IMAGE_TAG} .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Docker image built successfully${NC}"
    else
        echo -e "${RED}❌ Docker image build failed${NC}"
        exit 1
    fi
}

# Tag image for registry
tag_image() {
    echo -e "${YELLOW}🏷️ Tagging image for registry...${NC}"
    
    docker tag ${PROJECT_NAME}:${IMAGE_TAG} ${DOCKER_REGISTRY}/${PROJECT_NAME}:${IMAGE_TAG}
    
    echo -e "${GREEN}✅ Image tagged successfully${NC}"
}

# Push to registry
push_image() {
    echo -e "${YELLOW}📤 Pushing image to registry...${NC}"
    
    docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:${IMAGE_TAG}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Image pushed successfully${NC}"
    else
        echo -e "${RED}❌ Image push failed${NC}"
        exit 1
    fi
}

# Create environment file
create_env_file() {
    echo -e "${YELLOW}📝 Creating environment file...${NC}"
    
    cat > .env.agent_leader << EOF
# Agent Leader Environment Configuration
TZ=Europe/Helsinki
PYTHONUNBUFFERED=1

# Telegram Configuration
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}

# Agent Leader Configuration
AGENT_LEADER_LOG_LEVEL=INFO
AGENT_LEADER_REPORT_INTERVAL=300
AGENT_LEADER_HEALTH_CHECK_INTERVAL=30

# Redis Configuration (if using)
REDIS_URL=redis://redis:6379/0

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
EOF
    
    echo -e "${GREEN}✅ Environment file created${NC}"
}

# Deploy with Docker Compose
deploy_compose() {
    echo -e "${YELLOW}🚀 Deploying with Docker Compose...${NC}"
    
    # Stop existing containers
    docker-compose -f docker-compose.agent_leader.yml down || true
    
    # Start new containers
    docker-compose -f docker-compose.agent_leader.yml --env-file .env.agent_leader up -d
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Deployment successful${NC}"
    else
        echo -e "${RED}❌ Deployment failed${NC}"
        exit 1
    fi
}

# Health check
health_check() {
    echo -e "${YELLOW}🏥 Performing health check...${NC}"
    
    # Wait for container to start
    sleep 10
    
    # Check if container is running
    if docker-compose -f docker-compose.agent_leader.yml ps | grep -q "Up"; then
        echo -e "${GREEN}✅ Agent Leader is running${NC}"
    else
        echo -e "${RED}❌ Agent Leader is not running${NC}"
        docker-compose -f docker-compose.agent_leader.yml logs agent-leader
        exit 1
    fi
    
    # Check logs for errors
    echo -e "${YELLOW}📋 Checking logs...${NC}"
    docker-compose -f docker-compose.agent_leader.yml logs --tail=20 agent-leader
}

# Show deployment info
show_info() {
    echo -e "${BLUE}📊 Deployment Information${NC}"
    echo -e "${BLUE}========================${NC}"
    echo -e "Project: ${PROJECT_NAME}"
    echo -e "Environment: ${ENVIRONMENT}"
    echo -e "Image: ${DOCKER_REGISTRY}/${PROJECT_NAME}:${IMAGE_TAG}"
    echo -e "Container: agent-leader"
    echo -e ""
    echo -e "${YELLOW}🔗 Useful Commands:${NC}"
    echo -e "View logs: docker-compose -f docker-compose.agent_leader.yml logs -f agent-leader"
    echo -e "Stop: docker-compose -f docker-compose.agent_leader.yml down"
    echo -e "Restart: docker-compose -f docker-compose.agent_leader.yml restart agent-leader"
    echo -e "Shell access: docker-compose -f docker-compose.agent_leader.yml exec agent-leader bash"
    echo -e ""
    echo -e "${YELLOW}📊 Monitoring URLs:${NC}"
    echo -e "Grafana: http://localhost:3000 (admin/admin123)"
    echo -e "Prometheus: http://localhost:9090"
    echo -e ""
    echo -e "${GREEN}🎉 Agent Leader deployed successfully!${NC}"
}

# Main deployment flow
main() {
    check_requirements
    build_image
    tag_image
    push_image
    create_env_file
    deploy_compose
    health_check
    show_info
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "build")
        check_requirements
        build_image
        ;;
    "push")
        tag_image
        push_image
        ;;
    "deploy-local")
        check_requirements
        build_image
        create_env_file
        deploy_compose
        health_check
        show_info
        ;;
    "stop")
        docker-compose -f docker-compose.agent_leader.yml down
        echo -e "${GREEN}✅ Agent Leader stopped${NC}"
        ;;
    "logs")
        docker-compose -f docker-compose.agent_leader.yml logs -f agent-leader
        ;;
    "status")
        docker-compose -f docker-compose.agent_leader.yml ps
        ;;
    *)
        echo -e "${YELLOW}Usage: $0 {deploy|build|push|deploy-local|stop|logs|status}${NC}"
        echo -e "${YELLOW}  deploy: Full deployment to cloud${NC}"
        echo -e "${YELLOW}  build: Build Docker image only${NC}"
        echo -e "${YELLOW}  push: Push image to registry${NC}"
        echo -e "${YELLOW}  deploy-local: Deploy locally for testing${NC}"
        echo -e "${YELLOW}  stop: Stop all containers${NC}"
        echo -e "${YELLOW}  logs: View logs${NC}"
        echo -e "${YELLOW}  status: Show container status${NC}"
        exit 1
        ;;
esac
