from setuptools import setup, find_packages, find_namespace_packages

VERSION = "1.6.0"
PACKAGE_NAME = "freeradius-metrics-exporter"

setup(
    name=PACKAGE_NAME,
    description="Metrics Exporter for FreeRADIUS",
    version="1.6.0",
    author="Freezing",
    url="https://github.com/ptthanh1511/FreeRADIUS_Metrics_Exporter.git",
    package_dir = {"": "src"},
    packages = find_packages(where="src"),
    include_package_data=True,
    zip_safe=False,
    package_data={},
    license='MIT',
    classifiers=[
        'Development Status :: 1 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ],
    install_requires=[
        "prometheus-client",
        "pyyaml",
        "requests",
        "pyrad",
        # "jsonpath-ng",
        # "Jinja2",
    ],
    entry_points={
        'console_scripts': [
            'freeradius-metrics-exporter = freeradius_metrics_exporter.main:main',
        ],
    }
)
