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


def sign(x):
    return 1.0 if x >= 0 else -1.0

# Callback interface implementation to receive sensor data and send
# commands to actuator
class Callback(sensors.SensorFrameReceiver):

    def __init__(self, actuator):
        self.actuator = actuator
        self.prev_pos = 10.0


    def nextSensorFrame(self, frame, current=None):
        # Axis 2 is stick rotation
        # Axis 3 is "accel" knob
        if self.prev_pos == 10.0:
            self.prev_pos = 0.5
            actuator_frame = []
            actuator_cmd = actuators.ActuatorData()
            actuator_cmd.id = 0
            actuator_cmd.speed = -1.0
            actuator_cmd.distance = 1.0
            actuator_frame.append(actuator_cmd)
            # Position the servo to the left-most position
            try:
                self.actuator.setActuatorsNoWait(actuator_frame)
            except Ice.Exception, ex:
                print ex
            actuator_frame = []
            actuator_cmd = actuators.ActuatorData()
            actuator_cmd.id = 0
            actuator_cmd.speed = 1.0
            actuator_cmd.distance = 0.5
            actuator_frame.append(actuator_cmd)
            # Position the servo to the middle
            try:
                self.actuator.setActuatorsNoWait(actuator_frame)
            except Ice.Exception, ex:
                print ex

        # Scale to 0:1 interval
        new_pos = (frame[0].floatdata[2] + 1.0) / 2.0

        actuator_frame = []

        actuator_cmd = actuators.ActuatorData()
        actuator_cmd.id = 0
        # Uncomment if axis 3 (knob) is used
        # actuator_cmd.speed = sign(new_pos - self.prev_pos)
        # Uncomment if axis 2 (stick rotation) is used
        actuator_cmd.speed = sign(self.prev_pos - new_pos)
        actuator_cmd.distance = abs(new_pos - self.prev_pos)
        # Add some toolerance to avoid sending almost the 
        # same position again and again
        if actuator_cmd.distance  < 0.01:
            return;
        self.prev_pos = new_pos
        actuator_frame.append(actuator_cmd)

        # Send it to actuators
        try:
            self.actuator.setActuatorsNoWait(actuator_frame)
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
        admin = sensor.getStateInterface()
        admin.start()
        print 'Initialization complete. Ready.'

        self.communicator().waitForShutdown()
        print 'Shut down...'
        return 0


# This function is only called if started as stand-alone application,
# i.e. $ python SimpleSensor.py
if __name__ == '__main__':
    print("Ice runtime version %s" % Ice.stringVersion())
    app = Server()
    app.debug = True
    sys.exit(app.main(sys.argv, "testservo.config"))
