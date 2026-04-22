# Setup Google Cloud Run

## Prerequisites

- Google Cloud account
- `gcloud` CLI installed locally
- Your GitHub repo already created

---

## Step 1 — Create GCP project and enable APIs

```bash
# Create project (skip if you already have one)
gcloud projects create quiz-ai-prod --name="Quiz AI"
gcloud config set project quiz-ai-prod

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com
```

---

## Step 2 — Create Artifact Registry repository

Cloud Run can only pull images from Google Artifact Registry, not GHCR directly.
The CI pipeline handles the retag + push automatically.

```bash
gcloud artifacts repositories create quiz-ai \
  --repository-format=docker \
  --location=europe-west1 \
  --description="Quiz AI Docker images"
```

---

## Step 3 — Create a PostgreSQL database

Use Cloud SQL (managed PostgreSQL):

```bash
gcloud sql instances create quiz-ai-db \
  --database-version=POSTGRES_15 \
  --region=europe-west1 \
  --tier=db-f1-micro \
  --storage-type=SSD \
  --storage-size=10GB

gcloud sql databases create quiz_ai --instance=quiz-ai-db
gcloud sql users create quiz_user \
  --instance=quiz-ai-db \
  --password=CHOOSE_A_STRONG_PASSWORD
```

Get the connection string:
```bash
gcloud sql instances describe quiz-ai-db --format="value(connectionName)"
# Output: quiz-ai-prod:europe-west1:quiz-ai-db
```

Your DATABASE_URL for Cloud Run:
```
postgresql+pg8000://quiz_user:PASSWORD@/quiz_ai?host=/cloudsql/quiz-ai-prod:europe-west1:quiz-ai-db
```

> Note: Cloud Run uses Cloud SQL Auth Proxy via Unix socket — the host is `/cloudsql/<connection-name>`.
> You'll need `pg8000` instead of `psycopg2` in this case, or use Cloud SQL Connector.
> Alternatively, use a public IP with SSL (simpler for getting started).

---

## Step 4 — Set up Workload Identity Federation (GitHub Actions auth)

This allows GitHub Actions to authenticate to GCP without storing a JSON key.

```bash
# Create a service account for the pipeline
gcloud iam service-accounts create github-actions-sa \
  --display-name="GitHub Actions Service Account"

SA_EMAIL="github-actions-sa@quiz-ai-prod.iam.gserviceaccount.com"

# Grant necessary permissions
gcloud projects add-iam-policy-binding quiz-ai-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding quiz-ai-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding quiz-ai-prod \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"

# Create the Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
  --location=global \
  --display-name="GitHub Actions Pool"

POOL_ID=$(gcloud iam workload-identity-pools describe github-pool \
  --location=global --format="value(name)")

# Create the provider
# Replace YOUR_GITHUB_ORG/YOUR_REPO with your actual repo
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='YOUR_GITHUB_ORG/YOUR_REPO'"

# Allow the GitHub repo to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL_ID}/attribute.repository/YOUR_GITHUB_ORG/YOUR_REPO"

# Get the provider resource name (needed for GitHub secret)
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-pool \
  --location=global \
  --format="value(name)"
```

---

## Step 5 — Add GitHub Secrets

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret.

| Secret name | Value |
|---|---|
| `GCP_PROJECT_ID` | `quiz-ai-prod` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Output of the last command in Step 4 |
| `GCP_SERVICE_ACCOUNT` | `github-actions-sa@quiz-ai-prod.iam.gserviceaccount.com` |
| `DATABASE_URL` | Your Cloud SQL connection string |
| `API_KEY` | Your chosen API key |

---

## Step 6 — Push to main and watch the pipeline

```bash
git add .
git commit -m "feat: dockerize and add CI/CD"
git push origin main
```

Go to GitHub Actions — you should see two workflows running in sequence:
1. **Build & Push to GHCR** — builds the Docker image and pushes to GHCR
2. **Deploy to Google Cloud Run** — pulls the image, retags to Artifact Registry, deploys

---

## Testing the deployed service

```bash
# Get your Cloud Run URL
gcloud run services describe quiz-ai-service \
  --region=europe-west1 \
  --format="value(status.url)"

# Health check
curl https://YOUR-URL.run.app/health

# Store a quiz result
curl -X POST https://YOUR-URL.run.app/ai/quiz/result \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "studentId": "s_501",
    "quizId": "q_99",
    "score": 55,
    "maxScore": 100,
    "timeSpentSeconds": 720,
    "totalQuizTimeSeconds": 600
  }'

# Get recommendations
curl https://YOUR-URL.run.app/ai/recommendations/s_501 \
  -H "x-api-key: YOUR_API_KEY"
```
