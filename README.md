overdrive-python
================

Object interface for controlling Anki Overdrive with Python.

This project provide an API to control Anki Overdrive from Python.
Commands are mostly reverse engineered from [Anki Drive SDK](https://github.com/anki/drive-sdk) and [node-mqtt-for-anki-overdrive](https://github.com/IBM-Bluemix/node-mqtt-for-anki-overdrive).

This code is depended on [bluepy](https://github.com/IanHarvey/bluepy), so it's only work on Linux system.

Requirements
------------
* [Python 3.4+](https://python.org)
* [bluepy](https://github.com/IanHarvey/bluepy)
* Root permission

Usages
------
To use this interface, start with initiate Overdrive object with desired Bluetooth MAC address:

```python
from overdrive import Overdrive

car = Overdrive("YOUR OVERDRIVE MAC ADDRESS")
```

For example, if your Overdrive Bluetooth MAC address is 00:11:22:33:44:55, use the following code:

```python
from overdrive import Overdrive

car = Overdrive("00:11:22:33:44:55")
```

After initialization, you can perform desired action on created object. For example, if you want to set a speed for your Overdrive, call `changeSpeed` function on `car` object. The following code is an example with speed of 500 and acceleration of 1000:

```python
car.changeSpeed(500, 1000)
```

Documentation
-------------

See `overdrive.py` file.

License
-------

This project is licensed under MIT license.
See `LICENSE` file for details.
