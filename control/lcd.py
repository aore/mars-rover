# lcd.py

import comm
from enum import IntEnum


class LCDCommand(IntEnum):
    init = 0
    puts = 1
    clear = 2


def init():
    """ Initializes the rover's LCD subsystem for use.  """
    tx_mesg(Message.command, Subsys.lcd, LCDCommand.init, None)
    rx_mesg(Message.command, Subsys.lcd, LCDCommand.init, False)



def puts(s):
    """ Appends the given string `s` to the rover's LCD display. """
    b = bytes(s, 'utf-8')
    tx_mesg(Message.command, Subsys.lcd, LCDCommand.puts, b)
    rx_mesg(Message.command, Subsys.lcd, LCDCommand.puts, False)

    raise NotImplementedError



def clear():
    """ Clears the rover's LCD display. """
    tx_mesg(Message.command, Subsys.lcd, LCDCommand.clear, None)
    rx_mesg(Message.command, Subsys.lcd, LCDCommand.clear, False)
