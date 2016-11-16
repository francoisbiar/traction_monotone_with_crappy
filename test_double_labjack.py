import crappy2
import time

labjack_sensor = crappy2.sensor.LabJackSensor(channels=['AIN0', 'AIN1'], gain=1, offset=0)
labjack_actuator = crappy2.actuator.LabJackActuator(channel='TDAC0', gain=0.1, offset=0)
position = 0
try:
    while True:
        acquisition = labjack_sensor.get_data()
        time.sleep(0.01)
        print 'acquisition:', acquisition
        labjack_actuator.set_cmd(position)
        print 'command:', position
        position += 0.1
except:
    labjack_actuator.set_cmd(0)
