# oi.py

import comm
from enum import IntEnum


class OICommand(IntEnum):
    init = 0



def init():
    """
    Initializes the rover's open interface subsystem, that is, the open-
    interface over USART communication system between the ATmega128 and and the
    iRobot create.
    """

    tx_mesg(Message.command, Subsys.oi, OICommand.init, None)
    rx_mesg(Message.command, Subsys.oi, OICommand.init, False)




# TODO: Design other functions.
