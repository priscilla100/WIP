#!/bin/bash

# Project Launch Script
# Makes it easy to launch individual projects or all at once

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to launch a project
launch_project() {
    local name=$1
    local path=$2
    local port=$3
    
    echo -e "${BLUE}Launching $name on port $port...${NC}"
    
    cd "$path"
    
    # Check if virtual environment exists
    if [ -d "myenv" ]; then
        echo -e "${GREEN}Activating virtual environment...${NC}"
        source myenv/bin/activate
    fi
    
    # Check if port is already in use
    if check_port $port; then
        echo -e "${RED}Warning: Port $port is already in use!${NC}"
        echo -e "${RED}$name may already be running or another service is using this port.${NC}"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    streamlit run streamlit_app.py --server.port $port &
    
    sleep 2
    echo -e "${GREEN}$name launched! Access at http://localhost:$port${NC}"
    echo ""
    
    cd "$SCRIPT_DIR"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: ./launch.sh [option]

Options:
    dashboard    Launch only the dashboard (default: port 8501)
    nl2ltl       Launch NL2LTL Phase 2 (port 8502)
    protocol     Launch Protocol Formalization (port 8503)
    regulatory   Launch Regulatory Policy Checker (port 8504)
    all          Launch all projects including dashboard
    help         Show this help message

Examples:
    ./launch.sh dashboard       # Launch just the dashboard
    ./launch.sh nl2ltl          # Launch just NL2LTL project
    ./launch.sh all             # Launch everything

EOF
}

# Main script logic
case "${1:-dashboard}" in
    dashboard)
        echo -e "${BLUE}Starting Project Dashboard...${NC}"
        streamlit run main_app.py
        ;;
    
    nl2ltl)
        launch_project "NL2LTL Phase 2" "$SCRIPT_DIR/NL2LTL_PHASE2" 8502
        echo -e "${GREEN}Press Ctrl+C to stop${NC}"
        wait
        ;;
    
    protocol)
        launch_project "Protocol Formalization" "$SCRIPT_DIR/PROTOCOL_FORMALIZATION" 8503
        echo -e "${GREEN}Press Ctrl+C to stop${NC}"
        wait
        ;;
    
    regulatory)
        launch_project "Regulatory Policy Checker" "$SCRIPT_DIR/REGULATORY_POLICY_CHECKER" 8504
        echo -e "${GREEN}Press Ctrl+C to stop${NC}"
        wait
        ;;
    
    all)
        echo -e "${BLUE}Launching all projects...${NC}"
        echo ""
        
        # Launch dashboard
        echo -e "${BLUE}Starting Dashboard...${NC}"
        streamlit run main_app.py --server.port 8501 &
        sleep 3
        
        # Launch all projects
        launch_project "NL2LTL Phase 2" "$SCRIPT_DIR/NL2LTL_PHASE2" 8502
        launch_project "Protocol Formalization" "$SCRIPT_DIR/PROTOCOL_FORMALIZATION" 8503
        launch_project "Regulatory Policy Checker" "$SCRIPT_DIR/REGULATORY_POLICY_CHECKER" 8504
        
        echo ""
        echo -e "${GREEN}All projects launched!${NC}"
        echo -e "${GREEN}=======================${NC}"
        echo -e "Dashboard:    http://localhost:8501"
        echo -e "NL2LTL:       http://localhost:8502"
        echo -e "Protocol:     http://localhost:8503"
        echo -e "Regulatory:   http://localhost:8504"
        echo ""
        echo -e "${BLUE}Press Ctrl+C to stop all services${NC}"
        
        # Wait for all background processes
        wait
        ;;
    
    help|--help|-h)
        show_usage
        ;;
    
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac
