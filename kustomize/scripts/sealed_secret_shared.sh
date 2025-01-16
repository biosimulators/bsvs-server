#!/usr/bin/env bash

# This script is used to create a sealed secret for the s3 storeage
# this script should take 3 arguments as input:
#   namespace
#   storage_access_key_id
#   storage_secret
#
#   and outputs a sealed secret to stdout
# Example: ./sealed_secret_shared.sh remote GOOG1EONabcZEI 0WWTDgbabdbAkcL > output.yaml

# validate the number of arguments
if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters"
    echo "Usage: ./sealed_secret_shared.sh <namespace> <storage_access_key_id> <storage_secret>"
    exit 1
fi

SECRET_NAME="shared-secrets"
NAMESPACE=$1
STORAGE_ACCESS_KEY_ID=$2
STORAGE_SECRET=$3

kubectl create secret generic ${SECRET_NAME} --dry-run=client \
      --from-literal=STORAGE_ACCESS_KEY_ID="${STORAGE_ACCESS_KEY_ID}" \
      --from-literal=STORAGE_SECRET="${STORAGE_SECRET}" \
     --namespace="${NAMESPACE}" -o yaml | kubeseal --format yaml
