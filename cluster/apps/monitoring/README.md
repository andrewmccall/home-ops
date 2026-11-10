# Monitoring

Prometheus, Alertmanager and Grafana (kube-prometheus-stack plus the Grafana chart),
Loki for logs, and a Vector agent that ships pod and journal logs to Loki. Check the
live stack with `python3 scripts/verify-monitoring.py`.

**Monitoring an app** (logs, metrics, traces, dashboards and alerts for something
deployed from this or another repository): [APPS.md](APPS.md).

| Piece | Where | Notes |
|---|---|---|
| Prometheus, Alertmanager, node and kube-state metrics | `kube-prometheus-stack/` | No Thanos; 30 days, 10 GB retention. |
| Grafana | `grafana/` | Datasources and dashboards come from git; UI edits do not persist. |
| Loki | `loki/` | Single binary, filesystem storage, 30 days. |
| Vector agent | `vector/agent/` | DaemonSet writing straight to Loki. Skips Loki's and its own pods. |
| mqtt-exporter | `mqtt-exporter/` | Zigbee2MQTT device state from MQTT, independent of Home Assistant. |
| Alert rules and routing | `alerts/` | |
| OpenTelemetry collector, Tempo | `otel-collector/`, `tempo/` | OTLP in; traces to Tempo, metrics to Prometheus (`otel_`), logs to Loki ([APPS.md](APPS.md)). |
| Postgres (CloudNativePG) | `cluster/core/cloudnative-pg/` | Every instance in any namespace is scraped; dashboard and `alerts/postgres-rules.yaml`. |
| Envoy Gateway | `cluster/apps/networking/envoy-gateway/monitoring.yaml` | Proxy and controller metrics, per route; Envoy dashboards. |

## Dashboards

The Grafana sidecar loads every ConfigMap labelled `grafana_dashboard: "1"`, in **any
namespace**, into the folder named by its `grafana_folder` annotation. Grafana's
own home page is `Home` (`grafana/dashboards/home/home.json`).

Build or change a dashboard in the Grafana UI, export it as JSON (Share → Export,
with "Export for sharing externally" **off**), and commit the JSON. Saved UI
changes to a provisioned dashboard are lost on restart.

Reference datasources by these UIDs, which Grafana derives from the datasource names:

| Datasource | UID |
|---|---|
| Prometheus | `PBFA97CFB590B2093` |
| Loki | `P8E80F9AEF21F6940` |

### In this repo

Put the JSON under `grafana/dashboards/<folder>/` and list it in
`grafana/kustomization.yaml`: add the file to that folder's `configMapGenerator`
entry, or add a new entry with its own `grafana_folder` annotation. The generator
turns off Flux variable substitution, which would otherwise eat Grafana's and
PromQL's `$` syntax.

### From another repo (e.g. ashes / andrewmccall/survival)

Ship a ConfigMap from that repo's own Flux path, in any of its namespaces:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ashes-dashboard
  namespace: ashes-prod
  labels:
    grafana_dashboard: "1"
  annotations:
    grafana_folder: Ashes
data:
  ashes.json: |
    { ...exported dashboard JSON... }
```

A kustomize `configMapGenerator` with `files:` keeps the JSON in its own file. The
ashes Flux Kustomizations (`cluster/apps/ashes/overlays.yaml`) do no variable
substitution. A Flux Kustomization with `postBuild` substitution needs the
`kustomize.toolkit.fluxcd.io/substitute: disabled` annotation on the ConfigMap.

## Metrics and alerts from any namespace

Prometheus selects every ServiceMonitor, PodMonitor and PrometheusRule in the
cluster, without label selectors. An app or an external repo adds scraping and
alerts by shipping those resources next to its workloads.

Alertmanager has **no notification receiver**: the Telegram one never had a real
token and was removed. Alerts show on the Home dashboard and in Alertmanager. To add
a channel, put an AlertmanagerConfig in `alerts/` (any namespace's alerts reach it,
because `alertmanagerConfigMatcherStrategy: None` is set in
`kube-prometheus-stack/`) with its credentials in a SOPS secret, and send
`Watchdog` to a dead man's switch so a broken channel is noticed.

| `severity` | Meaning |
|---|---|
| `critical` | Something people rely on is down |
| `warning` | Needs attention; blocks the Monday k3s upgrade (`cluster/core/system-upgrade/`) |
| `info`, `none` | Inhibition and dashboards only |

Give every new rule a `severity` and a `summary` annotation, and a `description`
when the fix is not obvious. Before adding a rule, check that the chart's defaults
lack it (`kubectl get prometheusrule -n monitoring`): node, pod, volume, target,
Prometheus and Alertmanager failures are already covered.

## Logs

LogQL labels on pod logs: `namespace`, `pod`, `container`, `app`
(`app.kubernetes.io/name`), `instance`, `node`, `source="kubernetes"`. Host
journal logs carry `source="journal"`, `node` and `unit`. Loki's and Vector's own
logs stay out of Loki: Loki logs every rejected write, and shipping that back
formed a loop that filled the ingestion limit. Use `kubectl logs` for them.

The Vector `vector` and `loki` sinks need a scheme in the address
(`http://...`). Without one, Vector 0.61 fails every request with
`client error (Connect)`, which silently dropped logs for a week. `LogsNotReachingLoki`
and `VectorSinkErrors` now alert on it.

## The house

- **Home Assistant** metrics come from its `prometheus:` integration. That block
  lives in `configuration.yaml` on HA's config volume, **not in git**. Prometheus
  authenticates with a "Prometheus" long-lived token
  (`scripts/configure-prometheus-ha-token.py`, which writes
  `cluster/apps/house/home-assistant/prometheus-token.sops.yaml`). If
  `HomeAssistantDown` fires while HA works, the token was revoked.
- **Zigbee** metrics come from `mqtt-exporter`. Each device is a `topic` label,
  `zigbee2mqtt_<friendly name>`. Device availability needs
  `ZIGBEE2MQTT_CONFIG_AVAILABILITY_ENABLED` on zigbee2mqtt. Mains devices are
  offline after 10 minutes unheard, battery devices after 25 hours.
- `ZigbeeDeviceOffline` leaves out bulbs (names containing light, lamp or bedside),
  because they are switched off at the wall, and Zigbee groups. The group names are
  listed in `alerts/house-rules.yaml` and in the Zigbee table on the Home dashboard;
  update both when you add a group.
