import struct
import threading
import queue
import logging
import bluepy.btle as btle

class Overdrive:
    def __init__(self, addr):
        """Initiate an Anki Overdrive connection object,
        and call connect() function.

        Parameters:
        addr -- Bluetooth MAC address for desired Anki Overdrive car.
        """
        self.addr = addr
        self._peripheral = btle.Peripheral()
        self._readChar = None
        self._writeChar = None
        self._connected = False
        self._reconnect = False
        self._delegate = OverdriveDelegate(self)
        self._writeQueue = queue.Queue()
        self._btleSubThread = None
        self.speed = 0
        self.location = 0
        self.piece = 0
        self._locationChangeCallbackFunc = None
        self._pongCallbackFunc = None
        self._transitionCallbackFunc = None
        while True:
            try:
                self.connect()
                break
            except btle.BTLEException as e:
                logging.getLogger("anki.overdrive").error(e.message)

    def __del__(self):
        """Deconstructor for an Overdrive object"""
        self.disconnect()

    def connect(self):
        """Initiate a connection to the Overdrive."""
        if self._btleSubThread is not None and threading.current_thread().ident != self._btleSubThread.ident:
            return # not allow
        self._peripheral.connect(self.addr, btle.ADDR_TYPE_RANDOM)
        self._readChar = self._peripheral.getCharacteristics(1, 0xFFFF, "be15bee06186407e83810bd89c4d8df4")[0]
        self._writeChar = self._peripheral.getCharacteristics(1, 0xFFFF, "be15bee16186407e83810bd89c4d8df4")[0]
        self._delegate.setHandle(self._readChar.getHandle())
        self._peripheral.setDelegate(self._delegate)
        self.turnOnSdkMode()
        self.enableNotify()
        self._connected = True
        self._reconnect = False
        if self._btleSubThread is None:
            self._transferExecution()

    def _transferExecution(self):
        """Fork a thread for handling BTLE notification, for internal use only."""
        self._btleSubThread = threading.Thread(target=self._executor)
        self._btleSubThread.start()

    def disconnect(self):
        """Disconnect from the Overdrive."""
        if self._connected and (self._btleSubThread is None or not self._btleSubThread.is_alive()):
            self._disconnect()
        self._connected = False

    def _disconnect(self):
        """Internal function. Disconnect from the Overdrive."""
        try:
            self._writeChar.write(b"\x01\x0D")
            self._peripheral.disconnect()
        except btle.BTLEException as e:
            logging.getLogger("anki.overdrive").error(e.message)

    def changeSpeed(self, speed, accel):
        """Change speed for Overdrive.
        
        Parameters:
        speed -- Desired speed. (from 0 - 1000)
        accel -- Desired acceleration. (from 0 - 1000)
        """
        command = struct.pack("<BHHB", 0x24, speed, accel, 0x01)
        self.sendCommand(command)

    def changeLaneRight(self, speed, accel):
        """Switch to adjacent right lane.

        Parameters:
        speed -- Desired speed. (from 0 - 1000)
        accel -- Desired acceleration. (from 0 - 1000)
        """
        self.changeLane(speed, accel, 44.5)

    def changeLaneLeft(self, speed, accel):
        """Switch to adjacent left lane.

        Parameters:
        speed -- Desired speed. (from 0 - 1000)
        accel -- Desired acceleration. (from 0 - 1000)
        """
        self.changeLane(speed, accel, -44.5)

    def changeLane(self, speed, accel, offset):
        """Change lane.

        Parameters:
        speed -- Desired speed. (from 0 - 1000)
        accel -- Desired acceleration. (from 0 - 1000)
        offset -- Offset from current lane. (negative for left, positive for right)
        """
        self.setLane(0.0)
        command = struct.pack("<BHHf", 0x25, speed, accel, offset)
        self.sendCommand(command)

    def setLane(self, offset):
        """Set internal lane offset (unused).

        Parameters:
        offset -- Desired offset.
        """
        command = struct.pack("<Bf", 0x2c, offset)
        self.sendCommand(command)

    def turnOnSdkMode(self):
        """Turn on SDK mode for Overdrive."""
        self.sendCommand(b"\x90\x01\x01")

    def enableNotify(self):
        """Repeatly enable notification, until success."""
        while True:
            self._delegate.notificationsRecvd = 0
            self._peripheral.writeCharacteristic(self._readChar.valHandle + 1, b"\x01\x00")
            self.ping()
            self._peripheral.waitForNotifications(3.0)
            if self.getNotificationsReceived() > 0:
                break
            logging.getLogger("anki.overdrive").error("Set notify failed")
    
    def ping(self):
        """Ping command."""
        self.sendCommand(b"\x16")

    def _executor(self):
        """Notification thread, for internal use only."""
        data = None
        while self._connected:
            if self._reconnect:
                while True:
                    try:
                        self.connect()
                        self._reconnect = False
                        if data is not None:
                            self._writeChar.write(data)
                        break
                    except btle.BTLEException as e:
                        logging.getLogger("anki.overdrive").error(e.message)
                        self._reconnect = True
            try:
                data = self._writeQueue.get_nowait()
                self._writeChar.write(data)
                data = None
            except queue.Empty:
                try:
                    self._peripheral.waitForNotifications(0.001)
                except btle.BTLEException as e:
                    logging.getLogger("anki.overdrive").error(e.message)
                    self._reconnect = True
            except btle.BTLEException as e:
                logging.getLogger("anki.overdrive").error(e.message)
                self._reconnect = True
        self._disconnect()
        self._btleSubThread = None

    def getNotificationsReceived(self):
        """Get notifications received count."""
        return self._delegate.notificationsRecvd

    def sendCommand(self, command):
        """Send raw command to Overdrive
        
        Parameters:
        command -- Raw bytes command, without length.
        """
        finalCommand = struct.pack("B", len(command)) + command
        if self._writeChar is None:
            self._reconnect = True
        self._writeQueue.put(finalCommand)

    def setLocationChangeCallback(self, func):
        """Set location change callback.

        Parameters:
        func -- Function for callback. (see _locationChangeCallback() for details)
        """
        self._locationChangeCallbackFunc = func

    def _locationChangeCallback(self, location, piece, speed, clockwise):
        """Location change callback wrapper.

        Parameters:
        addr -- MAC address of car
        location -- Received location ID on piece.
        piece -- Received piece ID.
        speed -- Measured speed.
        clockwise -- Clockwise flag.
        """
        if self._locationChangeCallbackFunc is not None:
            self._locationChangeCallbackFunc(self.addr, location, piece, speed, clockwise)

    def setPongCallback(self, func):
        """Set pong callback.

        Parameters:
        func -- Function for callback. (see _pongCallback() for details)
        """
        self._pongCallbackFunc = func

    def _pongCallback(self):
        """Pong callback wrapper.
        
        Parameters:
        addr -- MAC address of car
        """
        if self._pongCallbackFunc is not None:
            self._pongCallbackFunc(self.addr)
    
    def setTransitionCallback(self, func):
        """Set piece transition callback.

        Parameters:
        func -- Function for callback. (see _transitionCallback() for details)
        """
        self._transitionCallbackFunc = func

    def _transitionCallback(self):
        """Piece transition callback wrapper.
        
        Parameters:
        addr -- MAC address of car
        """
        if self._transitionCallbackFunc is not None:
            self._transitionCallbackFunc(self.addr)


class OverdriveDelegate(btle.DefaultDelegate):
    """Notification delegate object for Bluepy, for internal use only."""

    def __init__(self, overdrive):
        self.handle = None
        self.notificationsRecvd = 0
        self.overdrive = overdrive
        btle.DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        if self.handle == handle:
            self.notificationsRecvd += 1
            (commandId,) = struct.unpack_from("B", data, 1)
            if commandId == 0x27:
                # Location position
                location, piece, offset, speed, clockwiseVal = struct.unpack_from("<BBfHB", data, 2)
                clockwise = False
                if clockwiseVal == 0x47:
                    clockwise = True
                threading.Thread(target=self.overdrive._locationChangeCallback, args=(location, piece, speed, clockwise)).start()
            if commandId == 0x29:
                # Transition notification
                piece, piecePrev, offset, direction = struct.unpack_from("<BBfB", data, 2)
                threading.Thread(target=self.overdrive._transitionCallback).start()
            elif commandId == 0x17:
                # Pong
                threading.Thread(target=self.overdrive._pongCallback).start()

    def setHandle(self, handle):
        self.handle = handle
        self.notificationsRecvd = 0