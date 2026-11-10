# Monitoring an app

For an app deployed into its own namespaces, from this repo or another (Flux applies
both). Most of it needs nothing from the app; the rest is a few resources it ships next
to its workloads. All of it shows in Grafana (`grafana.andrewmccall.com`), and alerts on
the Home dashboard and in Alertmanager.

| Signal | What the app does | Where it shows |
|---|---|---|
| Pod logs | Nothing: write to stdout/stderr | Loki |
| Pods, CPU, memory, restarts, volumes | Nothing | Kubernetes dashboards, chart alerts |
| Gateway traffic (requests, status codes, latency per route) | Nothing: use an HTTPRoute | Envoy dashboards and access logs |
| Postgres (CloudNativePG) | Nothing | CloudNativePG dashboard, `Postgres*` alerts |
| App metrics | A ServiceMonitor/PodMonitor, or OTLP to the collector | Prometheus |
| Traces | OTLP to the collector | Tempo (Grafana Explore) |
| Dashboards | A ConfigMap | Grafana, in its own folder |
| Alerts | A PrometheusRule | Home dashboard, Alertmanager |

## What comes for free

**Logs.** Vector ships every container's stdout/stderr to Loki with the labels
`namespace`, `pod`, `container`, `app` (`app.kubernetes.io/name`), `instance` and `node`.
Log JSON and it can be filtered by field:

```logql
{namespace="my-app"} |= "error"
{namespace="my-app", container="server"} | json | level="ERROR"
```

**Pods and Kubernetes.** kube-state-metrics, the kubelet and node-exporter cover every
namespace. The **Kubernetes** dashboards ("Compute Resources / Namespace (Pods)",
"Networking / Namespace (Pods)", "Persistent Volumes") take the namespace as a variable.
The chart's alerts already fire for crash loops, pods not ready, OOM kills, failed Jobs
and volumes filling up, with the namespace in the alert.

**Gateway traffic.** Every route on the `internal` and `external` Gateways is measured by
Envoy (`apps/networking/envoy-gateway/monitoring.yaml`). A route's backend is the Envoy
cluster `httproute/<namespace>/<route>/rule/<index>`:

```promql
# Requests per second by status class for one route
sum by (envoy_response_code_class) (
  rate(envoy_cluster_upstream_rq_xx{envoy_cluster_name=~"httproute/my-app/my-route/.*"}[5m]))
# p95 upstream latency
histogram_quantile(0.95, sum by (le) (
  rate(envoy_cluster_upstream_rq_time_bucket{envoy_cluster_name=~"httproute/my-app/.*"}[5m])))
```

The **Envoy Clusters** dashboard picks a route by namespace and name. Every request is
also an access log line in Loki, with the route, upstream, status, timing and the
client address:

```logql
{namespace="networking", container="envoy"} | json | route_name=~"httproute/my-app/.*" | response_code >= 500
```

**Postgres.** Every CloudNativePG instance, in any namespace, is scraped
(`core/cloudnative-pg/postgres-podmonitor.yaml`): no `spec.monitoring` on the Cluster is
needed. The **CloudNativePG** dashboard selects namespace and cluster; `PostgresDown`,
`PostgresConnectionsHigh`, `PostgresTransactionIDAgeHigh`, `PostgresWALArchivingFailing`
and `PostgresMetricsCollectionErrors` (`alerts/postgres-rules.yaml`) apply to every one.

## What the app adds

### Metrics from its own endpoint

Serve Prometheus text on a named port and ship a ServiceMonitor (or PodMonitor) next to
the workload. Prometheus picks up monitors in any namespace; no labels are needed.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: server
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: server      # labels on the Service
  endpoints:
    - port: metrics                       # a named port on the Service
      interval: 60s
```

### OpenTelemetry (traces, metrics, logs)

The collector in `monitoring` accepts OTLP and routes each signal:

| Signal | Goes to | Find it in Grafana |
|---|---|---|
| Traces | Tempo | Explore, datasource Tempo; search by `service.name` |
| Metrics | Prometheus, prefixed `otel_` | Any Prometheus query; `job` is the `service.name` |
| Logs | Loki | `{service_name="<service.name>"}` |

Endpoints from inside the cluster (no TLS):

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.monitoring.svc.cluster.andrewmccall.com:4318   # HTTP
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector.monitoring.svc.cluster.andrewmccall.com:4317   # gRPC
OTEL_SERVICE_NAME=server
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=prod,service.namespace=my-app
```

From the LAN (a dev machine), gRPC over TLS: `https://otel.andrewmccall.com:443`. Not
public. The cluster DNS domain is `cluster.andrewmccall.com`; a `.cluster.local` address
does not resolve.

### Dashboards

A ConfigMap labelled `grafana_dashboard: "1"`, in any of the app's namespaces, with a
`grafana_folder` annotation; see [README.md, Dashboards](README.md#dashboards). Export from
the Grafana UI and commit the JSON; UI edits do not persist.

### Alerts

A PrometheusRule in the app's namespace. Give each rule `severity: critical` (people rely
on it and it is down) or `warning`, and a `summary`. A warning or critical alert holds the
Monday k3s upgrade until it clears (`cluster/README.md#updates-and-maintenance-windows`),
so alert on what needs fixing, not on what is merely interesting.

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: my-app
spec:
  groups:
    - name: my-app
      rules:
        - alert: MyAppErrorsHigh
          expr: |
            sum(rate(envoy_cluster_upstream_rq_xx{envoy_cluster_name=~"httproute/my-app/.*", envoy_response_code_class="5"}[5m]))
              / sum(rate(envoy_cluster_upstream_rq_total{envoy_cluster_name=~"httproute/my-app/.*"}[5m])) > 0.05
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "More than 5% of my-app's requests are failing"
```

## NetworkPolicies

A namespace with a default-deny ingress policy must let Prometheus in to scrape
(`namespace: monitoring`, `app.kubernetes.io/name: prometheus`, to the metrics port), and
one restricting egress must allow the OTLP ports to the collector. Logs, Gateway traffic,
Kubernetes and Postgres metrics need no policy changes: they are collected from outside
the pod (CloudNativePG instances excepted, which Prometheus scrapes on 9187).
