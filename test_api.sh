#!/bin/bash
# Script de test rapide du backend

set -e

echo "🚀 DIRISI 2025 Backend - Quick Test Script"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8080"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_endpoint() {
    local endpoint=$1
    local method=${2:-GET}
    local data=${3:-}
    
    echo -n "Testing $method $endpoint... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $http_code)${NC}"
        return 1
    fi
}

# 1. Health check
echo "1️⃣  Health Check"
check_endpoint "/health"
echo ""

# 2. Ingest synthetic data
echo "2️⃣  Ingesting Synthetic Data"
ingest_data='{
  "seed": 42,
  "num_sites": 3,
  "nodes_per_site": 3,
  "duration_min": 120,
  "freq_min": 5,
  "incident_rate": 0.01
}'
check_endpoint "/v1/ingest" "POST" "$ingest_data"
echo ""

# 3. Get topology
echo "3️⃣  Get Topology"
check_endpoint "/v1/topology"
echo ""

# 4. Predict
echo "4️⃣  Predict Risks"
predict_data='{
  "horizon_min": 30,
  "targets": [
    {"node_id": "N0"},
    {"node_id": "N1"},
    {"link_id": "L0"}
  ]
}'
check_endpoint "/v1/predict" "POST" "$predict_data"
echo ""

# 5. Generate plan
echo "5️⃣  Generate Plan"
plan_data='{
  "objectives": ["minimize_risk", "preserve_critical_flows"],
  "constraints": {"max_latency_ms": 50, "reserve_pct": 20},
  "context": {
    "impacted": ["N1", "L0"],
    "critical_flows": ["FLOW_CRIT_1"]
  }
}'
check_endpoint "/v1/plan" "POST" "$plan_data"
echo ""

# 6. Simulate scenario
echo "6️⃣  Simulate Scenario"
simulate_data='{
  "scenario": "Test scenario: N0 failure",
  "failures": ["N0"],
  "variations": {"L0": 0.90}
}'
check_endpoint "/v1/simulate" "POST" "$simulate_data"
echo ""

# 7. Explain prediction
echo "7️⃣  Explain Prediction"
check_endpoint "/v1/explain?entity_id=N0" "POST"
echo ""

# 8. Get metrics
echo "8️⃣  Get Prometheus Metrics"
check_endpoint "/v1/metrics"
echo ""

echo "=========================================="
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "📚 For more details, visit: $BASE_URL/docs"
