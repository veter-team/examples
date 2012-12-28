#!/usr/bin/env python
#
# Copyright (c) 2012 Andrey Nechypurenko
# See the file LICENSE for copying permission.

# Standard set for Ice
import sys, traceback, Ice

import threading
import time
import math

# Our sensors interfaces
Ice.loadSlice('-I/usr/share/Ice/slice --all ../remote-interfaces/sensors.ice')
import sensors


class CalcSynus(threading.Thread):

    def __init__(self, sensor, period = 10, update_interval = 0.1):
        threading.Thread.__init__(self)
        self.period = period
        self.stop = False
        self.sensor = sensor
        self.t = 0.0
        self.update_interval = update_interval
        self.t_increment = math.pi / (period / self.update_interval)

    def requestStop(self):
        self.stop = True
        self.join()

    def run(self):
        print '  sinus thread started'
        while not self.stop:
            time.sleep(self.update_interval)
            self.sensor.current_data.bytedata[0] = int(abs(math.sin(self.t) * 255.0))
            self.t += self.t_increment
            self.sensor.sendUpdate()


# Implementation of the SensorGroup interface
class SinusSensor(sensors.SensorGroup):

    def __init__(self):
        self.current_data = sensors.SensorData()
        self.current_data.sensorid = 1
        self.current_data.bytedata = [0]

        self.current_callback = None
        self.update_interval = 0.5


    def getStateInterface(self, current=None):
        raise NotImplementedError()


    def getSensorDescription(self, current=None):
        descr = sensors.SensorDescription()
        descr.id = self.current_data.sensorid
        descr.type = sensors.SensorType.Unknown
        descr.minvalue = 0
        descr.maxvalue = 255
        descr.refreshrate = 1.0 / self.update_interval # Hz
        descr.description = 'Generate sinus data'
        descr.vendorid = 'SinusSensorv1.0'

        return [descr]


    def getCurrentValues(self, current=None):
        return [self.current_data]


    def setSensorReceiver(self, callback, current=None):
        self.current_callback = callback


    def cleanSensorReceiver(self, current=None):
        self.current_callback = None

    def sendUpdate(self):
        try:
            if self.current_callback != None:
                self.current_callback.nextSensorFrame([self.current_data])
        except Ice.Exception, ex:
            print 'Can not reach callback receiver. Forgetting it'
            self.current_callback = None


# Main application class
class Server(Ice.Application):

    def run(self, args):
        if len(args) > 1:
            print self.appName() + ": too many arguments"
            return 1

        # Make sensor instance remotely visible
        sensor = SinusSensor()
        adapter = self.communicator().createObjectAdapter("Sensors")
        adapter.add(sensor, self.communicator().stringToIdentity("byteval"))
        adapter.activate()
        print 'Sensor is online'

        sin_thread = CalcSynus(sensor, update_interval=sensor.update_interval)
        sin_thread.start()

        self.communicator().waitForShutdown()

        print 'Shutting down...'
        sin_thread.requestStop()
        print '  sinus thread stopped'
        return 0


# This function is only called if started as stand-alone application,
# i.e. $ python SimpleSensor.py
if __name__ == '__main__':
    print("Ice runtime version %s" % Ice.stringVersion())
    app = Server()
    app.debug = True
    sys.exit(app.main(sys.argv, "sensor.config"))
