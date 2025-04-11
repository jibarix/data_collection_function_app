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
LOCATION="${AZURE_LOCATION:-eastus}"
APP_INSIGHTS="${AZURE_APP_INSIGHTS:-pr-opendata-collector}"
APP_SERVICE_PLAN="${AZURE_APP_SERVICE_PLAN:-EastUSLinuxDynamicPlan}"
KEY_VAULT="${AZURE_KEY_VAULT:-pr-opendata-kv}"

echo "🔄 Deleting existing Function App and related resources..."

# Delete the Function App
echo "🗑️ Deleting Function App: $FUNCTION_APP"
az functionapp delete \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

# Delete Application Insights
echo "🗑️ Deleting Application Insights: $APP_INSIGHTS"
az monitor app-insights component delete \
  --app $APP_INSIGHTS \
  --resource-group $RESOURCE_GROUP

# We'll keep the App Service Plan as it might be used by other functions
echo "ℹ️ Keeping App Service Plan: $APP_SERVICE_PLAN for potential reuse"

# Sleep to allow Azure to fully process the deletions
echo "⏳ Waiting for deletion to complete..."
sleep 10

# Create new Application Insights
echo "🔧 Creating new Application Insights: $APP_INSIGHTS"
az monitor app-insights component create \
  --app $APP_INSIGHTS \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --application-type web

# Get the instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app $APP_INSIGHTS \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

# Create new Function App
echo "🔧 Creating new Function App: $FUNCTION_APP"
az functionapp create \
  --name $FUNCTION_APP \
  --storage-account $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --consumption-plan-location $LOCATION \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --disable-app-insights false \
  --app-insights $APP_INSIGHTS \
  --os-type Linux

# Add CORS configuration for the Azure Portal
echo "🌐 Configuring CORS settings for portal testing..."
az functionapp cors add \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --allowed-origins "https://portal.azure.com" "https://functions.azure.com"

# Configure network access - allow from Azure Portal
echo "🔌 Configuring network access to allow Azure Portal..."
az functionapp config access-restriction add \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --rule-name "AllowAzurePortal" \
  --action Allow \
  --priority 100 \
  --service-tag AzureCloud

# Configure the Function App settings
echo "🔧 Configuring Function App settings..."

# Get the storage connection string to set as an app setting
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
  --name $STORAGE_ACCOUNT \
  --resource-group $RESOURCE_GROUP \
  --query connectionString \
  --output tsv)

# Set application settings
az functionapp config appsettings set \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --settings \
  "AZURE_STORAGE_CONNECTION_STRING=$STORAGE_CONNECTION_STRING" \
  "KEY_VAULT_NAME=$KEY_VAULT" \
  "APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY" \
  "FUNCTIONS_EXTENSION_VERSION=~4" \
  "FUNCTIONS_WORKER_RUNTIME=python" \
  "WEBSITE_MOUNT_ENABLED=1" \
  "SCM_DO_BUILD_DURING_DEPLOYMENT=1" \
  "ENABLE_ORYX_BUILD=true"

# Enable managed identity for the function app
echo "🔐 Enabling system-assigned managed identity for Function App..."
az functionapp identity assign \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP

# Get the principal ID of the function app's managed identity
PRINCIPAL_ID=$(az functionapp identity show \
  --name $FUNCTION_APP \
  --resource-group $RESOURCE_GROUP \
  --query principalId \
  --output tsv)

# Set Key Vault access policy for the function app
echo "🔑 Setting Key Vault access policy for Function App's managed identity..."
az keyvault set-policy \
  --name $KEY_VAULT \
  --resource-group $RESOURCE_GROUP \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get list

echo "✅ Function App recreation complete! Ready for deployment."