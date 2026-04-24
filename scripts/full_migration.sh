#!/bin/bash

./scripts/migrate.sh tf-aws-module_primitive-api_gateway_v2_api
./scripts/migrate.sh tf-aws-module_primitive-iam_role
./scripts/migrate.sh tf-aws-module_primitive-lambda_layer
./scripts/migrate.sh tf-aws-module_primitive-route53_record
./scripts/migrate.sh tf-aws-module_primitive-route53_zone
./scripts/migrate.sh tf-aws-module_primitive-sqs_queue
./scripts/migrate.sh tf-azurerm-module_primitive-container_registry
./scripts/migrate.sh tf-azurerm-module_primitive-dns_zone
# ./scripts/migrate.sh tf-azurerm-module_primitive-iothub
./scripts/migrate.sh tf-azurerm-module_primitive-key_vault
./scripts/migrate.sh tf-azurerm-module_primitive-route_table
./scripts/migrate.sh tf-azurerm-module_primitive-resource_group
./scripts/migrate.sh tf-azurerm-module_primitive-storage_account
