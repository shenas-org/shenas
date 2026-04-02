#!/usr/bin/env bash
# Set up GCP IAM + Workload Identity Federation for GitHub Actions.
#
# Run once before the first deployment. Creates:
#   - Service account for GitHub Actions
#   - Workload Identity Pool + Provider (OIDC)
#   - IAM bindings
#
# Prerequisites:
#   - gcloud CLI installed and authenticated as project owner
#   - gh CLI installed and authenticated
#
# Usage:
#   bash deploy/setup-iam.sh
set -euo pipefail

PROJECT="${PROJECT:-shenas-491609}"
REGION="${REGION:-us-east4}"
GITHUB_REPO="afuncke/shenas"
SA_NAME="github-deploy"
SA_EMAIL="${SA_NAME}@${PROJECT}.iam.gserviceaccount.com"
POOL_NAME="github-pool"
PROVIDER_NAME="github-provider"

echo "Project:     $PROJECT"
echo "GitHub repo: $GITHUB_REPO"
echo "SA:          $SA_EMAIL"
echo ""

# 1. Enable required APIs
echo "Enabling IAM APIs..."
gcloud services enable \
    iam.googleapis.com \
    iamcredentials.googleapis.com \
    sts.googleapis.com \
    --project="$PROJECT"

# 2. Create service account
echo "Creating service account..."
gcloud iam service-accounts create "$SA_NAME" \
    --display-name="GitHub Actions deploy" \
    --project="$PROJECT" 2>/dev/null || echo "  (already exists)"

# 3. Grant IAM roles
echo "Granting IAM roles..."
for role in \
    roles/artifactregistry.writer \
    roles/container.developer \
    roles/iam.serviceAccountUser; do
    gcloud projects add-iam-policy-binding "$PROJECT" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        --condition=None \
        --quiet
    echo "  $role"
done

# 4. Create Workload Identity Pool
echo "Creating Workload Identity Pool..."
gcloud iam workload-identity-pools create "$POOL_NAME" \
    --location="global" \
    --display-name="GitHub Actions" \
    --project="$PROJECT" 2>/dev/null || echo "  (already exists)"

# 5. Create Workload Identity Provider (OIDC for GitHub)
echo "Creating Workload Identity Provider..."
gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_NAME" \
    --location="global" \
    --workload-identity-pool="$POOL_NAME" \
    --display-name="GitHub" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository=='${GITHUB_REPO}'" \
    --project="$PROJECT" 2>/dev/null || echo "  (already exists)"

# 6. Allow GitHub repo to impersonate the service account
echo "Binding workload identity to service account..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT" --format="value(projectNumber)")
MEMBER="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --role="roles/iam.workloadIdentityUser" \
    --member="$MEMBER" \
    --project="$PROJECT" \
    --quiet

# 7. Get the provider resource name
WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/providers/${PROVIDER_NAME}"

echo ""
echo "============================================================"
echo "Setup complete!"
echo "============================================================"
echo ""
echo "Add these as GitHub repository variables:"
echo ""
echo "  GCP_WORKLOAD_IDENTITY_PROVIDER: ${WIF_PROVIDER}"
echo "  GCP_SERVICE_ACCOUNT: ${SA_EMAIL}"
echo ""

# 8. Optionally set them automatically via gh CLI
if command -v gh > /dev/null 2>&1; then
    read -p "Set these as GitHub variables now? [y/N] " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIF_PROVIDER"
        gh variable set GCP_SERVICE_ACCOUNT --body "$SA_EMAIL"
        echo "GitHub variables set."
    fi
fi
