#!/bin/bash

set -e

# Load environment variables from .env file
if [ -f .env ]; then
  echo "📂 Loading configuration from .env file..."
  export $(grep -v '^#' .env | xargs)
else
  echo "⚠️ No .env file found, will use default values or fail if required variables are missing."
fi

# === CONFIGURATION ===
# Use environment variables with defaults where appropriate
RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-pr-opendata-rg}"
FUNCTION_APP="${AZURE_FUNCTION_APP:-pr-opendata-collector}"
STORAGE_ACCOUNT="${AZURE_STORAGE_ACCOUNT:-propendata}"
CONTAINER_NAME="${AZURE_FUNCTION_CONTAINER:-function-packages}"
ZIP_NAME="${AZURE_FUNCTION_ZIP:-project.zip}"
SUBSCRIPTION_ID="${AZURE_SUBSCRIPTION_ID}"
KEY_VAULT="${AZURE_KEY_VAULT:-pr-opendata-kv}"

# Validate required variables
if [ -z "$SUBSCRIPTION_ID" ]; then
  echo "❌ AZURE_SUBSCRIPTION_ID is required in .env file or environment"
  exit 1
fi

# Get storage key securely using Azure CLI
echo "🔑 Retrieving storage account key..."
STORAGE_KEY=$(az storage account keys list \
  --resource-group $RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT \
  --query '[0].value' \
  -o tsv)

if [ -z "$STORAGE_KEY" ]; then
  echo "❌ Failed to retrieve storage account key. Make sure you're logged in with az login and have proper permissions."
  exit 1
fi

echo "🔄 Cleaning up previous zip..."
rm -f $ZIP_NAME

echo "📦 Zipping project..."
zip -r $ZIP_NAME . \
  -x "*.pyc" "*__pycache__*" "*.git*" ".vscode/*" ".venv/*" \
     "run_locally.py" "test_ac.py" "deploymentstructure.md" \
     "local.settings.json" ".env" ".gitignore" "$ZIP_NAME" \
     "local_processed/*" "local_raw/*" ".DS_Store"

echo "☁️ Uploading to blob storage..."
az storage blob upload \
  --account-name $STORAGE_ACCOUNT \
  --account-key "$STORAGE_KEY" \
  --container-name $CONTAINER_NAME \
  --name $ZIP_NAME \
  --file $ZIP_NAME \
  --overwrite

echo "🔐 Generating SAS token..."
# Cross-platform date generation (works on both macOS and Linux)
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS date command
  EXPIRY=$(date -u -v+1d '+%Y-%m-%dT%H:%MZ')
else
  # Linux date command
  EXPIRY=$(date -u -d "tomorrow" '+%Y-%m-%dT%H:%MZ')
fi

SAS=$(az storage blob generate-sas \
  --account-name $STORAGE_ACCOUNT \
  --account-key "$STORAGE_KEY" \
  --container-name $CONTAINER_NAME \
  --name $ZIP_NAME \
  --permissions r \
  --expiry $EXPIRY \
  --output tsv)

ZIP_URL="https://${STORAGE_ACCOUNT}.blob.core.windows.net/${CONTAINER_NAME}/${ZIP_NAME}?${SAS}"

# Get the storage connection string for environment variables
echo "🔧 Getting storage connection string..."
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString \
  --output tsv)

echo "🔧 Setting required environment variables..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
  "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING" \
  "KEY_VAULT_NAME=$KEY_VAULT" \
  "WEBSITE_RUN_FROM_PACKAGE=$ZIP_URL" \
  "SCM_DO_BUILD_DURING_DEPLOYMENT=true" \
  "FUNCTIONS_WORKER_RUNTIME=python" \
  "FUNCTIONS_EXTENSION_VERSION=~4"

echo "🔧 Setting Linux runtime to Python 3.11..."
az functionapp config set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --linux-fx-version "Python|3.11"

echo "🔄 Restarting function app..."
az functionapp restart \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

echo "✅ Deployment complete!"