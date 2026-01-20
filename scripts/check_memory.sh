#!/bin/bash
# Memory monitoring script for PrimeData development
# Monitors Docker/Podman container memory usage and system memory
# Supports macOS and Linux platforms
# Requires: bash, bc (calculator), docker or podman
# Usage: ./scripts/check_memory.sh

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📊 Memory Usage Monitor${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if Docker or Podman is running
CONTAINER_RUNTIME=""
if command -v docker > /dev/null 2>&1 && docker info > /dev/null 2>&1; then
    CONTAINER_RUNTIME="docker"
elif command -v podman > /dev/null 2>&1 && podman info > /dev/null 2>&1; then
    CONTAINER_RUNTIME="podman"
else
    echo -e "${RED}❌ Neither Docker nor Podman is running${NC}"
    exit 1
fi

# Docker container memory usage
echo -e "${GREEN}🐳 Container Memory Usage (${CONTAINER_RUNTIME})${NC}"
echo ""

# Check if containers exist (works for both Docker and Podman)
if $CONTAINER_RUNTIME ps --format "{{.Names}}" 2>/dev/null | grep -q "aird-"; then
    $CONTAINER_RUNTIME stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}" \
        $($CONTAINER_RUNTIME ps --format "{{.Names}}" 2>/dev/null | grep "aird-") 2>/dev/null || true
    
    echo ""
    
    # Calculate total container memory
    TOTAL_CONTAINER_MEM=$($CONTAINER_RUNTIME stats --no-stream --format "{{.MemUsage}}" \
        $($CONTAINER_RUNTIME ps --format "{{.Names}}" 2>/dev/null | grep "aird-") 2>/dev/null | \
        awk '{split($1, arr, /[A-Za-z]/); sum += arr[1]} END {print sum}')
    
    if [ ! -z "$TOTAL_CONTAINER_MEM" ]; then
        TOTAL_CONTAINER_MEM_MB=$(echo "$TOTAL_CONTAINER_MEM" | awk '{printf "%.0f", $1}')
        echo -e "${BLUE}Total Container Memory Usage (${CONTAINER_RUNTIME}): ~${TOTAL_CONTAINER_MEM_MB}MB${NC}"
        
        # Warning thresholds
        if (( $(echo "$TOTAL_CONTAINER_MEM_MB > 6000" | bc -l) )); then
            echo -e "${RED}⚠️  WARNING: Container memory usage is high (>6GB). Consider using test-only services.${NC}"
        elif (( $(echo "$TOTAL_CONTAINER_MEM_MB > 4000" | bc -l) )); then
            echo -e "${YELLOW}⚠️  WARNING: Container memory usage is moderate (>4GB). Monitor system memory.${NC}"
        fi
    fi
else
    echo -e "${YELLOW}No PrimeData containers are running${NC}"
    echo -e "${YELLOW}Start services with: make services${NC}"
    echo -e "${YELLOW}Or test services with: make test-services${NC}"
fi

echo ""
echo -e "${GREEN}💻 System Memory${NC}"
echo ""

# Detect platform and get memory info
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS system memory info
    # Get total memory
    TOTAL_MEM=$(sysctl -n hw.memsize)
    TOTAL_MEM_GB=$(echo "scale=2; $TOTAL_MEM / 1024 / 1024 / 1024" | bc)
    
    # Get memory pressure using vm_stat
    VM_STAT=$(vm_stat)
    FREE_PAGES=$(echo "$VM_STAT" | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
    INACTIVE_PAGES=$(echo "$VM_STAT" | grep "Pages inactive" | awk '{print $3}' | sed 's/\.//')
    ACTIVE_PAGES=$(echo "$VM_STAT" | grep "Pages active" | awk '{print $3}' | sed 's/\.//')
    WIRED_PAGES=$(echo "$VM_STAT" | grep "Pages wired down" | awk '{print $4}' | sed 's/\.//')
    
    # Calculate page size (usually 4096 bytes on macOS)
    PAGE_SIZE=$(pagesize)
    
    # Calculate memory in MB
    FREE_MB=$(echo "scale=2; $FREE_PAGES * $PAGE_SIZE / 1024 / 1024" | bc)
    INACTIVE_MB=$(echo "scale=2; $INACTIVE_PAGES * $PAGE_SIZE / 1024 / 1024" | bc)
    ACTIVE_MB=$(echo "scale=2; $ACTIVE_PAGES * $PAGE_SIZE / 1024 / 1024" | bc)
    WIRED_MB=$(echo "scale=2; $WIRED_PAGES * $PAGE_SIZE / 1024 / 1024" | bc)
    USED_MB=$(echo "scale=2; $ACTIVE_MB + $WIRED_MB" | bc)
    AVAILABLE_MB=$(echo "scale=2; $FREE_MB + $INACTIVE_MB" | bc)
    TOTAL_MB=$(echo "scale=2; $USED_MB + $AVAILABLE_MB" | bc)
    
    # Calculate percentages
    USED_PERCENT=$(echo "scale=1; ($USED_MB / $TOTAL_MB) * 100" | bc)
    AVAILABLE_PERCENT=$(echo "scale=1; ($AVAILABLE_MB / $TOTAL_MB) * 100" | bc)
    
    echo "Platform: macOS"
    echo "Total Memory: ${TOTAL_MEM_GB} GB"
    echo "Used (Active + Wired): $(printf "%.1f" $USED_MB) MB ($(printf "%.1f" $USED_PERCENT)%)"
    echo "Available (Free + Inactive): $(printf "%.1f" $AVAILABLE_MB) MB ($(printf "%.1f" $AVAILABLE_PERCENT)%)"
    echo ""
    
    # Check memory pressure
    if command -v memory_pressure > /dev/null 2>&1; then
        echo "Memory Pressure:"
        memory_pressure 2>/dev/null | head -5 || echo "Unable to check"
        echo ""
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux"* ]]; then
    # Linux system memory info using /proc/meminfo
    if [ -f /proc/meminfo ]; then
        # Read memory information from /proc/meminfo
        MEM_TOTAL=$(grep "^MemTotal:" /proc/meminfo | awk '{print $2}')
        MEM_FREE=$(grep "^MemFree:" /proc/meminfo | awk '{print $2}')
        MEM_AVAILABLE=$(grep "^MemAvailable:" /proc/meminfo | awk '{print $2}' || echo "$MEM_FREE")
        MEM_BUFFERS=$(grep "^Buffers:" /proc/meminfo | awk '{print $2}' || echo "0")
        MEM_CACHED=$(grep "^Cached:" /proc/meminfo | awk '{print $2}' || echo "0")
        
        # Convert from KB to MB and GB
        TOTAL_MEM_KB=$MEM_TOTAL
        TOTAL_MEM_MB=$(echo "scale=2; $TOTAL_MEM_KB / 1024" | bc)
        TOTAL_MEM_GB=$(echo "scale=2; $TOTAL_MEM_KB / 1024 / 1024" | bc)
        
        # Calculate available memory (use MemAvailable if available, otherwise MemFree + Buffers + Cached)
        if [ -n "$MEM_AVAILABLE" ] && [ "$MEM_AVAILABLE" != "0" ]; then
            AVAILABLE_KB=$MEM_AVAILABLE
        else
            AVAILABLE_KB=$(echo "$MEM_FREE + $MEM_BUFFERS + $MEM_CACHED" | bc)
        fi
        
        AVAILABLE_MB=$(echo "scale=2; $AVAILABLE_KB / 1024" | bc)
        USED_KB=$(echo "$TOTAL_MEM_KB - $AVAILABLE_KB" | bc)
        USED_MB=$(echo "scale=2; $USED_KB / 1024" | bc)
        
        # Calculate percentages
        USED_PERCENT=$(echo "scale=1; ($USED_KB * 100) / $TOTAL_MEM_KB" | bc)
        AVAILABLE_PERCENT=$(echo "scale=1; ($AVAILABLE_KB * 100) / $TOTAL_MEM_KB" | bc)
        
        echo "Platform: Linux"
        echo "Total Memory: ${TOTAL_MEM_GB} GB"
        echo "Used: $(printf "%.1f" $USED_MB) MB ($(printf "%.1f" $USED_PERCENT)%)"
        echo "Available: $(printf "%.1f" $AVAILABLE_MB) MB ($(printf "%.1f" $AVAILABLE_PERCENT)%)"
        echo ""
        
        # Check swap usage
        SWAP_TOTAL=$(grep "^SwapTotal:" /proc/meminfo | awk '{print $2}' || echo "0")
        SWAP_FREE=$(grep "^SwapFree:" /proc/meminfo | awk '{print $2}' || echo "0")
        if [ "$SWAP_TOTAL" != "0" ]; then
            SWAP_USED=$(echo "$SWAP_TOTAL - $SWAP_FREE" | bc)
            SWAP_USED_MB=$(echo "scale=2; $SWAP_USED / 1024" | bc)
            SWAP_TOTAL_MB=$(echo "scale=2; $SWAP_TOTAL / 1024" | bc)
            if (( $(echo "$SWAP_USED > 0" | bc -l) )); then
                echo "Swap Used: $(printf "%.1f" $SWAP_USED_MB) MB / $(printf "%.1f" $SWAP_TOTAL_MB) MB"
                echo ""
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  /proc/meminfo not available - cannot read memory information${NC}"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠️  Platform not fully supported for memory monitoring${NC}"
    echo "Detected OS: $OSTYPE"
    echo "Memory monitoring is available for macOS and Linux only."
    echo ""
fi

# Warnings (common for both platforms)
if [ -n "$USED_PERCENT" ] && [ -n "$USED_MB" ] && [ -n "$AVAILABLE_MB" ]; then
    if (( $(echo "$USED_PERCENT > 85" | bc -l) )); then
        echo -e "${RED}⚠️  CRITICAL: System memory usage is very high (>85%). Close applications or reduce Docker memory limits.${NC}"
    elif (( $(echo "$USED_PERCENT > 75" | bc -l) )); then
        echo -e "${YELLOW}⚠️  WARNING: System memory usage is high (>75%). Consider using test-only services.${NC}"
    elif (( $(echo "$AVAILABLE_MB < 2000" | bc -l) )); then
        echo -e "${YELLOW}⚠️  WARNING: Less than 2GB available memory. System may swap.${NC}"
    else
        echo -e "${GREEN}✅ System memory usage is within acceptable limits${NC}"
    fi
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}💡 Recommendations for 8GB Systems:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "1. Use test-only services for testing:"
echo "   ${GREEN}make test-services${NC}"
echo ""
echo "2. Use OpenAI API embeddings (saves ~500MB-1GB):"
echo "   Set ${GREEN}OPENAI_API_KEY${NC} and ${GREEN}USE_OPENAI_EMBEDDINGS=true${NC}"
echo ""
echo "3. Stop unnecessary containers:"
echo "   ${GREEN}make stop${NC}"
echo ""
echo "4. Close other memory-intensive applications"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
