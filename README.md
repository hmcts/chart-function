# chart-function

Basic helm chart for running functions using [KEDA.](https://keda.sh/)

## Breaking Changes

**v2.2.0**:
``` yaml
scaleType: Job | Object # must be specified due to now supporting ScaledJob & ScaledObject
```

the following value has adjusted:
```yaml
triggerPodIdentityProvider: Azure
```
becomes:
```yaml
triggerAuth:
  triggerPodIdentityProvider: Azure
```

## Supported Scale Types

[ScaledJob](https://keda.sh/docs/1.4/concepts/scaling-jobs/).

[ScaledObject](https://keda.sh/docs/2.8/concepts/scaling-deployments/).

## Supported Triggers

It currently supports below triggers:

### [Azure service bus trigger](https://keda.sh/docs/1.4/scalers/azure-service-bus/)
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
### [Azure blob storage trigger](https://keda.sh/docs/1.4/scalers/azure-storage-blob/)
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
### [HTTP trigger](https://dev.to/anirudhgarg_99/scale-up-and-down-a-http-triggered-function-app-in-kubernetes-using-keda-4m42)
```helmyaml
triggers
  - type: prometheus
    url: https://hmcts-funcapp.platform.hmcts.net:8080
    metricName: "access_frequency" # Default access_frequency
    threshold: "2" # Default 1
    requestsPer: "2m" # Default every 1 minute
```


## Pod Identity Auth

Supported for both Blob Storage Trigger & Service Bus Trigger.

Blob Storage Trigger - Supply the `accountName` value of the Storage Account which the Blob Store is in and leave the `connection` value empty.

Service Bus Trigger - Supply `serviceBusNamespace` value of the Service Bus namespace name, leave connection empty.

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
