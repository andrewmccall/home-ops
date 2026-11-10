# Monitoring

Prometheus, Alertmanager and Grafana (kube-prometheus-stack plus the Grafana chart),
Loki for logs, and a Vector agent that ships pod and journal logs to Loki. Check the
live stack with `python3 scripts/verify-monitoring.py`.

| Piece | Where | Notes |
|---|---|---|
| Prometheus, Alertmanager, node and kube-state metrics | `kube-prometheus-stack/` | No Thanos; 30 days, 10 GB retention. |
| Grafana | `grafana/` | Datasources and dashboards come from git; UI edits do not persist. |
| Loki | `loki/` | Single binary, filesystem storage, 30 days. |
| Vector agent | `vector/agent/` | DaemonSet writing straight to Loki. Skips Loki's and its own pods. |
| mqtt-exporter | `mqtt-exporter/` | Zigbee2MQTT device state from MQTT, independent of Home Assistant. |
| Alert rules and routing | `alerts/` | |
| Tempo, OpenTelemetry collector | `tempo/`, `otel-collector/` | Deployed, but nothing sends traces yet. |

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

Alertmanager routes every alert, from any namespace, through
`alerts/alertmanager-config.yaml`:

| `severity` | Goes to |
|---|---|
| `critical` | Telegram, repeated hourly |
| `warning` | Telegram, repeated every 4 h |
| `info`, `none`, `Watchdog` | Nowhere (inhibition and dashboards only) |

Give every new rule a `severity` and a `summary` annotation; the Telegram message
is built from `summary` and `description`. Before adding a rule, check that the
chart's defaults lack it (`kubectl get prometheusrule -n monitoring`): node, pod,
volume, target, Prometheus and Alertmanager failures are already covered.

`alertmanagerConfigMatcherStrategy: None` in `kube-prometheus-stack/` is what lets
one AlertmanagerConfig route other namespaces' alerts. The operator default scopes
it to `monitoring` alone, which silently dropped every house alert.

Telegram delivery is broken until the bot token placeholder in
`alerts/alertmanager-config.yaml` is replaced with a SOPS secret.
`AlertmanagerFailedToSendAlerts` cannot reach you through a broken channel, so
the planned fix is a dead man's switch fed from `Watchdog`.

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
