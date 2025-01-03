# FreeRADIUS_Metrics_Exporter

This project forked from Radfilter Exporter version 1.6.0, we with change them to become exporter that collect metrics from FreeRADIUS

## Guide:
#### Create Exporter
There're two ways that you can use FreeRADIUS-Metrics-Exporter:
* Using Container Images:
  - Pull FreeRADIUS Metrics Exporter images via `docker pull` command (if you're using docker):

    ``` bash
    docker pull freeradius-metrics-exporter:1.0
    ```

    Run `docker run` command if you use Docker:

    ``` bash
    docker run -d --name <your exporter name> -p 9814:9814 freeradius-metrics-exporter:<version>
    ```

* Runing with source: (Will be added soon)

