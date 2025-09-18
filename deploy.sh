#!/bin/bash

# Deribit Webhook Python - Deployment Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="deribit-webhook-python"
DOCKER_IMAGE="$APP_NAME:latest"
CONTAINER_NAME="$APP_NAME-container"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    log_success "Requirements check passed"
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create necessary directories
    mkdir -p config data logs
    
    # Copy configuration files if they don't exist
    if [ ! -f ".env" ]; then
        if [ "$1" = "production" ]; then
            cp .env.production .env
            log_info "Copied production environment configuration"
        else
            cp .env.example .env
            log_info "Copied example environment configuration"
        fi
        log_warning "Please review and update .env file with your settings"
    fi
    
    if [ ! -f "config/apikeys.yml" ]; then
        if [ -f "../deribit_webhook/config/apikeys.example.yml" ]; then
            cp ../deribit_webhook/config/apikeys.example.yml config/apikeys.yml
            log_info "Copied API keys configuration template"
            log_warning "Please update config/apikeys.yml with your API keys"
        else
            log_warning "API keys configuration not found. Please create config/apikeys.yml"
        fi
    fi
    
    log_success "Environment setup completed"
}

build_image() {
    log_info "Building Docker image..."
    
    docker build -t $DOCKER_IMAGE .
    
    log_success "Docker image built successfully"
}

deploy_standalone() {
    log_info "Deploying standalone container..."
    
    # Stop existing container if running
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        log_info "Stopping existing container..."
        docker stop $CONTAINER_NAME
        docker rm $CONTAINER_NAME
    fi
    
    # Run new container
    docker run -d \
        --name $CONTAINER_NAME \
        -p 3001:3001 \
        -v $(pwd)/config:/app/config:ro \
        -v $(pwd)/data:/app/data \
        -v $(pwd)/logs:/app/logs \
        --restart unless-stopped \
        $DOCKER_IMAGE
    
    log_success "Container deployed successfully"
}

deploy_compose() {
    log_info "Deploying with Docker Compose..."
    
    docker-compose down
    docker-compose up -d --build
    
    log_success "Docker Compose deployment completed"
}

deploy_compose_with_proxy() {
    log_info "Deploying with Docker Compose and Nginx proxy..."
    
    docker-compose --profile with-proxy down
    docker-compose --profile with-proxy up -d --build
    
    log_success "Docker Compose deployment with proxy completed"
}

check_health() {
    log_info "Checking application health..."
    
    # Wait for application to start
    sleep 10
    
    # Check health endpoint
    if curl -f http://localhost:3000/health > /dev/null 2>&1; then
        log_success "Application is healthy"
    else
        log_error "Application health check failed"
        return 1
    fi
}

show_status() {
    log_info "Application status:"
    
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        echo "Container Status: Running"
        echo "Container ID: $(docker ps -q -f name=$CONTAINER_NAME)"
        echo "Port Mapping: $(docker port $CONTAINER_NAME 2>/dev/null || echo 'Not available')"
    else
        echo "Container Status: Not running"
    fi
    
    echo ""
    echo "Useful commands:"
    echo "  View logs: docker logs $CONTAINER_NAME"
    echo "  Follow logs: docker logs -f $CONTAINER_NAME"
    echo "  Stop container: docker stop $CONTAINER_NAME"
    echo "  Restart container: docker restart $CONTAINER_NAME"
    echo "  Access dashboard: http://localhost:3001"
    echo "  API documentation: http://localhost:3001/docs"
}

show_help() {
    echo "Deribit Webhook Python - Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  setup [env]     Setup environment (env: production|development)"
    echo "  build           Build Docker image"
    echo "  deploy          Deploy standalone container"
    echo "  compose         Deploy with Docker Compose"
    echo "  compose-proxy   Deploy with Docker Compose and Nginx proxy"
    echo "  status          Show application status"
    echo "  logs            Show application logs"
    echo "  stop            Stop the application"
    echo "  restart         Restart the application"
    echo "  clean           Clean up containers and images"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 setup production"
    echo "  $0 build"
    echo "  $0 deploy"
    echo "  $0 compose"
}

# Main script logic
case "$1" in
    "setup")
        check_requirements
        setup_environment $2
        ;;
    "build")
        check_requirements
        build_image
        ;;
    "deploy")
        check_requirements
        build_image
        deploy_standalone
        check_health
        show_status
        ;;
    "compose")
        check_requirements
        deploy_compose
        check_health
        show_status
        ;;
    "compose-proxy")
        check_requirements
        deploy_compose_with_proxy
        check_health
        show_status
        ;;
    "status")
        show_status
        ;;
    "logs")
        docker logs -f $CONTAINER_NAME
        ;;
    "stop")
        log_info "Stopping application..."
        docker-compose down 2>/dev/null || docker stop $CONTAINER_NAME 2>/dev/null || true
        log_success "Application stopped"
        ;;
    "restart")
        log_info "Restarting application..."
        docker restart $CONTAINER_NAME
        log_success "Application restarted"
        ;;
    "clean")
        log_info "Cleaning up..."
        docker-compose down --rmi all --volumes --remove-orphans 2>/dev/null || true
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
        docker rmi $DOCKER_IMAGE 2>/dev/null || true
        log_success "Cleanup completed"
        ;;
    "help"|"--help"|"-h"|"")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
