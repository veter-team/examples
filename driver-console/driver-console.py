#!/usr/bin/env python
import sys
import os

import gst
import collada
import pyglet
from pyglet.gl import *

import renderer
import video
import SensorCallbackReceiver


try:
    # Try and create a window with multisampling (antialiasing)
    config = Config(sample_buffers=1, samples=4,
                    depth_size=16, double_buffer=True)
    window = pyglet.window.Window(resizable=False, config=config, vsync=True)
except pyglet.window.NoSuchConfigException:
    # Fall back to no multisampling for old hardware
    window = pyglet.window.Window(resizable=False)

window.rotate_x  = 0.0
window.rotate_y = 0.0
window.rotate_z = 0.0


@window.event
def on_draw():
    vreceiver.updateTexture()
    daerender.render(window.rotate_x, window.rotate_y, window.rotate_z)


@window.event
def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
    if abs(dx) > 2:
        if dx > 0:
            window.rotate_y += 2
        else:
            window.rotate_y -= 2
		
    if abs(dy) > 1:
        if dy > 0:
            window.rotate_x -= 2
        else:
            window.rotate_x += 2

    
@window.event
def on_resize(width, height):
    if height==0: height=1
    # Override the default on_resize handler to create a 3D projection
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(60., width / float(height), .1, 1000.)
    glMatrixMode(GL_MODELVIEW)
    return pyglet.event.EVENT_HANDLED


def update(dt):
    pass
pyglet.clock.schedule_interval(update, 1.0/30.0)
    


if __name__ == '__main__':
    filename = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__) + '/data/cockpit.zip'

    # open COLLADA file ignoring some errors in case they appear
    collada_file = collada.Collada(filename, ignore=[collada.DaeUnsupportedError,
                                            collada.DaeBrokenRefError])

    daerender = renderer.GLSLRenderer(collada_file)
	
    window.width = 1024
    window.height = 768

    video_tex_id = daerender.getTextureId('earth2_jpg')
    pipeline = 'autovideosrc ! \
                video/x-raw-yuv, width=640, height=480, framerate=30/1 ! \
                ffmpegcolorspace ! \
                video/x-raw-rgb, bpp=32, depth=32 ! \
                fakesink sync=1'
    # pipeline = 'videotestsrc is-live=true ! video/x-raw-yuv,width=640,height=480,framerate=30/1 ! ffmpegcolorspace ! video/x-raw-rgb, bpp=32, depth=32 ! fakesink sync=1'
    # pipeline = 'videotestsrc is-live=true ! video/x-raw-rgb,width=640,height=480,framerate=30/1 ! ffmpegcolorspace ! video/x-raw-rgb, bpp=32, depth=32  ! fakesink sync=1'
    pipeline = 'appsrc ! application/x-rtp, payload=(int)96 ! gstrtpjitterbuffer latency=10 ! rtph264depay ! h264parse ! decodebin2 ! videoscale ! video/x-raw-yuv, width=640, height=480 ! clockoverlay halign=left valign=top time-format="%Y/%m/%d %H:%M:%S" ! ffmpegcolorspace ! video/x-raw-rgb, bpp=32, depth=32 ! fakesink sync=1'

    sensor_cb = SensorCallbackReceiver.SensorCallbackReceiver(sys.argv)
    vreceiver = video.Receiver(video_tex_id, pipeline, sensor_cb.needdata)

    pyglet.app.run()

    sensor_cb.cleanup()
    vreceiver.cleanup()
    daerender.cleanup()
