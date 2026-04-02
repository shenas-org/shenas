#!/usr/bin/env bash
# Set up a GKE cluster and deploy shenas services.
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker installed
#   - kubectl installed
#   - IAM setup complete: bash deploy/setup-iam.sh
#
# Usage:
#   bash deploy/setup-gke.sh                    # interactive setup
#   PROJECT=my-project REGION=us-east4 bash deploy/setup-gke.sh  # non-interactive
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Configuration
PROJECT="${PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-east4}"
ZONE="${ZONE:-${REGION}-a}"
CLUSTER_NAME="${CLUSTER_NAME:-shenas}"
REPO_NAME="shenas"

if [ -z "$PROJECT" ]; then
    echo "No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Project:  $PROJECT"
echo "Region:   $REGION"
echo "Cluster:  $CLUSTER_NAME"
echo ""

# 1. Enable required APIs
echo "Enabling GCP APIs..."
gcloud services enable \
    container.googleapis.com \
    artifactregistry.googleapis.com \
    --project="$PROJECT"

# 2. Create Artifact Registry repository for Docker images
echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create "$REPO_NAME" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT" \
    --description="Shenas container images" 2>/dev/null || echo "  (already exists)"

# 3. Create GKE Autopilot cluster (managed, pay-per-pod)
echo "Creating GKE Autopilot cluster..."
gcloud container clusters create-auto "$CLUSTER_NAME" \
    --region="$REGION" \
    --project="$PROJECT" 2>/dev/null || echo "  (already exists)"

# 4. Get cluster credentials
echo "Getting cluster credentials..."
gcloud container clusters get-credentials "$CLUSTER_NAME" \
    --region="$REGION" \
    --project="$PROJECT"

# 5. Reserve a static IP for the ingress
echo "Reserving static IP..."
gcloud compute addresses create shenas-ip \
    --global \
    --project="$PROJECT" 2>/dev/null || echo "  (already exists)"

IP=$(gcloud compute addresses describe shenas-ip --global --project="$PROJECT" --format="value(address)")
echo "  Static IP: $IP"

# 6. Configure Docker auth for Artifact Registry
echo "Configuring Docker auth..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# 7. Build and push images
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT}/${REPO_NAME}"

echo "Building repo-server image..."
docker build -t "${REGISTRY}/repo-server:latest" -f deploy/docker/Dockerfile.repo-server .
docker push "${REGISTRY}/repo-server:latest"

echo "Building fl-server image..."
docker build -t "${REGISTRY}/fl-server:latest" -f deploy/docker/Dockerfile.fl-server .
docker push "${REGISTRY}/fl-server:latest"

# 8. Update manifests with actual project/region
echo "Applying Kubernetes manifests..."
for f in deploy/k8s/*.yaml; do
    sed "s|REGION|${REGION}|g; s|PROJECT_ID|${PROJECT}|g" "$f" | kubectl apply -f -
done

# 9. Wait for deployment
echo ""
echo "Waiting for deployments..."
kubectl rollout status deployment/repo-server -n shenas --timeout=120s
kubectl rollout status deployment/fl-server -n shenas --timeout=120s

echo ""
echo "Deployment complete!"
echo ""
echo "Services:"
kubectl get services -n shenas
echo ""
echo "Ingress (may take 5-10 min for TLS provisioning):"
kubectl get ingress -n shenas
echo ""
echo "Static IP: $IP"
echo "Point your DNS:"
echo "  repo.shenas.dev -> $IP"
echo "  fl.shenas.dev   -> $IP"
