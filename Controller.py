#!/usr/bin/env python
#
# Copyright (c) 2012 Andrey Nechypurenko
# See the file LICENSE for copying permission.

# Standard set for Ice
import sys, traceback, Ice

# Sensors and actuators interface definitions
Ice.loadSlice('-I/usr/share/Ice/slice --all ../remote-interfaces/sensors.ice')
Ice.loadSlice('-I/usr/share/Ice/slice --all ../remote-interfaces/actuators.ice')
import sensors, actuators


# Callback interface implementation to receive sensor data and send
# commands to actuator
class Callback(sensors.SensorFrameReceiver):

    def __init__(self, actuator):
        self.actuator = actuator


    def nextSensorFrame(self, frame, current=None):
        actuator_cmd = actuators.ActuatorData()
        actuator_cmd.id = 0
        if len(frame) is 0:
            print 'Warning: got empty sensor frame'
            return

        if len(frame[0].bytedata) is 0:
            print 'Warning: bytedata attribute of sensor frame is empty'
            return
        else:
            print 'Got sensor data: ', ord(frame[0].bytedata[0])

        # Initialize actuator control sttucture
        actuator_cmd.speed = int(ord(frame[0].bytedata[0]) * (100.0 / 255.0))
        actuator_cmd.distance = 10 # ask for one revolution
        # Send it to actuators
        try:
            self.actuator.setActuatorsNoWait([actuator_cmd])
        except Ice.Exception, ex:
            print ex


# Main application class
class Server(Ice.Application):

    def run(self, args):
        if len(args) > 1:
            print self.appName() + ": too many arguments"
            return 1

        # Connect to sensor
        sensor = sensors.SensorGroupPrx.checkedCast(\
            self.communicator().propertyToProxy('Sensor.Proxy'))
        if not sensor:
            print args[0] + ": invalid sensor proxy"
            return 1 

        # Connect to actuator
        actuator = actuators.ActuatorGroupPrx.checkedCast(\
            self.communicator().propertyToProxy('Actuator.Proxy'))
        if not actuator:
            print args[0] + ": invalid actuator proxy"
            return 1 

        actuator_state = actuator.getStateInterface();
        actuator_state.start();
        # Make callback instance remotely visible
        cb = Callback(actuator)
        adapter = self.communicator().createObjectAdapter("Controllers")
        cbObj = adapter.add(cb, self.communicator().stringToIdentity("simplemap"))
        adapter.activate()
        print 'Sensor callback is online'

        # Instruct sensor to send data to our Callback instance
        cbPrx = sensors.SensorFrameReceiverPrx.uncheckedCast(cbObj)
        sensor.setSensorReceiver(cbPrx)
        print 'Initialization complete. Ready.'

        self.communicator().waitForShutdown()
        print 'Shut down...'
        actuator_state.stop();
        return 0


# This function is only called if started as stand-alone application,
# i.e. $ python SimpleSensor.py
if __name__ == '__main__':
    print("Ice runtime version %s" % Ice.stringVersion())
    app = Server()
    app.debug = True
    sys.exit(app.main(sys.argv, "controller.config"))
