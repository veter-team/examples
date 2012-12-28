import pyglet
from pyglet.gl import *

import ctypes

import gobject
import gst


class Receiver(object):

    def __init__(self, video_tex_id, pipeline_string, needdata):
        self.tex_updated = True
        self.texdata = (ctypes.c_ubyte * 640 * 480 * 4)()
        self.video_tex_id = video_tex_id
        
        # Create GStreamer pipeline
        self.pipeline = gst.parse_launch(pipeline_string)

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        self.fakesink = self.pipeline.get_by_name('fakesink0')
        self.fakesink.props.signal_handoffs = True
        self.fakesink.connect("handoff", self.on_gst_buffer)

        appsrc = self.pipeline.get_by_name('appsrc0')
        if appsrc is not None and needdata is not None:
            appsrc.connect('need-data', needdata)

        self.pipeline.set_state(gst.STATE_PLAYING)


    def on_gst_buffer(self, fakesink, buff, pad, data=None):
        self.tex_updated = False
        ctypes.memmove(self.texdata, buff.data, buff.size)
        return gst.FLOW_OK


    def updateTexture(self):
        if not self.tex_updated and not self.texdata == None:
            glBindTexture(GL_TEXTURE_2D, self.video_tex_id)
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 640, 480, GL_RGBA, GL_UNSIGNED_BYTE, self.texdata)
            self.tex_updated = True
      
        
    def on_eos(self, bus, msg):
        print('on_eos(): seeking to start of video')
#        self.pipeline.seek_simple(
#            gst.FORMAT_TIME,        
#            gst.SEEK_FLAG_FLUSH | gst.SEEK_FLAG_KEY_UNIT,
#            0L
#        )


    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())


    def cleanup(self):
        print 'Video receiver cleaning up...'
        self.pipeline.set_state(gst.STATE_NULL)
        print 'Video receiver uninitialized.'
