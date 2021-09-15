# chart-function

Basic helm chart for running functions using [KEDA](https://keda.sh/)

## Supported scale types

It currently supports only [scaling jobs](https://keda.sh/docs/2.4/concepts/scaling-jobs/).

## Supported triggers

It currently supports below triggers
### [Azure service bus trigger](https://keda.sh/docs/2.4/scalers/azure-service-bus/)
```helmyaml
triggers
  - type: azure-servicebus 
    # Required: queueName OR topicName and subscriptionName
    queueName:
    topicName:
    subscriptionName:
    connection: # This must be a connection string for a queue itself, and not a namespace level (e.g. RootAccessPolicy) connection string [#215](https://github.com/kedacore/keda/issues/215)
    queueLength: 1
```
### [Azure blob storage trigger](https://keda.sh/docs/2.4/scalers/azure-storage-blob/)
```helmyaml
triggers
  - type: azure-blob
    # Required: blobContainerName and accountName (when using pod identity) or connection
    blobContainerName:
    accountName: ""
    connection: ""
    blobCount: 1
    blobPrefix: ""
    blobDelimiter: "/"
```

## Pod Identity Auth

Currently only supported by the Blob Storage Trigger. Simply supply the `accountName` value of the Storage Account which 
the Blob Store is in and leave the `connection` value empty.

If multiple services need to reference the same Trigger Auth for some reason, use the `nameOverride` value like this:
```helmyaml
values:
  function:
    triggerAuth:
      create: false
      enabled: true
      nameOverride: "azure-mi-auth{{ .Values.something-dynamic-even }}"
...
```

## Upgrading from 0.x.x
Since version `1.0.0`, the chart now supports multiple triggers of different types and as such, the `Values` need to be 
supplied as a list instead of a single object.

Example of `0.x.x` `Values`
```helmyaml
values:
  function:
    trigger:
      type: azure-blob
      blob:
        blobContainerName: "new"
        accountName: "rpesendletterdemo"
```

Since `1.0.0`
```helmyaml
values:
  function:
    triggerAuth:
      enabled: true
    triggers:
      - type: azure-blob
        blobContainerName: "new"
        accountName: "rpesendletterdemo"
```
