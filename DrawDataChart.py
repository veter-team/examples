#!/usr/bin/env python
#
# Copyright (c) 2012 Andrey Nechypurenko
# See the file LICENSE for copying permission.

# Standard set for Ice
import sys, traceback, Ice

# Our Sensors interface definitions
Ice.loadSlice('-I/usr/share/Ice/slice --all ../remote-interfaces/sensors.ice')
import sensors

import gtk
from gtk import gdk
import cairo
import gobject
import random


# Area to display sensor data chart
class SensorChart(gtk.DrawingArea):

    def __init__(self):
        super(SensorChart, self).__init__()
        self.sensor_data = []
        self.sensor_smooth_data = []
        for i in xrange(256):
            self.sensor_data.append(10)
            self.sensor_smooth_data.append(10)
        self.connect("expose_event", self.expose)
        self.update()
        # update the chart four time a second
        gobject.timeout_add(250, self.update)
        self.annotation = "Sensor data log"


    def expose(self, widget, event):
        context = widget.window.cairo_create()
        # set a clip region for the expose event
        context.rectangle(event.area.x, event.area.y,
                          event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        return False


    def draw(self, context):
        rect = self.get_allocation()
        graph_area_height = rect.height - 16 # leave some place for text

        context.set_source_rgb(1, 1, 1)
        context.fill_preserve()
        context.set_source_rgb(0, 0, 0)
        context.set_line_width(0.25 * context.get_line_width()) 
        
        # Plot data
        context.set_source_rgb(1, 0, 0) # red
        data_len = len(self.sensor_data)
        x = 0
        dx = float(rect.width) / data_len
        y_scale = float(graph_area_height) / max(self.sensor_data)
        y_prev = self.sensor_data[0]
        for dp in self.sensor_data[1:]:
            x_prev = x
            x += dx
            context.move_to(x_prev, rect.height - y_scale * y_prev)
            context.line_to(x, rect.height - y_scale * dp)
            context.stroke()
            y_prev = dp

        # Plot smoothed data
        context.set_source_rgb(0, 1, 0) # green
        context.move_to(0, 0)
        data_len = len(self.sensor_smooth_data)
        x = 0
        dx = float(rect.width) / data_len
        y_scale = float(graph_area_height) / max(self.sensor_smooth_data)
        y_prev = self.sensor_smooth_data[0]
        for dp in self.sensor_smooth_data[1:]:
            x_prev = x
            x += dx
            context.move_to(x_prev, rect.height - y_scale * y_prev)
            context.line_to(x, rect.height - y_scale * dp)
            context.stroke()
            y_prev = dp

        # Draw sensor info
        context.set_source_rgb(0, 0, 0) # black
        context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        context.set_font_size(12)
        context.move_to(0, 12)
        context.show_text(self.annotation)

    def redraw_canvas(self):
        if self.window:
            alloc = self.get_allocation()
            rect = gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
            self.window.process_updates(True)

    def update(self):
        # update the time
        if self.window:
            alloc = self.get_allocation()
            rect = gdk.Rectangle(alloc.x, alloc.y, alloc.width, alloc.height)
            self.window.invalidate_rect(rect, True)
        return True # keep running this event

    def addDataPoint(self, datapoint):
        self.sensor_data = self.sensor_data[1:] + [datapoint]
        self.sensor_smooth_data = self.sensor_smooth_data[1:] + [datapoint]
        n = min(len(self.sensor_smooth_data), 3)
        self.sensor_smooth_data[len(self.sensor_smooth_data) - 1] = sum(self.sensor_smooth_data[-n:]) / n

    def setAnnotation(self, text):
        self.annotation = text

    def getAnnotation(self):
        return self.annotation


# Callback interface implementation to receive sensor data and update
# chart
class Callback(sensors.SensorFrameReceiver):

    def __init__(self, chart, frameidx):
        self.chart = chart
        self.frameidx = frameidx
        self.annotation = ''


    def nextSensorFrame(self, frame, current=None):
        if len(frame) is 0:
            print 'Warning: got empty sensor frame'
            return

        if len(frame[self.frameidx].bytedata) is not 0:
            datapoint = ord(frame[self.frameidx].bytedata[0])
        elif len(frame[self.frameidx].shortdata) is not 0:
            datapoint = frame[self.frameidx].shortdata[0]
        elif len(frame[self.frameidx].intdata) is not 0:
            datapoint = frame[self.frameidx].intdata[0]
        elif len(frame[self.frameidx].longdata) is not 0:
            datapoint = frame[self.frameidx].longdata[0]
        elif len(frame[self.frameidx].floatdata) is not 0:
            datapoint = frame[self.frameidx].floatdata[0]
        else:
            print 'Warning: bytedata attribute of sensor frame is empty'
            return
        if len(self.annotation) == 0:
            self.annotation = self.chart.getAnnotation()
        self.chart.addDataPoint(datapoint)
        self.chart.setAnnotation(self.annotation + '. ' + str(datapoint))


# Main application class
class Server(Ice.Application):

    def __init__(self, chart, dataidx):
        super(Server, self).__init__()
        self.chart = chart
        self.dataidx = dataidx

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

        # Make callback instance remotely visible
        cb = Callback(self.chart, dataidx)
        adapter = self.communicator().createObjectAdapter("Callback")
        cbObj = adapter.add(cb, self.communicator().stringToIdentity("chart"))
        adapter.activate()
        print 'Sensor callback is online'

        # Instruct sensor to send data to our Callback instance
        cbPrx = sensors.SensorFrameReceiverPrx.uncheckedCast(cbObj)
        sensor.setSensorReceiver(cbPrx)
        admin = sensor.getStateInterface()
        admin.start()
        print 'Initialization complete. Ready.'

        return 0



# This function is only called if started as stand-alone application,
# i.e. $ python SimpleSensor.py
def main():
    # Which SensorData element from data frame to use
    dataidx = 0

    window = gtk.Window()
    window.set_default_size(600, 300)

    chart = SensorChart()

    window.add(chart)
    window.connect("destroy", gtk.main_quit)
    window.show_all()

    print("Ice runtime version %s" % Ice.stringVersion())
    #app = Server(chart)
    #app.debug = True

    try:
        if len(sys.argv) == 1:
            print 'using default configuration settings: --Ice.Config=drawchart.config'
            sys.argv.append('--Ice.Config=drawchart.config')
        communicator = Ice.initialize(sys.argv)


        # Connect to sensor
        sensor = sensors.SensorGroupPrx.checkedCast(\
            communicator.propertyToProxy('Sensor.Proxy'))
        if not sensor:
            print args[0] + ": invalid sensor proxy"
            return 1 

        # Make callback instance remotely visible
        cb = Callback(chart, dataidx)
        adapter = communicator.createObjectAdapter("Callback")
        cbObj = adapter.add(cb, communicator.stringToIdentity("chart"))
        adapter.activate()
        print 'Sensor callback is online'

        # Instruct sensor to send data to our Callback instance
        cbPrx = sensors.SensorFrameReceiverPrx.uncheckedCast(cbObj)
        sensor.setSensorReceiver(cbPrx)
        sensor_descr = sensor.getSensorDescription()
        chart.setAnnotation("Sensor " + str(sensor_descr[dataidx].id) + ": " + sensor_descr[dataidx].description + ". Model: " + sensor_descr[dataidx].vendorid)
        admin = sensor.getStateInterface()
        admin.start()
        print 'Initialization complete. Ready.'
    except:
        traceback.print_exc()
        return 1

    # Run GTK event loop. Activating ICE object adapter (above) will
    # create worker threads to process callback invocations.
    gtk.main()

    # It is important to destroy communicator before main thread exits
    communicator.destroy()

if __name__ == '__main__':
    main()
