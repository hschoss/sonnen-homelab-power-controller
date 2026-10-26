# Projektbeschreibung: Sonnen-Homelab Power Controller mit Kubernetes Low-Power-Steuerung

## Ziel des Projekts

Dieses Projekt soll ein intelligentes Energiemanagement-System für ein privates Homelab aufbauen. Die zentrale Idee ist, den Energieverbrauch des Kubernetes-Clusters automatisch an die verfügbare Energie aus einem Batteriespeicher bzw. einer Solaranlage anzupassen.

Das System soll den aktuellen Ladezustand des Batteriespeichers überwachen und abhängig vom verfügbaren Energielevel entscheiden, ob das Kubernetes-Cluster normal betrieben wird oder in einen energiesparenden Low-Power-Modus wechselt.

Das Ziel ist nicht, das Cluster vollständig auszuschalten, sondern die Rechenlast und den Stromverbrauch dynamisch zu reduzieren, wenn wenig Energie verfügbar ist.

---

# Ausgangssituation

Es existiert ein Kubernetes-Cluster in einer privaten Homelab-Umgebung.

Beispiel:

* Kubernetes läuft auf mehreren Nodes.
* Das Cluster wird für verschiedene Workloads verwendet.
* Ein BOINC/Eintein@Home-Compute-Workload läuft als CPU-intensiver Dienst.
* Die Nodes können erhebliche elektrische Leistung aufnehmen.
* Ein Batteriespeicher versorgt die Infrastruktur teilweise oder vollständig mit erneuerbarer Energie.

Derzeit läuft das Cluster unabhängig vom Energiezustand.

Beispiel:

* Batterie voll → Cluster darf maximale Leistung liefern.
* Batterie fast leer → Cluster verbraucht weiterhin hohe Leistung.
* Batterie leer → unnötige Belastung des Stromnetzes.

Das soll automatisiert optimiert werden.

---

# Grundidee

Das System bildet eine Steuerungsschicht zwischen:

1. Energiequelle

   * Batteriespeicher
   * Solaranlage
   * Wechselrichter
   * Energiemonitoring-System

und

2. Kubernetes-Cluster

Die Steuerung liest regelmäßig den Batteriestand aus und führt abhängig vom Zustand Aktionen im Cluster aus.

---

# Hauptlogik

## Normalbetrieb

Batteriestand:

```
>= 80%
```

Aktion:

Das Kubernetes-Cluster läuft vollständig.

Erlaubt:

* BOINC CPU-Workloads
* Compute-intensive Pods
* Entwicklungsumgebungen
* Home-Services
* Monitoring
* Datenbanken
* Container-Workloads

Beispiel:

```
Battery: 95%

Controller:
"Genug Energie vorhanden"

Kubernetes:
- alle Nodes aktiv
- normale Pod-Scheduling-Regeln
- BOINC darf rechnen
- keine Einschränkungen
```

---

# Low-Power-Modus

Trigger:

```
Battery < 80%
```

Das Cluster wird nicht heruntergefahren.

Stattdessen wird ein Energiesparmodus aktiviert.

Ziel:

Den Stromverbrauch stark reduzieren, aber die Infrastruktur erreichbar halten.

---

## Aktionen im Low-Power-Modus

### 1. Compute-Workloads stoppen

CPU-intensive Anwendungen werden pausiert.

Beispiele:

BOINC:

Vorher:

```
56 CPU Kerne
34 Einstein@Home Tasks
CPU Load ~30+
```

Nachher:

```
BOINC Deployment:
replicas = 0
```

oder:

```
boinccmd --set_run_mode never
```

---

### 2. Nicht notwendige Pods herunterfahren

Das System soll zwischen wichtigen und unwichtigen Anwendungen unterscheiden.

Beispiel Kubernetes Labels:

Produktive Services:

```yaml
labels:
  power-mode: critical
```

bleiben aktiv.

Nicht kritische Services:

```yaml
labels:
  power-mode: optional
```

werden pausiert.

Beispiel:

Vorher:

```
namespace home:
  homeassistant       running
  grafana             running
  postgres            running

namespace compute:
  boinc               running
  ai-worker           running
  benchmark           running
```

Low Power:

```
namespace home:
  homeassistant       running
  grafana             running

namespace compute:
  boinc               stopped
  ai-worker           stopped
  benchmark           stopped
```

---

### 3. Kubernetes Ressourcen reduzieren

Der Controller soll optional:

* Deployments skalieren
* Replicas reduzieren
* CronJobs pausieren
* Jobs stoppen
* CPU Limits reduzieren

Beispiele:

```bash
kubectl scale deployment boinc --replicas=0
```

oder:

```yaml
resources:
 limits:
   cpu: "1"
```

statt:

```yaml
limits:
 cpu: "56"
```

---

# High-Power-Modus

Wenn Batterie wieder steigt:

Trigger:

```
Battery > 90%
```

(Hysterese, damit das System nicht ständig umschaltet)

Dann:

```
Controller:
"Energie verfügbar"

Aktionen:
- BOINC starten
- pausierte Deployments hochfahren
- normale Ressourcen aktivieren
```

Beispiel:

```
Battery:
92%

Kubernetes:
boinc replicas = 1
compute workloads active
normal mode restored
```

---

# Warum zwei Schwellenwerte?

Nicht:

```
80%:
OFF

80%:
ON
```

weil das zu ständigem Umschalten führt.

Stattdessen:

```
Battery < 80%
       |
       v
LOW POWER


Battery > 90%
       |
       v
NORMAL
```

Diese Differenz nennt man Hysterese.

---

# Architektur

## Komponenten

## 1. Power Controller Service

Eigene Anwendung.

Mögliche Technologien:

* Python
* Go
* Rust

Aufgabe:

* Batterie API abfragen
* Zustand speichern
* Kubernetes API bedienen

Beispiel:

```
sonnen-api
     |
     |
     v

Power Controller

     |
     |
     v

Kubernetes API
```

---

# Datenbank

Das Projekt enthält bereits:

```
sonnen-homelab-power-controller
```

mit PostgreSQL.

Die Datenbank soll speichern:

## Battery History

Beispiel:

```
timestamp
battery_percentage
solar_power
grid_power
mode
```

Beispiel:

```
15:00
battery=87%
mode=normal


15:30
battery=75%
mode=low_power
```

---

# Dashboard

pgAdmin existiert bereits als Werkzeug.

Später möglich:

Grafana Dashboard:

Anzeige:

```
Battery:
████████░░ 82%

Cluster Mode:
NORMAL


CPU usage:
340W


Saved Energy:
1.4kWh
```

---

# Kubernetes Integration

Der Controller benötigt Zugriff auf Kubernetes.

Möglichkeiten:

## Option 1: Kubernetes ServiceAccount

Empfohlen.

Der Controller läuft selbst im Cluster.

Beispiel:

```
namespace:
power-controller

deployment:
power-controller

serviceAccount:
power-controller
```

RBAC erlaubt:

* deployments skalieren
* pods löschen
* nodes cordon/drain
* jobs pausieren

---

# Beispiel Ablauf

## Morgens

```
08:00

Solar produziert Energie

Battery:
95%

Controller:

Mode = NORMAL

Actions:
- BOINC active
- all workloads active
```

---

## Nachmittag

```
15:00

Clouds

Battery:
78%

Controller:

Mode change:
NORMAL -> LOW_POWER
```

Aktionen:

```
scale boinc 1 -> 0

pause AI workloads

keep:
Home Assistant
Monitoring
Database
```

---

## Abend

```
22:00

Battery:
93%

Controller:

LOW_POWER -> NORMAL
```

Aktionen:

```
start BOINC
restore workloads
```

---

# Sicherheitsanforderungen

Das System darf niemals kritische Dienste abschalten.

Deshalb:

Whitelist:

```
critical:
- monitoring
- dns
- homeassistant
- storage
```

Blacklist:

```
optional:
- BOINC
- AI workloads
- benchmarks
```

---

# Erweiterungen

Später möglich:

## Wettervorhersage

Nicht nur aktuelle Batterie betrachten.

Beispiel:

```
Battery:
70%

Aber:
Morgen Sonne erwartet

=> kein aggressiver Shutdown
```

---

## Strompreis berücksichtigen

Bei dynamischen Tarifen:

```
Strom teuer:
reduce workloads

Strom billig:
increase workloads
```

---

## Automatische Compute-Nutzung

Überschussenergie:

```
Solar:
3000W Überschuss

Controller:
Starte zusätzliche Compute Pods
```

---

# Endziel

Das fertige System soll ein autonomes, energieoptimiertes Homelab ermöglichen:

```
                 Solar
                   |
                   |
             Batteriespeicher
                   |
                   |
          Power Controller
                   |
        ---------------------
        |
        |
 Kubernetes Cluster

        |
        |
 ----------------------------
 |            |             |
BOINC     Services      Storage

```

Das Cluster nutzt möglichst viel erneuerbare Energie, reduziert automatisch seine Last bei Energiemangel und maximiert Compute-Leistung bei Energieüberschuss.

Das System verbindet:

* Kubernetes-Orchestrierung
* Energiemanagement
* Automatisierung
* Homelab-Infrastruktur
* nachhaltiges Computing

und bildet eine intelligente Energie-Aware-Compute-Plattform.

