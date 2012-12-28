#!/usr/bin/env python
#
# Copyright (c) 2012 Andrey Nechypurenko
# See the file LICENSE for copying permission.

# Standard set for Ice
import sys, traceback, Ice
import time # for sleep function

# Load actuators remote interface definitions
Ice.loadSlice('-I/usr/share/Ice/slice --all ../remote-interfaces/actuators.ice')
import actuators


# Main application class
class HelloMotorApp(Ice.Application):

    def run(self, args):
        # Connect to actuator
        actuator = actuators.ActuatorGroupPrx.checkedCast(\
            self.communicator().stringToProxy('wheels:tcp -h beagleboard.lan -p 10010'))
        if not actuator:
            print args[0] + ": invalid actuator proxy"
            return -1 

        actuator_state = actuator.getStateInterface()
        actuator_state.start() # turn the motor on

        actuator_cmd = actuators.ActuatorData()
        actuator_cmd.id = 0 # use just right track motor

        for s in xrange(0,100,10):
            # Initialize actuator control sttucture
            actuator_cmd.speed = s
            actuator_cmd.distance = 3 # ask for one revolution
            # Send it to actuators
            try:
                actuator.setActuatorsAndWait([actuator_cmd])
            except Ice.Exception, ex:
                print ex
                return -2
            time.sleep(1)

        actuator_state.stop() # turn the motor off
        return 0


# This function is only called if started as stand-alone application,
# i.e. $ python SimpleSensor.py
if __name__ == '__main__':
    print("Ice runtime version %s" % Ice.stringVersion())
    app = HelloMotorApp()
    app.debug = True
    sys.exit(app.main(sys.argv))
