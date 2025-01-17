#!/usr/bin/env bash

# This script is used to create a sealed secret for the s3 storage
# this script should take 3 arguments as input:
#   namespace
#   storage_access_key_id
#   storage_secret
#   and an optional --cert <filename.pem> argument to specify the certificate file for kubeseal
# Example: ./sealed_secret_shared.sh [--cert <filename.pem>] <namespace> <storage_access_key_id> <storage_secret> > output.yaml

# note that for GKE, the cert file is needed and can be extracted by running:
# kubeseal --fetch-cert > filename.pem
# or
# kubectl get secret -n kube-system -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
#     | grep tls.crt | awk '{print $2}' | base64 --decode > filename.pem

# Initialize variables
CERT_ARG=""

# Parse optional arguments
while [[ "$1" == --* ]]; do
  case "$1" in
    --cert)
      CERT_ARG="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate the number of positional arguments
if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters"
    echo "Usage: ./sealed_secret_shared.sh [--cert <filename.pem>] <namespace> <storage_access_key_id> <storage_secret>"
    exit 1
fi

SECRET_NAME="shared-secrets"
NAMESPACE=$1
STORAGE_ACCESS_KEY_ID=$2
STORAGE_SECRET=$3

# Create the generic secret and seal it
kubectl create secret generic ${SECRET_NAME} --dry-run=client \
      --from-literal=STORAGE_ACCESS_KEY_ID="${STORAGE_ACCESS_KEY_ID}" \
      --from-literal=STORAGE_SECRET="${STORAGE_SECRET}" \
      --namespace="${NAMESPACE}" -o yaml | kubeseal --format yaml ${CERT_ARG:+--cert=$CERT_ARG}