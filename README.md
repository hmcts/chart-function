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

## Testing

Unit tests are written using [helm-unittest](https://github.com/helm-unittest/helm-unittest) and live under
`function/tests/unit-tests/`. They assert conditional rendering paths (ScaledJob vs ScaledObject, per-trigger
metadata fields, TriggerAuthentication gating, etc.) without needing a live Kubernetes cluster.

Run the full suite locally with:

```bash
./tests/test-templates.sh
```

This script:
1. Vendors the `library` chart dependency (`helm dependency build function/`) — required since
   `function/templates/secretproviderclass.yaml` delegates to `hmcts.*` named templates defined in
   `chart-library`.
2. Runs `helm lint function/ --values ci-values-servicebus.yaml`.
3. Runs `helm unittest --values function/ci-values-minimal.yaml function -f 'tests/unit-tests/*.yaml'`.
   `ci-values-minimal.yaml` supplies only the chart's one required field (`image`) so each test's own
   `set:` block is the sole driver of the values under test — this prevents chart defaults from silently
   satisfying a condition a test is meant to be verifying.

Prerequisites:
```bash
brew install helm
helm plugin install https://github.com/helm-unittest/helm-unittest.git
```

Pulling the `library` OCI dependency from `hmctsprod.azurecr.io` requires an authenticated Helm registry
session. If `helm dependency build` fails with a `401 Unauthorized`, log in first:
```bash
az acr login --name hmctsprod --expose-token --output tsv --query accessToken \
  | helm registry login hmctsprod.azurecr.io \
      --username 00000000-0000-0000-0000-000000000000 \
      --password-stdin
```

In CI (`azure-pipelines.yaml`), each `Validate*` job (`ValidateServiceBus`, `ValidateBlob`, `ValidateMixed`,
`ValidateAzuredevopstrigger`, `ValidatePostgrestrigger`) also runs its matching `tests/unit-tests/*_test.yaml`
file (via the shared `steps/charts/validate.yaml@cnp-azuredevops-libraries` template's `runUnitTests` /
`unitTestFile` parameters) in addition to a real `helm install`/`helm test` against a live cluster, using the
corresponding `ci-values-*.yaml` scenario at the repo root.

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
