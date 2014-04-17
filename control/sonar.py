# sonar.py

import comm
from enum import IntEnum


class SonarCommand(IntEnum):
    init = 0
    calibrate = 1
    readings = 2



def init():
    """
    Initializes the sonar subsystem for use. Also activates the sonar, i.e.,
    the sonar state is made to be "on".
    """

    tx_mesg(Message.command, Subsys.sonar, SonarCommand.init, None)
    rx_mesg(Message.command, Subsys.sonar, SonarCommand.init, False)




def calibrate():
    """
    Initiates the `control`-operated calibration routine of the sonar subsystem.
    """

    raise NotImplementedError()



def readings(n, raw = True, rand = False, timestamps = False):
    """
    Gets an `ndarray` of sonar readings from the `rover`.

    Expects `n` to be an unsiged integer. Expects both `rand` and `timestamps`
    to be booleans.

    If `n` is a positive integer, then `rover` should stream `n` independent
    sonar readings back to `control`. If `n` is zero, then independent IR
    readings should be streamed back to `control` until `control` sends a
    command to stop.

    If `raw` is `True`, then the raw ADC output is streamed back to `control`
    rather than the approximated distance as calculated by `rover`.

    If `rand` is `True`, then readings will not be taken as often as possible.
    Rather, each reading should delayed by a random amount of time before it
    is started.

    If `timestamps` is `True`, then timestamps indicating when a reading was
    taken are streamed back to `control` along with the readings themselves.
    """

    raise NotImplementedError()
