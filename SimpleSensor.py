#!/usr/bin/env python
#
# Copyright (c) 2012 Andrey Nechypurenko
# See the file LICENSE for copying permission.

# Standard set for Ice
import sys, traceback, Ice

# Our sensors interfaces
Ice.loadSlice('-I/usr/share/Ice/slice --all ../remote-interfaces/sensors.ice')
import sensors

# Implementation of the SensorGroup interface
class IntValSensor(sensors.SensorGroup):

    def __init__(self):
        self.current_data = sensors.SensorData()
        self.current_data.sensorid = 1
        self.current_data.bytedata = [0]

        self.current_callback = None


    def getStateInterface(self, current=None):
        raise NotImplementedError()


    def getSensorDescription(self, current=None):
        descr = sensors.SensorDescription()
        descr.id = self.current_data.sensorid
        descr.type = sensors.SensorType.Unknown
        descr.minvalue = 0
        descr.maxvalue = 255
        descr.refreshrate = 0
        descr.description = 'Integer value entered with the keyboard'
        descr.vendorid = 'SimpleSensorKBv1.0'

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
        sensor = IntValSensor()
        adapter = self.communicator().createObjectAdapter("Sensors")
        adapter.add(sensor, self.communicator().stringToIdentity("byteval"))
        adapter.activate()
        print 'Sensor is online'

        # In real application it might be necessary for the Sensor
        # interface implementation to start own thread and observe the
        # data source. In this case, instead of having loop here, it
        # should be enough to call
        # self.communicator().waitForShutdown().
        while True:
            try:
                # Read "sensor value" from standard input
                v = int(raw_input("==> "))
                if v >= 0 and v <= 255:
                    sensor.current_data.bytedata[0] = v
                    sensor.sendUpdate()
                else:
                    raise ValueError()
                                    
            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Ice.Exception, ex:
                print ex
            except ValueError:
                print 'Please enter the integer value in range 0-255'

        print 'Shutting down...'
        self.communicator().shutdown()
        return 0


# This function is only called if started as stand-alone application,
# i.e. $ python SimpleSensor.py
if __name__ == '__main__':
    print("Ice runtime version %s" % Ice.stringVersion())
    app = Server()
    app.debug = True
    sys.exit(app.main(sys.argv, "sensor.config"))
