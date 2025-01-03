# Compile freeradius_Exporter
FROM alpine:3.14 as build

LABEL Name=builder
# LABEL appVersion=${appVersion}
# LABEL maintainer=${maintainer}

ENV TZ=Asia/Ho_Chi_Minh

COPY ./src /opt/Radfilter_Exporter/src
COPY setup.py /opt/Radfilter_Exporter/setup.py

RUN apk add py3-pip && \
    pip3 install setuptools
WORKDIR /opt/Radfilter_Exporter
RUN python3 setup.py sdist --formats=gztar

FROM alpine:3.14

LABEL Name=freeradius_Exporter
LABEL appVersion=1.0.0
LABEL maintainer=Freezing

ENV TZ=Asia/Ho_Chi_Minh

# COPY --from=build /opt/Radfilter_Exporter/src/freeradius_Exporter/templates /opt/Radfilter_Exporter/templates
COPY --from=build /opt/Radfilter_Exporter/dist/*.tar.gz /tmp/freeradius_Exporter/freeradius-exporter.tar.gz
COPY --from=build /opt/Radfilter_Exporter/src/freeradius_exporter/dictionary.freeradius.pyrad /dictionary.freeradius.pyrad
RUN apk add tzdata py3-pip && \
    echo $TZ > /etc/timezone && \
    pip install --no-cache-dir /tmp/freeradius_Exporter/freeradius-exporter.tar.gz && \
    rm -rf /tmp/*
ENTRYPOINT ["freeradius-metrics-exporter"]
EXPOSE 9812
