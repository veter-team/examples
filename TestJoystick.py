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
        self.smooth_window0 = [0,0,0]
        self.smooth_window1 = [0,0,0]


    def nextSensorFrame(self, frame, current=None):

        self.smooth_window0 = self.smooth_window0[1:] + [frame[0].floatdata[0]]
        n = len(self.smooth_window0)
        self.smooth_window0[len(self.smooth_window0) - 1] = sum(self.smooth_window0) / n
        self.smooth_window1 = self.smooth_window1[1:] + [frame[0].floatdata[1]]
        n = len(self.smooth_window1)
        self.smooth_window1[len(self.smooth_window1) - 1] = sum(self.smooth_window1) / n

        actuator_frame = []

        # Initialize actuator control sttucture
        # Forward/backward - axis 1, left/right - axis 0.
        # Actuator 0 is the left wheel, 1 - right

        # If both axis are less then sensibility, then do nothing
        sensibility = 0.20 # 20%

        # If acceleration is less than sensibility, then use
        # "on-place" rotation mode where wheels will rotate in the
        # opposite directions
        if abs(self.smooth_window1[-1:][0]) <= sensibility:
            if abs(self.smooth_window0[-1:][0]) > sensibility:
                # On-place rotation mode
                actuator_cmd = actuators.ActuatorData()
                actuator_cmd.id = 0
                actuator_cmd.speed = self.smooth_window0[-1:][0] * 100.0
                actuator_cmd.distance = 100
                actuator_frame.append(actuator_cmd)

                actuator_cmd = actuators.ActuatorData()
                actuator_cmd.id = 1
                actuator_cmd.speed = -self.smooth_window0[-1:][0] * 100.0
                actuator_cmd.distance = 100
                actuator_frame.append(actuator_cmd)
            else:
                actuator_cmd = actuators.ActuatorData()
                actuator_cmd.id = 0
                actuator_cmd.speed = 0
                actuator_cmd.distance = 0
                actuator_frame.append(actuator_cmd)
                actuator_cmd = actuators.ActuatorData()
                actuator_cmd.id = 1
                actuator_cmd.speed = 0
                actuator_cmd.distance = 0
                actuator_frame.append(actuator_cmd)
        else:
            # Normal cruise mode
            actuator_cmd = actuators.ActuatorData()
            actuator_cmd.id = 0
            actuator_cmd.speed = -self.smooth_window1[-1:][0] * 100.0
            actuator_cmd.distance = 100
            actuator_frame.append(actuator_cmd)
            if self.smooth_window0[-1:][0] < 0: 
                # Left turn. Slow down the left wheel depending on the
                # value of the left/right axis
                actuator_cmd.speed = actuator_cmd.speed - actuator_cmd.speed * (-self.smooth_window0[-1:][0])
            actuator_cmd = actuators.ActuatorData()
            actuator_cmd.id = 1
            actuator_cmd.speed = -self.smooth_window1[-1:][0] * 100.0
            actuator_cmd.distance = 100
            actuator_frame.append(actuator_cmd)
            if self.smooth_window0[-1:][0] > 0: 
                # Right turn. Slow down the right wheel depending on the
                # value of the left/right axis
                actuator_cmd.speed = actuator_cmd.speed - actuator_cmd.speed * self.smooth_window0[-1:][0]            

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
    sys.exit(app.main(sys.argv, "testjoystick.config"))
