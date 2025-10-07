#!/bin/bash

echo "Deleting existing camunda-custom container..."
docker rm -f camunda-custom
sleep 5

echo "Starting camunda-custom container..."
docker run -d -p 8080:8080 --name camunda-custom camunda-custom:7.20.0
sleep 10

echo "Deploying approval workflow..."
curl -u demo:demo -F "deployment-name=approval-deployment" -F "deploy-changed-only=true" -F "approval.bpmn=@approval_generated.bpmn" http://localhost:8080/engine-rest/deployment/create
sleep 3

echo "Deploying rsa workflow..."
curl -u demo:demo -F "deployment-name=rsa-deployment" -F "deploy-changed-only=true" -F "rsa.bpmn=@rsa_generated.bpmn" http://localhost:8080/engine-rest/deployment/create
sleep 3

echo "Deploying main workflow..."
curl -u demo:demo -F "deployment-name=main-deployment" -F "deploy-changed-only=true" -F "main.bpmn=@main_generated.bpmn" http://localhost:8080/engine-rest/deployment/create
