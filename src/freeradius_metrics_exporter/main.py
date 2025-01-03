"""
Entrypoint for the application
"""

import argparse
# from radfilterExporter import radfilterExporter
from freeradius_metrics_exporter.metricsExporter import metricsExporter

def main():
    parser = argparse.ArgumentParser(description='FreeRADIUS Metrics Exporter')

    parser.add_argument('--address', type=str, dest='address', default='0.0.0.0', help='address to serve on')
    parser.add_argument('--port', type=int, dest='port', default='9812', help='port to bind')
    parser.add_argument('--endpoint', type=str, dest='endpoint', default='/metrics', help='endpoint where metrics will be published')
    parser.add_argument('--radfilterip', type=str, dest='radfilterip', default="127.0.0.1", help='Exporter IP address')
    parser.add_argument('--secretport', type=int, dest='secretport', default='18121', help='Exporter secret port number')
    parser.add_argument('--secret', type=str, dest='secret', default="exporter@123", help='FreeRADIUS secret shared with exporter')
    parser.add_argument('--loglevel', type=str, dest='loglevel', default="info", help='log level used for debugging')

    args = parser.parse_args()

    exporter = metricsExporter(**vars(args))
    exporter.run()

if __name__ == '__main__':
    main()
