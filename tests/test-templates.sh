#!/usr/bin/env bash

set -e

# Vendor the chart-library dependency (required for the hmcts.* templates used by
# function/templates/secretproviderclass.yaml to resolve during rendering/tests).
helm dependency build function/
helm lint function/ --values ci-values-servicebus.yaml
helm unittest --help

# Unit tests: verify conditional rendering paths (ScaledJob vs ScaledObject, trigger
# metadata per trigger type, TriggerAuthentication gating) and structural rules.
# ci-values-minimal.yaml supplies only the required image field so each test's
# `set:` values are the sole driver — preventing chart defaults from silently
# satisfying a condition under test.
helm unittest --values function/ci-values-minimal.yaml function -q -f 'tests/unit-tests/*.yaml'

