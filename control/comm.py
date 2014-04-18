# comm.py - The module by which the control program communicates with the rover
# program.


import sys
import queue
from enum import IntEnum

#import numpy as np
import serial

import aux


MAX_DATA_FRAME_LEN = 100
DEFAULT_SERIAL_PORT = "/dev/tty.ElementSerial-ElementSe"


ser = None  # The serial connection to the rover.



class Signal(IntEnum):
    """ Different control signals to be sent/received as bytes in a message. """
    null = 0
    start = 1  # Start of message
    stop = 2   # End of message



class Message(IntEnum):
    """ Identifies different message types. """
    error = 3
    ping = 4
    echo = 5
    command = 6



class Subsys(IntEnum):
    """ Identifies different subsystems in messages. """
    lcd = 0
    oi = 1
    sonar = 2
    servo = 3
    ir = 4
    rng = 5




def tx_mesg(t, subsys = None, command = None, data = None):
    """ Sends a message to the rover as described by the arguments.

    - `t` must be a `Message`. This is the message type of the message to be
      sent.
    - `subsys` must be `None` or a `Subsys`. This is the value to be sent
      in the subsystem ID byte. If this is `None`, then no such byte will be
      sent in this message.
    - `command` is either `None` or an int that is a valid command code (of the
      given `subsys`. This is the value to be sent in the command ID byte. If
      this is `None`, then no such byte will be sent in this message. `command`
      is `None` if and only if `subsys` is `None`. 
    - `data` must be either `None` or a `bytes` object. This is the data to be
      sent in the sequence of data frames. In the case that this is `None`, no
      data frames will be sent.

    The message being sent will illicit a subsequent response message (of the
    same type). Reading this response should be handled by `rx_mesg()`.

    You should expect that no checks of correctness are performed on the args.
    If you pass garbage to this function, garbage may well be sent to the rover.
    """

    global ser
    b = bytearray(1)

    # Some validation for function arguments:
    if type(t) != Message:
        raise Exception()
    if subsys != None and type(subsys) != Subsys:
        raise Exception()

    # `subsys` is `None` iff `command` is `None`:
    if subsys == None and command != None:
        raise Exception()
    if subsys != None and command == None:
        raise Exception()

    b[0] = Signal.start
    ser.write(b)
    b[0] = t
    ser.write(b)

    if subsys is not None:
        b[0] = subsys
        ser.write(b)
        b[0] = command
        ser.write(b)
        if data is not None:
            ser.write(frame_data(data))

    b[0] = Signal.stop
    ser.write(b)



def rx_mesg(t, subsys = None, command = None, has_data = False):
    """ Recieves a message from the rover, and expects it to have the format
    specified by the given arguments.

    - `t` must be a `Message`. This is the expected message type of the
      message being received.
    - `subsys` must be `None` or a `Subsys`. This is the expected Subsystem
      ID of the message being received. If this is `None`, then no Subsystem ID
      byte is expected.
    - `command` must be `None` or an int that is a valid command code of the
      given `subsys`. This is the expected value of the Command ID byte of the
      message being received. Command is `None` if and only if `subsys` is
      `None`. 
    - `has_data` must be a boolean indicating whether or not a sequence of data
      frames is expected in the message being received.

    This function returns any data that was included with the response message
    as a `bytes` object.

    If there isn't a timely response message, or if the response has
    unexpected features, an `Exception` is raised.
    """

    global ser

    # Set timeouts to be 1 second while reading each byte. If a timeout occurs
    # while trying to read one byte, then a bytes object of length zero will be
    # returned.
    ser.timeout = 1

    b = bytearray(1)

    n = ser.readinto(b)
    if n != 1 or b[0] != int(Signal.start):
        print(b)  # DEBUG
        raise Exception("Did not receive the expected Start Signal.")

    n = ser.readinto(b)
    if n != 1 or b[0] != t:
        raise Exception("Did not receive the expected Message ID.")

    n = ser.readinto()
    if subsys != None and (n != 1 or b[0] != subsys):
        raise Exception("Did not receive the expected Subsystem ID.")

    ser.readinto(b)
    if command != None and (n != 1 or b[0] != command):
        raise Exception("Did not receive the expected Command ID.")

    if has_data:
        rv = read_data()

    if int(ser.read()) != Signal.stop:
        raise Exception("Did not receive the expected Stop Signal.")

    ser.timeout = None  # Disable timeouts.




def frame_data(d):
    """ A helper function that takes the bytes object `d` and returns a `bytes`
    object with added data framing bytes. """

    # The number of full frames to be sent:
    full_frames = len(d) // MAX_DATA_FRAME_LEN

    # The final partially-full frame to be sent:
    partial_frame_len = len(d) % MAX_DATA_FRAME_LEN
    has_partial_frame = False if partial_frame_len == 0 else True

    frames = []
    for i in range(full_frames):
        # `start` is index of first byte of `d` to be copied into this `frame`.
        start = i * MAX_DATA_FRAME_LEN
        frame = bytearray(MAX_DATA_FRAME_LEN + 3)

        # Add data and framing info to this `frame`:
        frame[0] = MAX_DATA_FRAME_LEN
        frame[1: 1 + MAX_DATA_FRAME_LEN] = d[start: start + MAX_DATA_FRAME_LEN]
        frame[MAX_DATA_FRAME_LEN + 1] = MAX_DATA_FRAME_LEN
        frame[MAX_DATA_FRAME_LEN + 2] = True

        # Add this newly formed frame to the list of frames to be sent.
        frames.append(frame)

    if has_partial_frame:
        start = full_frames * MAX_DATA_FRAME_LEN
        frame = bytearray(partial_frame_len + 3)

        frame[0] = partial_frame_len
        frame[1 : 1 + partial_frame_len] = d[start : ]
    
    # Set the last byte of the last frame (whether full or partial) to indicate
    # that there are no more frames.
    frames[-1][-1] = False

    return b''.join(frames)



def read_data():
    """ Reads data frame and returns data bytes. """
    
    global ser

    global ser

    keep_going = True
    num_good_bytes = 0
    temp_bytes_list = []
    data_bytes_list = []
    
    # Keep reading data frames until there are no more data frames:
    while keep_going:
        frame_length = ser.read()
        
        temp_bytes_list = [0]*frame_length

        if ser.readinto(temp_bytes_list) != frame_length:
            raise Exception("Did not receive all expected data bytes.")
        
        # Add only the good bytes to the list:
        num_good_bytes = ser.read()
        data_bytes_list += temp_bytes_list[0:num_good_bytes]
        
        # Check to see if we should keep going:
        keep_going_byte = ser.read()
        
        if keep_going_byte == b'\x00':
            keep_going = False
        elif keep_going_byte != b'\x01':
            raise Exception("Invalid \"Keep Going\" byte.")

    return b''.join(data_bytes_list)


def heartbeat():
    """ Sends ping and receives ping signals to the rover indefinitely. """

    while True:
        ping()
        sys.stdout.write('.')
        sleep(1)



def ping():
    aux.stop()
    tx_mesg(Message.ping)
    rx_mesg(Message.ping)
    aux.start()
    


def echo(s):
    """
    Sends a message of type `echo` along with the supplied string `s`.
    Expects an identical message to be returned, i.e., a message of type `echo`
    along with this same string `s`.
    """

    b = bytes(s, 'utf-8')
    tx_mesg(Message.echo, data = b)
    rv = rx_mesg(Message.echo, data = True)
    if b != rv:
        raise Exception("A different string was returned from the rover.")



def handle_rover_error(data):
    """
    Interprets the data segment of an error sent from the `rover` and responds
    to it as appropriate.
    """

    raise NotImplementedError()




def tty(stream):
    """
    Indefinitely writes to `stream` (a subclass of `io.IOBase`) whatever data
    is coming from the rover.
    """

    global ser

    while True:
        stream.write(ser.read())




def connect(port = DEFAULT_SERIAL_PORT):

    """ Opens the serial connection on the given `port` and starts the `aux`
    thread to listen for any unexpected (i.e. un-prompted) messages. """

    global ser
    ser = serial.Serial(port, baudrate = 57600, stopbits = serial.STOPBITS_TWO)
    if ser == None:
        raise Exception("Could not connect to serial port.")

    # Clear whatever data might already be in the serial buffer.
    ser.timeout = 0
    while ser.read() != b'':
        pass

    ser.timeout = 1
    #DEBUG
    #aux.start(ser)  # Sends signal that allows `aux` to listen for messages.




def disconnect():
    global ser
    aux.stop()
    ser.close()
    ser = None
    aux = None
    q = None
    



def main():
    """
    if len(sys.argv) != 2:
        sys.stderr.write("Expected one argument, the path of the serial tty.")
        exit()
    """

    connect()
    ping()
    """
    # Manually Issue and Read.
    ser.write(b'\x01')
    ser.write(b'\x04')
    ser.write(b'\x02')
    print(ser.read())
    print(ser.read())
    print(ser.read())
    """


if __name__ == "__main__":
    main()
