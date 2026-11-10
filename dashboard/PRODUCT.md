# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Yash checks his single-node K3s homelab, opens its applications, and investigates resource pressure and unavailable services.

## Product Purpose

A private application and monitoring dashboard at dashboard.yashbhangale.site, backed by maintained open-source projects and real cluster metrics.

## Operating Context

Homepage 2.7.0 provides the existing interface; Gatus 5.38.0 records endpoint checks. The existing Prometheus, node exporter, metrics-server and Grafana provide resource data. Cloudflare Tunnel exposes authenticated pages.

## Capabilities and Constraints

Show app health, pod resource usage, CPU, memory, storage, network, power, temperature, and active alerts. Retain uptime history. Use a separate generated dashboard login, as requested. Preserve running homelab applications and the host session. Kubernetes access is read-only and excludes Secrets. Existing applications keep their own authentication. No outgoing alert messages or notification destinations are configured.

## Brand Commitments

Use Homepage's established interface with a dark theme, as presented to the user. Preserve native responsive components and navigation.
