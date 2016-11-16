import crappy2
from time import sleep, time

montant = True

labjack = crappy2.technical.LabJackTechnical(sensor={'channels': ['AIN0', 'AIN1']}, actuator={'channel': 'TDAC0', 'gain': 1, 'offset': 0})

depart = 0
arrivee = 10.
step = 0.01
labjack.set_cmd(depart)
step_actuel = depart
descente = False
t0 = time()
while True:
    try:
        if step_actuel < arrivee and not descente:
            step_actuel += step
            print 'montee, step actuel:', step_actuel
        elif int(step_actuel) == arrivee:
            sleep(5)
            step_actuel -= step
            print 'stabilise, step actuel', step_actuel
            descente = True
        elif step_actuel > 0 and descente:
            print 'descente, step_actuel', step_actuel
            step_actuel -= step
        else:
            break

        labjack.set_cmd(step_actuel)
        print labjack.get_data()
        sleep(0.01)
    except Exception as e:
        print e
        labjack.close()
        break

print time() - t0
