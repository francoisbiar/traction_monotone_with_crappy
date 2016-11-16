# coding: utf-8
import crappy2
import time
import numpy as np

#  General parameters for whole program

loop_frequency = 50 # Acquisition and command frequency (Hz)
offset_time = 10  # Time during which offset is measured on labjack
tau_max = 900  # Limit before discharging
tempo_extremas = 5  # Time (secs) during which the instron maintains position (at the beginning, and when tau_max reached)
displacement_velocity = 0.01  # in mm/s.
amplitude_instron = 1  # in mm/V, it is what is set in instron consigne
path_measures_instron = '/home/francois/Essais/005_Traction_Specimen_1mois/28sept_Instron_command/' + raw_input(
    'Nom_fichier') + '/'

#  Program and crappy initialization, do not change following

crappy2.blocks.MasterBlock.instances = []  # Init masterblock instances

timestamp = time.localtime()
string_stamp = "%i_%i_%i_%ih%i" % (timestamp.tm_year, timestamp.tm_mon,
                                   timestamp.tm_mday, timestamp.tm_hour,
                                   timestamp.tm_min)


class EvalStress(crappy2.links.MetaCondition):
    """
    This class returns strain stress related to torque applied by the instron.
    """

    def __init__(self):
        self.section = 10. * 3.89  # Specimen section in mm^2 (in order to have MPa below)
        # self.section = 8. * 3.  # Specimen eprouvette avec tetes
        
        self.tau_max = float(tau_max)  # For limiting the command
        self.step = displacement_velocity / loop_frequency  #
        # print 'self.step:', self.step
        self.nb_points_averaging = 10  # Points to compute the running mean
        self.tempo_limit = tempo_extremas  # Temporisation, seconds (at start, and at tau_max)
        
        # Values initialization, do not change following
        self.position = 0.
        self.unload = False
        self.tau_liste = []
        self.tau_averaging = [0]
        self.t_reached = 0
        self.over = False

    def evaluate(self, value):
        """
        Evaluates tau(MPa), then makes displacement if tau hasnt reached a certain maximum.
        """
        value['tau(MPa)'] = value['Force(N)'] / self.section
        tau = value['tau(MPa)']
        self.tau_liste.append(tau)

        if len(self.tau_liste) == self.nb_points_averaging:
            self.tau_averaging.append(np.mean(self.tau_liste))
            self.tau_liste = []

        
        value['tau_mean(MPa)'] = self.tau_averaging[-1]
        

        if (time.time() - t0) > self.tempo_limit and not self.over:
            if self.tau_averaging[-1] < self.tau_max and not self.unload:
                self.position += self.step
                comedi_actuator.set_cmd(self.position)

            elif tau > self.tau_max and not self.unload:
                print "Limite atteinte ! Dechargement dans %d secondes..." % self.tempo_limit
                self.unload = True
                self.t_reached = time.time()

            elif self.unload and (time.time() - self.t_reached) > self.tempo_limit:
                    self.position -= self.step
                    comedi_actuator.set_cmd(self.position)
                    if self.position < 0.:
                        self.over = True
                        print 'FIN DU PROGRAMME. VEUILLEZ QUITTER.'
                                                
            reste = round((100 * self.position) % (100 * 0.01), 10)
            # print 'reste: %f, commande actuelle: %f' %(reste, self.position)
            if reste == 0.0 or reste == 1.0:
                print 'position actuelle: %.2f V' % self.position

        return value


def eval_offset(device, duration):
    timeout = time.time() + duration  # 60 secs from now
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
    labjack_device = crappy2.sensor.LabJackSensor(channels=[0, 1, 2], gain=[0.5, 2500, 0.3], offset=[0, 0 ,0])
    offsets = eval_offset(labjack_device, offset_time)
    labjack_device.close()
    # Labjack to acquire data (force, deplacement)
    labjack_device = crappy2.sensor.LabJackSensor(channels=[0, 1, 2], gain=[0.5, 2500, 0.3], offset=offsets)
    # Comedi to set the command (deplacement)
    comedi_actuator = crappy2.actuator.ComediActuator(device='/dev/comedi0', channel=0, gain=amplitude_instron, offset=0, range_num=1) #offset=-(4063*6000.)/(2977*2000.))
    comedi_actuator.set_cmd(0)
    # labjack_actuator = crappy2.actuator.LabJackActuator(channel='TDAC0', gain=1, offset=0)
    # sensor_args = {'channels': ['AIN0', 'AIN1']}
    # labjack_device = crappy2.technical.LabJackTechnical(sensor=sensor_args)
    # actuator_args = {'channel': 'TDAC0', 'gain': 2, 'offset': 2}
    # sensor_args = {'channels': ['AIN0', 'AIN1'], 'gain': [1, 1], 'offset': offsets, 'chan_range': 10}
    # labjack_device = crappy2.technical.LabJackTechnical(sensor=sensor_args, actuator=actuator_args)

    # EFFORT ET DEPLACEMENT

    # Blocks
    measurebystep = crappy2.blocks.MeasureByStep(sensor=labjack_device, labels=['t(s)', 'Deplacement(mm)', 'Force(N)', 'Deformation(%)'], freq=loop_frequency)
    grapher_force = crappy2.blocks.Grapher(('t(s)', 'tau(MPa)'), ('t(s)', 'tau_mean(MPa)'), window_pos=(1920, 0), length=20)
    grapher_deplacement = crappy2.blocks.Grapher(('t(s)', 'Deplacement(mm)'), window_pos=(640, 0), length=20)
    grapher_deformation = crappy2.blocks.Grapher(('t(s)', 'Deformation(%)'), window_pos=(0, 0), length=20)

    saver = crappy2.blocks.Saver(path_measures_instron + string_stamp + '.csv')
    compacter = crappy2.blocks.Compacter(25)

    # Links
    link_to_compacter = crappy2.links.Link(name='to_compacter', condition=EvalStress())
    link_to_force = crappy2.links.Link(name='to_force')
    link_to_deplacement = crappy2.links.Link(name='to_deplacement')
    link_to_deformation = crappy2.links.Link(name='to_deformation')
    link_to_save = crappy2.links.Link(name='to_save')

    # Linking
    measurebystep.add_output(link_to_compacter)  # > Mesures
    compacter.add_input(link_to_compacter)
    compacter.add_output(link_to_force)  # > Vers les graphs
    compacter.add_output(link_to_deplacement)
    compacter.add_output(link_to_deformation)

    compacter.add_output(link_to_save)  # > Vers le saver

    grapher_deplacement.add_input(link_to_deplacement)
    grapher_force.add_input(link_to_force)
    grapher_deformation.add_input(link_to_deformation)
    saver.add_input(link_to_save)

    ## CAMERA

    # Blocks
    camera = crappy2.blocks.StreamerCamera("Ximea", numdevice=0, freq=80, save=True,
                                           save_directory=path_measures_instron + 'Images_' + string_stamp + '/',
                                           xoffset=0, yoffset=0, width=2048, height=2048)
    displayer = crappy2.blocks.CameraDisplayer(framerate=5)

    # Links
    link_camera_to_displayer = crappy2.links.Link(name="link_camera_to_displayer")

    # Linking
    camera.add_output(link_camera_to_displayer)
    displayer.add_input(link_camera_to_displayer)

    # # EXTENSOMETRIE
    #
    # # Blocks
    # correl_images = crappy2.blocks.VideoExtenso(camera="ximea", numdevice=0, xoffset=0, yoffset=0, width=2048,
    #                                             height=2048, white_spot=False,
    #                                             display=False, update_tresh=False, labels=None, security=False,
    #                                             save_folder=path_measures_instron + '/Images/')
    #
    # saver_extenso = crappy2.blocks.Saver(path_measures_instron + string_stamp + 'extenso.csv')
    # compacter_extenso = crappy2.blocks.Compacter(10)
    #
    # # Links
    # link_extenso = crappy2.links.Link(name='extenso')
    # link_to_def = crappy2.links.Link(name='to_def')
    #
    # # Linking
    # correl_images.add_output(link_extenso)
    # link_to_save_extenso = crappy2.links.Link(name='to_save_extenso')
    # compacter_extenso.add_input(link_extenso)
    #
    # compacter_extenso.add_output(link_to_def)
    # compacter_extenso.add_output(link_to_save_extenso)
    # saver_extenso.add_input(link_to_save_extenso)
    # graph_extenso = crappy2.blocks.Grapher(('t(s)', 'Exx(%)'), ('t(s)', 'Eyy(%)'))
    # graph_extenso.add_input(link_to_def)

    ## Definition de la commande, qui doit etre synchronisée avec la mesure

    # trigger_measures = crappy2.links.Link(name='trigger')
    # labjack_actuator.set_cmd(0)

    # measurebystep.add_input(trigger_measures)

    # Suite du programme : commande simple
    raw_input("ready? Now it's time to click on DEPART in the instron software command")

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
