# coding: utf-8
import crappy2
import time
import numpy as np

#  General parameters for whole program

offset_time = 5  # Time during which offset is measured on labjack

#  Program and crappy initialization, do not change following

crappy2.blocks.MasterBlock.instances = []  # Init masterblock instances
timestamp = time.localtime()
string_stamp = "%i_%i_%i_%i:%i" % (timestamp.tm_year, timestamp.tm_mon,
                                   timestamp.tm_mday, timestamp.tm_hour,
                                   timestamp.tm_min)
path_measures_instron = '/home/francois/Essais/005_Traction_Specimen_1mois/4_11/'
class EvalStress(crappy2.links.MetaCondition):
    """
    This class returns strain stress related to torque applied by the instron.
    """

    def __init__(self):
        self.section = 10. * 2  # Specimen section in mm^2 (in order to have MPa below)

    def evaluate(self, value):
        """
        Evaluates tau(MPa), then makes displacement if tau hasnt reached a certain maximum.
        """

        value['tau(MPa)'] = (np.asarray(value['Force(N)']) / self.section).tolist()
        return value


def eval_offset(device, duration):
    timeout = time.time() + duration  # duration secs from now
    print 'Measuring offset (%d sec), please be patient...' % duration
    offset_channels = [[] for i in xrange(device.nb_channels)]
    offsets = []
    while True:
        mesures = device.get_data()[1]
        for i in xrange(len(offset_channels)):
            offset_channels[i].append(mesures[i])

        if time.time() > timeout:
            for i in xrange(len(offset_channels)):
                offsets.append(-np.mean(offset_channels[i]))
            print 'offsets:', offsets
            break
    return offsets


try:

    # Version avec labjack comme sensor uniquement. On recupere effort et deplacement
    labjack_device = crappy2.sensor.LabJackSensor(channels=[0, 1], gain=[0.15, 2000], offset=[0, 0])

    offsets = eval_offset(labjack_device, offset_time)
    labjack_device.close()
    # Labjack to acquire data (force, deplacement)
    labjack_device = crappy2.sensor.LabJackSensor(channels=[0, 1], gain=[0.15, 2000], offset=offsets, mode='streamer',
                                                  scan_rate_per_channel=10000, scans_per_read=5000)

    # EFFORT ET DEPLACEMENT

    # Blocks
    streamer = crappy2.blocks.Streamer(sensor=labjack_device, labels=['t(s)', 'Deplacement(mm)', 'Force(N)'], mean=10)

    grapher_force = crappy2.blocks.Grapher(('t(s)', 'tau(MPa)'), window_pos=(1920, 0),
                                           length=200)
    grapher_deplacement = crappy2.blocks.Grapher(('t(s)', 'Deplacement(mm)'), window_pos=(640, 0), length=200)
    saver = crappy2.blocks.Saver(path_measures_instron + 'ep_poubelle.csv', stamp='date')

    # Links

    link_to_force = crappy2.links.Link(name='to_force', condition=EvalStress())
    link_to_deplacement = crappy2.links.Link(name='to_deplacement')
    link_to_save = crappy2.links.Link(name='to_save', condition=EvalStress())

    # Linking

    streamer.add_output(link_to_force)  # > Vers les graphs
    streamer.add_output(link_to_deplacement)
    streamer.add_output(link_to_save)  # > Vers le saver

    grapher_deplacement.add_input(link_to_deplacement)
    grapher_force.add_input(link_to_force)
    saver.add_input(link_to_save)
    grapher_deformation = crappy2.blocks.Grapher(('t(s)', 'Deformation(%)'), window_pos=(0, 0), length=20)

    # link_to_deformation = crappy2.links.Link(name='to_deformation')

    # compacter.add_output(link_to_deformation)

    # grapher_deformation.add_input(link_to_deformation)

    ## CAMERA

    # Blocks
    camera = crappy2.blocks.StreamerCamera("Ximea", numdevice=0, freq=80, save=True,
                                           save_directory=path_measures_instron + 'Images_poubelle' + string_stamp + '/',
                                           xoffset=0, yoffset=0, width=2048, height=2048)
    displayer = crappy2.blocks.CameraDisplayer(framerate=10)

    # Links
    link_camera_to_displayer = crappy2.links.Link(name="link_camera_to_displayer")

    # Linking
    camera.add_output(link_camera_to_displayer)
    displayer.add_input(link_camera_to_displayer)
    raw_input("ready? Press ENTER")

    t0 = time.time()

    for instance in crappy2.blocks.MasterBlock.instances:
        instance.t0 = t0

    for instance in crappy2.blocks.MasterBlock.instances:
        instance.start()  # Waiting for execution

except KeyboardInterrupt:
    for instance in crappy2.blocks.MasterBlock.instances:
        instance.stop()
except Exception:
    raise
