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

**v2.6.0**:

this value has been updated to:

```yaml
triggerAuth:
  triggerPodIdentityProvider: azure-workload
```


## Releases
We use semantic versioning via GitHub releases to handle new releases of this application chart, this is done via automation called Release Drafter. When you merge a PR to master, a new draft release will be created.
More information is available about the [release process and how to create draft releases for testing purposes in more depth](https://hmcts.github.io/ops-runbooks/Testing-Changes/drafting-a-release.html)


## Supported Scale Types

[ScaledJob](https://keda.sh/docs/1.4/concepts/scaling-jobs/).

[ScaledObject](https://keda.sh/docs/2.8/concepts/scaling-deployments/).

## Supported Scaling Strategies for ScaledJob

It currently supports the "default" or "accurate" scaling strategy, to use "accurate" set the following
``` yaml
scalingStrategy: accurate
```

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
### [Azure pipelines trigger](https://keda.sh/docs/2.9/scalers/azure-pipelines/#trigger-specification)
```helmyaml
triggers
  - type: azure-pipelines
      poolName: "{agentPoolName}"
      poolID: "{agentPoolId}"
      organizationURLFromEnv: "AZP_URL"
      targetPipelinesQueueLength: "1"
      activationTargetPipelinesQueueLength: "0"
```
### [Postgres trigger](https://keda.sh/docs/2.11/scalers/postgresql/)
```helmyaml
triggers
  - type: postgres
    connectionFromEnv: DB_CONNECTION_STRING
    query: "SELECT count(*) FROM queue WHERE status = 'NEW'"
    targetQueryValue: "1.1"
```

## Using Azure Triggers

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