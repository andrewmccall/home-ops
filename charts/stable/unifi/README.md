# unifi

![Version: 1.0.2](https://img.shields.io/badge/Version-1.0.2-informational?style=flat-square) ![AppVersion: v7.1.68](https://img.shields.io/badge/AppVersion-v7.1.68-informational?style=flat-square)

Ubiquiti Network's Unifi Controller

## Source Code

* <https://github.com/jacobalberty/unifi-docker>

## Requirements

## Dependencies

| Repository | Name | Version |
|------------|------|---------|
| https://charts.bitnami.com/bitnami | mongodb | 15.6.18 |
| https://home-ops.andrewmccall.com/charts/library/ | common | 1.0.2 |

## Installing the Chart

This is a [Helm Library Chart](https://helm.sh/docs/topics/library_charts/#helm).

**WARNING: THIS CHART IS NOT MEANT TO BE INSTALLED DIRECTLY**

## Configuration

Read through the [values.yaml](./values.yaml) file. It has several commented out suggested values.

## Custom configuration

### Running with separate MongoDB

By default the Unifi controller runs an internal MongoDB.
If you wish to run the chart with a separate MongoDB instance our chart provides the option to enable a MongoDB instance by adding the following in your `values.yaml`:

```yaml
mongodb:
  enabled: true
```

(For more configuration options see the [mongodb chart documentation](https://github.com/bitnami/charts/tree/master/bitnami/mongodb).)

If you do not specify any other configuration, the required environment variables will be inferred automatically.
It is also possible to override the environment variables to configure the image. See [here](https://github.com/jacobalberty/unifi-docker#external-mongodb-environment-variables) for more details.

### Regarding the services

By default it is not possible to combine TCP and UDP ports on a service with `type: LoadBalancer`. This can be solved in a number of ways:

1. Create a separate service containing the UDP ports. This could be done by setting disabling the UDP ports under `service.main.ports` and adding the following in your `values.yaml`:

```yaml
service:
  udp:
    enabled: true
    type: LoadBalancer
    # <your other service configuration>
    ports:
      stun:
        enabled: true
        port: 3478
        protocol: UDP
      syslog:
        enabled: true
        port: 5514
        protocol: UDP
      discovery:
        enabled: true
        port: 10001
        protocol: UDP
```

2. Since Kubernetes 1.20 there is a feature gate that can be enabled to allow TCP and UDP ports to coexist on Services with `type: Loadbalancer`.
   You will need to enable the `MixedProtocolLBService` feature gate in order to achieve this.

   For more information about feature gates, please see [the docs](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/).

## Values

**Important**: When deploying an application Helm chart you can add more values from our common library chart [here](https://github.com/k8s-at-home/library-charts/tree/main/charts/stable/common)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| env | object | See below | environment variables. See more environment variables in the [image documentation](https://github.com/jacobalberty/unifi-docker#environment-variables). |
| env.JVM_INIT_HEAP_SIZE | string | `nil` | Java Virtual Machine (JVM) initial, and minimum, heap size Unset value means there is no lower limit |
| env.JVM_MAX_HEAP_SIZE | string | `"1024M"` | Java Virtual Machine (JVM) maximum heap size For larger installations a larger value is recommended. For memory constrained system this value can be lowered. |
| env.RUNAS_UID0 | string | `"false"` | Run UniFi as root |
| env.TZ | string | `"UTC"` | Set the container timezone |
| env.UNIFI_GID | string | `"999"` | Specify the group ID the application will run as |
| env.UNIFI_UID | string | `"999"` | Specify the user ID the application will run as |
| image.pullPolicy | string | `"IfNotPresent"` | image pull policy |
| image.repository | string | `"jacobalberty/unifi"` | image repository |
| image.tag | string | `"8.3.32"` |  |
| ingress.main | object | See values.yaml | Enable and configure ingress settings for the chart under this key. |
| ingress.portal | object | See values.yaml | Enable and configure settings for the captive portal ingress under this key. |
| mongodb | object | See values.yaml | Enable and configure mongodb database subchart under this key.    For more options see [mongodb chart documentation](https://github.com/bitnami/charts/tree/master/bitnami/mongodb) |
| persistence | object | See values.yaml | Configure persistence settings for the chart under this key. |
| podSecurityContext | object | See below | pod security context. |
| service | object | See values.yaml | Configures service settings for the chart. |
| service.main.ports.controller | object | See values.yaml | Configure Controller port used for device command/control |
| service.main.ports.discovery | object | See values.yaml | Configure device discovery port |
| service.main.ports.http | object | See values.yaml | Configure Web interface + API port |
| service.main.ports.portal-http | object | See values.yaml | Configure Captive Portal HTTP port |
| service.main.ports.portal-https | object | See values.yaml | Configure Captive Portal HTTPS port |
| service.main.ports.speedtest | object | See values.yaml | Configure Speedtest port (used for UniFi mobile speed test) |
| service.main.ports.stun | object | See values.yaml | Configure STUN port |
| service.main.ports.syslog | object | See values.yaml | Configure remote syslog port |

## Changelog

All notable changes to this application Helm chart will be documented in this file but does not include changes from our common library. To read those click [here](https://github.com/k8s-at-home/library-charts/tree/main/charts/stable/commonREADME.md#Changelog).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### [1.0.0]

Copy from k8s-at-home

#### Added

- N/A

#### Changed

- N/A

#### Removed

- N/A

[1.0.0]: #1.0.0

## Support

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.5.0](https://github.com/norwoodj/helm-docs/releases/v1.5.0)
