# chart-function

Basic helm chart for running functions using [KEDA](https://keda.sh/)

## supported scale types

It currently supports only [scaling jobs](https://keda.sh/docs/1.4/concepts/scaling-jobs/).

## Supported triggers

It currently supports only 
1. [Azure service bus trigger](https://keda.sh/docs/1.4/scalers/azure-service-bus/)
1. [Azure blob storage trigger](https://keda.sh/docs/1.4/scalers/azure-storage-blob/)

## Pod Identity Auth

Currently only supported by the Blob Storage Trigger. Simply supply the `accountName` value of the Storage Account which 
the Blob Store is in and leave the `connection` value empty.
