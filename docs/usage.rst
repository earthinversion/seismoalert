Usage
=====

Command-Line Interface
----------------------

SeismoAlert provides a CLI with four main commands.

Fetch Earthquakes
~~~~~~~~~~~~~~~~~

Fetch recent earthquakes from the USGS API:

.. code-block:: bash

   # Last 24 hours, M2.5+
   seismoalert fetch

   # Last 7 days, M4.0+
   seismoalert fetch --days 7 --min-magnitude 4.0

Analyze Seismicity
~~~~~~~~~~~~~~~~~~

Run statistical analysis including Gutenberg-Richter fitting:

.. code-block:: bash

   seismoalert analyze --days 30 --min-magnitude 1.0

Generate Maps
~~~~~~~~~~~~~

Create an interactive HTML map of earthquake locations:

.. code-block:: bash

   seismoalert map --output earthquakes.html

Monitor
~~~~~~~

One-shot monitoring with configurable alert thresholds:

.. code-block:: bash

   seismoalert monitor --alert-magnitude 6.0 --alert-count 50

Python API
----------

You can also use SeismoAlert as a Python library:

.. code-block:: python

   from seismoalert.client import USGSClient
   from seismoalert.analyzer import gutenberg_richter

   client = USGSClient()
   catalog = client.fetch_earthquakes(min_magnitude=2.5)

   gr = gutenberg_richter(catalog)
   print(f"b-value: {gr.b_value}")
