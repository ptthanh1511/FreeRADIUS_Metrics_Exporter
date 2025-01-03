import time
from pyrad.client import Client
from pyrad.dictionary import Dictionary
import socket
import pyrad.packet
import logging
import binascii
from threading import Thread
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn,TCPServer
from prometheus_client import generate_latest, Summary, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, Gauge, CollectorRegistry
from urllib.parse import urlparse


REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])
# registry = REGISTRY

REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')
CACHE=()


class ThreadedTCPServer(ThreadingMixIn,TCPServer):
    pass

class ManualRequestHandler(SimpleHTTPRequestHandler):
    """
    Endpoint handler
    """
    def log_message(self, format, *args):
        pass

    def _sendContent(self, data, status=200, content_type="text/plain"):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        self.wfile.flush()

    def do_GET(self):
        start_time = time.time()
        url = urlparse(self.path)
        logging.info(self.path)
        exporterIP = self.headers.get('Host')
        logging.debug(url)
        if url.path == "/":
            return self._sendContent(
                "<form method=get action=/data><input type=search name=q><input type=submit></form>",
                content_type="text/html",
            )
        elif url.path == self.endpoint:
            global CACHE
            # componentMetrics = list()
            registry = CollectorRegistry()
            componentMetrics={}
            # registry.clear()
            timestampNow = time.time()
            totalAcctRequestOld = 0
            totalProxyAcctRequestOld = 0
            timestampOld = 0
            if CACHE:
                cachedResponse,totalAcctRequestOld,totalProxyAcctRequestOld, timestampOld = CACHE
                if timestampNow - timestampOld < 60:
                    logging.info("Complete gathering health-check information from cache")
                    # logging.warning("Maybe your query interval too small, you should set interval more than 60s.")
                    return self._sendContent(cachedResponse, content_type="application/json")

            radCollection = Client(server=self.freeradexporterip, authport=self.secretport, secret=bytes(self.secret, encoding= 'utf-8'), dict=Dictionary("dictionary.freeradius.pyrad"))
            radCollection.timeout=20 # seconds
            radCollection.retries=3
            raw_data = dict()
            # check_timestamp = dict()

            req = radCollection.CreateAuthPacket(code=pyrad.packet.StatusServer)
            req["FreeRADIUS-Statistics-Type"] = "All"
            req.add_message_authenticator()
            try:
                logging.info("Sending FreeRADIUS_Exporter status request to %s" % self.freeradexporterip)
                raw_data = radCollection.SendPacket(req)
                # check_timestamp = time.time()
                status = 1
                # logging.info("raw_data: %s" % raw_data)
            except pyrad.client.Timeout:
                logging.error("FreeRADIUS_Exporter does not reply")
                status = 0
            except socket.error as error:
                logging.error("Network error: " + error[1])
                status = 99

            componentMetrics['freeradexporter_health_status'] = Gauge('freeradexporter_health_status','FreeRADIUS_Exporter health status',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
            componentMetrics['freeradexporter_health_status'].labels(self.freeradexporterip,exporterIP).set(float(status))

            for attr in raw_data.keys():
                if attr == 'FreeRADIUS-Total-Accounting-Requests':
                    totalAcctRequestNow = raw_data[attr][0]
                    logging.debug('FreeRADIUS-Total-Accounting-Requests: ' + str(raw_data[attr][0]))
                    componentMetrics['freeradexporter_total_accounting_requests'] = Gauge('freeradexporter_total_accounting_requests','FreeRADIUS_Exporter total accounting requests',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                    componentMetrics['freeradexporter_total_accounting_requests'].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                    if raw_data[attr][0] >= totalAcctRequestOld:
                        packets_rate = (raw_data[attr][0] - totalAcctRequestOld)/(timestampNow - timestampOld)
                    else:
                        packets_rate = (raw_data[attr][0])/(timestampNow - timestampOld)
                    componentMetrics['freeradexporter_accounting_requests_rate'] = Gauge('freeradexporter_accounting_requests_rate','FreeRADIUS_Exporter accounting requests rate',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                    componentMetrics['freeradexporter_accounting_requests_rate'].labels(self.freeradexporterip,exporterIP).set(float(packets_rate))
                # elif attr == 'FreeRADIUS-Total-Proxy-Accounting-Requests':
                #     totalProxyAcctRequestNow = raw_data[attr][0]
                #     logging.debug('FreeRADIUS-Total-Proxy-Accounting-Requests: ' + str(raw_data[attr][0]))
                #     componentMetrics['freeradexporter_total_proxy_accounting_requests'] = Gauge('freeradexporter_total_proxy_accounting_requests','FreeRADIUS_Exporter total proxy accounting requests',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                #     componentMetrics['freeradexporter_total_proxy_accounting_requests'].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                #     if raw_data[attr][0] >= totalAcctRequestOld:
                #         packets_rate = (totalProxyAcctRequestNow - totalProxyAcctRequestOld)/(timestampNow - timestampOld)
                #     else:
                #         packets_rate = (raw_data[attr][0])/(timestampNow - timestampOld)
                #     componentMetrics['freeradexporter_total_proxy_accounting_requests_rate'] = Gauge('freeradexporter_total_proxy_accounting_requests_rate','FreeRADIUS_Exporter total proxy accounting requests rate',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                #     componentMetrics['freeradexporter_total_proxy_accounting_requests_rate'].labels(self.freeradexporterip,exporterIP).set(float(packets_rate))
                elif attr == 'FreeRADIUS-Stats-Start-Time':
                    logging.debug('FreeRADIUS-Stats-Start-Time: ' + str(raw_data[attr][0]))
                    componentMetrics['freeradexporter_start_timestamp'] = Gauge('freeradexporter_start_timestamp','FreeRADIUS_Exporter start timestamp',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                    componentMetrics['freeradexporter_start_timestamp'].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                elif attr == 'FreeRADIUS-Queue-PPS-In':
                    logging.debug('FreeRADIUS-Queue-PPS-In: ' + str(raw_data[attr][0]))
                    componentMetrics['freeradexporter_queue_pps_in'] = Gauge('freeradexporter_queue_pps_in','FreeRADIUS_Exporter Queue PPS In',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                    componentMetrics['freeradexporter_queue_pps_in'].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                elif attr == 'FreeRADIUS-Queue-PPS-Out':
                    logging.debug('FreeRADIUS-Queue-PPS-Out: ' + str(raw_data[attr][0]))
                    componentMetrics['freeradexporter_queue_pps_out'] = Gauge('freeradexporter_queue_pps_out','FreeRADIUS_Exporter Queue PPS Out',['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                    componentMetrics['freeradexporter_queue_pps_out'].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                else:
                    # logging.debug("Skipped Metrics: %s" % attr)
                    ### With Viettel DPI project, we're using AAA EMS system to monitor, so skip some metrics is good

                    logging.debug('%s: %s' % (attr, str(raw_data[attr][0])))
                    attr_replace = attr.lower().replace('-', '_')
                    attr_description = attr.lower().replace('-', ' ').replace('_time', 'seconds').replace('freeradius', 'FreeRADIUS_Exporter')
                    attr_replace = attr_replace.replace('acct_','accounting_')
                    attr_description = attr_description.replace('acct ','accounting ')
                    if 'accounting' in attr_replace:
                        componentMetrics[attr_replace] = Gauge(attr_replace,attr_description,['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                        componentMetrics[attr_replace].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                    elif ('auth' not in attr.lower()) or ('access' not in attr.lower()):
                        componentMetrics[attr_replace] = Gauge(attr_replace,attr_description,['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                        componentMetrics[attr_replace].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))
                    else:
                        logging.debug("Skipped Metrics: %s" % attr_replace)

                    ### Show all metrics
                    # attr_replace = attr.lower().replace('-', '_')
                    # logging.debug('%s: %s' % (attr, str(raw_data[attr][0])))
                    # componentMetrics[attr_replace] = Gauge(attr_replace,attr,['FreeRADIUS_ExporterIP','ExporterIP'],registry=registry)
                    # componentMetrics[attr_replace].labels(self.freeradexporterip,exporterIP).set(float(raw_data[attr][0]))

            metrics = generate_latest(registry)
            REQUEST_TIME.observe(time.time() - start_time)
            CACHE = (metrics, totalAcctRequestNow, totalProxyAcctRequestNow, timestampNow)
            logging.info("Complete gathering health-check information")
            return self._sendContent(metrics, content_type="application/json")
        else:
            return self._sendContent(f"404: {url}", status=404)

class freeradexporterExporter(object):
    """
    Basic server implementation that exposes metrics to Prometheus
    """

    def __init__(self, address='0.0.0.0', port=9812, endpoint="/metrics", freeradexporterip="127.0.0.1", secretport=18121, secret='exporter@123', loglevel="info"):
        self._address = address
        self._port = port
        self._endpoint = endpoint
        self._freeradexporterip = freeradexporterip
        self._secretport = secretport
        self._secret = secret
        self._loglevel = loglevel.upper()
        # self._cachetimeout = cachetimeout

    def run(self):
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=(self._loglevel).upper())
        with ThreadedTCPServer(("", self._port), ManualRequestHandler) as httpd:
            ManualRequestHandler.endpoint=self._endpoint
            ManualRequestHandler.freeradexporterip=self._freeradexporterip
            ManualRequestHandler.secretport=self._secretport
            ManualRequestHandler.secret=self._secret
            ManualRequestHandler.loglevel=self._loglevel
            try:
                logging.info("Serving at port " + str(self._port))
                threadServer=Thread(httpd.serve_forever())
                threadServer.daemon()
                threadServer.start()
            except KeyboardInterrupt:
                httpd.shutdown()
                logging.info("Killed exporter Successfully")
