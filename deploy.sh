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

# Create/update .python_packages directory
echo "🔧 Creating local .python_packages directory to help Oryx build system..."
mkdir -p .python_packages/lib/site-packages

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

# First, configure build settings before deploying package
echo "🔧 Setting build configuration to ensure Oryx properly installs dependencies..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
  "ENABLE_ORYX_BUILD=true" \
  "SCM_DO_BUILD_DURING_DEPLOYMENT=1" \
  "PYTHON_ENABLE_WORKER_EXTENSIONS=1" \
  "ENABLE_ORYX=true" \
  "ORYX_SDK_STORAGE_BASE_URL=https://oryx-cdn.microsoft.io"

# Wait a moment for settings to take effect
echo "⏳ Waiting for settings to apply..."
sleep 5

echo "🔧 Setting core environment variables..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
  "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING" \
  "KEY_VAULT_NAME=$KEY_VAULT" \
  "FUNCTIONS_WORKER_RUNTIME=python" \
  "FUNCTIONS_EXTENSION_VERSION=~4" 

echo "🔧 Setting Linux runtime to Python 3.11..."
az functionapp config set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --linux-fx-version "Python|3.11"

# Now deploy the package after all settings are configured
echo "🚀 Deploying function package with Oryx build enabled..."
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
  "WEBSITE_RUN_FROM_PACKAGE=$ZIP_URL"

echo "⏳ Waiting for deployment to complete..."
sleep 30

echo "🔄 Restarting function app to apply all changes..."
az functionapp restart \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

echo "⏳ Waiting for restart to complete..."
sleep 20

echo "✅ Deployment complete!"
echo ""
echo "You can test your function with:"
echo "https://$FUNCTION_APP.azurewebsites.net/api/HttpTriggerScraper?scraper=auto_sales"
echo ""
echo "📝 If the function still fails to import dependencies, check the function logs in the portal."
echo "   You can also consider creating a 'requirements.psd1' file to explicitly manage Python dependencies:"
echo ""
echo "# Example requirements.psd1 content:"
echo "@{"
echo "    'pandas' = '1.5.3'"
echo "    'numpy' = '1.24.4'"
echo "    'requests' = '*'"
echo "    'openpyxl' = '*'"
echo "    'azure-storage-blob' = '*'"
echo "    'azure-data-tables' = '*'"
echo "    'xlrd' = '>=2.0.1'"
echo "}"