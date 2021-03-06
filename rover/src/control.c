/*
 * control.c
 *
 * Created: 4/13/2014 3:48:46 PM
 *  Author: asr
 */

//NOTE: If you want the debugging messages to appear, it is necessary to change debug's value in 
//mars-rover.h file.

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>


#include "util.h"
#include "usart.h"
#include "IR.h"
#include "open_interface.h"
#include "sonar.h"
#include "servo.h"
#include "txq.h"
#include "control.h"
#include "r_error.h"
#include "lcd.h"
#include "mars-rover.h";


control_t control;  // Lone instance of the `control` struct.



/**
 * Reads a single frame from the current message being received on the serial
 * connection into `control.data`. Returns whether another frame is coming.
 * Note that the *real* data length of this frame is what ends up being stored
 * `control.data_len`.
 *
 * To be clear, whatever was previously stored in `control.data` and
 * `control.data_len` is clobbered.
 */
bool rx_frame()
{
	bool rv;

	// Get the (expected) length of this data frame:
	control.data_len = usart_rx();
	if(control.data_len > DATA_FRAME_MAX_LEN) {
		r_error(error_bad_message, "Data frame length must not exceed DATA_FRAME_MAX_LEN");
	}

	
	
		// Copy bytes coming from serial into `control.data`.
		if (debug) lcd_putc('['); // DEBUG
		int i = 0;
		for (i = 0; i < control.data_len; i++) {
			control.data[i] = usart_rx();
			if (debug) lcd_putc('.'); // DEBUG
		}
		if (debug) lcd_putc(']'); // DEBUG

	// Notice that `i` now holds the expected data frame length.
	control.data_len = usart_rx();
	if (debug){
		lcd_putc(control.data_len + '0');  // DEBUG
	}
	if (control.data_len > i) {
		r_error(error_bad_message, "The real data frame length cannot be larger than the expected data frame length.");
	}

	// The last byte in this frame indicates whether another frame is coming:
	rv = usart_rx();
	if (debug){
		lcd_putc(rv ? 'y' : 'n');  // DEBUG
	}
	return rv;
}



/**
 * Adds the complete contents of `control.data` as a frame, along with
 * the appropriate framing bytes to the `txq`. The argument `another_frame`
 * indicates whether the another frame byte should be either 0 or 1.
 */
void tx_frame(bool another_frame)
{
	txq_enqueue(control.data_len);
	for (int i = 0; i < control.data_len; i++) {
		txq_enqueue(control.data[i]);
	}
	txq_enqueue(control.data_len);
	txq_enqueue(another_frame);
}





/**
 * A function to handle requests messages for readings from either sonar or IR.
 * This assumes that none of the response message has been sent to the queue.
 */
void dist_reading_handler(subsys_t subsys)
{
	// The interface used to access the request parameters encoded in the
	// data frame of the received message:
	struct {
		uint16_t n;		// The number of readings to be performed.
		bool raw;		  // Whether the data should be raw or converted.
		bool random;	   // Ignore this for now.
		bool timestamps;   // Whether the data should include timestamps.
	} request;

	// Point the function pointers to the subsystem indicated by `subsys`:
	int (*raw_reading)();
	int (*conv_reading)();

	if (subsys == subsys_ir)
	{
		raw_reading = ir_raw_reading;
		conv_reading = ir_reading;
	}
	else if (subsys == subsys_sonar)
	{
		raw_reading = sonar_raw_reading;
		conv_reading = sonar_reading;
	}
	else
	{
			r_error(error_unknown, "`dist_reading_handler()` was called with a "
										  "subsystem other than IR or sonar.");	
	}


	// Check whether the data frame of the request message was valid:
	if (rx_frame() == true)
	{
		r_error(error_frame, "A distance reading request message should not "
												 "have multiple data frames.");
	}
	if (control.data_len != sizeof(request)) 
	{
		r_error(error_frame, "Did not receive the anticipated number of data "
							 "bytes in the distance reading request message.");
	}

	// The request that is in `control.data` has been validated. Start
	// response. First, make a copy of the request so it doesn't get clobbered.
	memcpy(&request, control.data, sizeof(request));

	
	// Number of raw readings to be put into a response data frame:
	#define RAW_READINGS_PER_FRAME (DATA_FRAME_MAX_LEN / sizeof(uint16_t))

	// Number of converted data readings to be put into a response data frame:
	#define CONV_READINGS_PER_FRAME (DATA_FRAME_MAX_LEN / sizeof(float))

	// The interface for interpreting `control.data` as an array into which
	// we put either raw data or converted data:
	union {
		uint16_t raw[RAW_READINGS_PER_FRAME];
		float conv[CONV_READINGS_PER_FRAME];
	} *response = (void *) &control.data;

	uint8_t i;  // An index into an array of `response`.
	uint16_t readings_sent = 0;

	// Each iteration generates a response frame of readings.
	while (readings_sent < request.n)
	{
		i = 0;  // Index into a frame of data via our `response` pointer.

		if (request.raw)
		{
			// Place as many raw readings into `control.data` as will fit.
			while (i < RAW_READINGS_PER_FRAME && readings_sent < request.n) {
				response->raw[i] = raw_reading();
				readings_sent++;
				i++;
			}
		}
		else
		{
			// Place as many converted readings into `control.data` as will fit.
			while (i < CONV_READINGS_PER_FRAME && readings_sent < request.n) {
				response->conv[i] = conv_reading();
				readings_sent++;
				i++;
			}
		}

		// Frame and send the contents of `control.data` to `control`, and
		// indicate whether a subsequent frame must still be sent as well:
		control.data_len = i * (request.raw ? sizeof(uint16_t) : sizeof(float));
		tx_frame(readings_sent < request.n);
		txq_drain();
	}
}




static void ping_handler() 
{
	; // Do nothing, since there is nothing else to be added to the response.
}


/**
 * This should be called after the current message has been determined to be of
 * type `mesg_echo`. It reads the data stored in the message's sequence of
 * data frames and responds with a message whose data frames contain the same
 * data.
 */
static void echo_handler()
{
	// In each iteration, a data frame is de-framed
	bool another_frame = true;
	while (another_frame)
	{
		another_frame = rx_frame();
		tx_frame(another_frame);
		txq_drain();
	}
}


/**
 * This function controls servo movement, sonar collection and IR collection combined into one. 
 * Should replace dist_reading_handler().
 */
void scan_handler()
{
	// Warning: The constants used in this function are tuned specifically to the
	// protocol, and are brittle to changes.
	
	// Note that the angles are actually transmitted as pulse widths, not angles.
	// Note that the maximum number of angles that can be transmitted is 200.
	uint16_t angles[200];
	
	// The interface by which we write the readings into `control.data` for transmission:
	uint16_t *tx_data = (void *) &control.data;
	
	// Copy the angles coming from `control` into the `angles` array:
	bool another_rx_frame = true;
	int num_angles = 0;
	int num_rx_frames = 0;
	while (another_rx_frame && num_rx_frames < 4) {
		another_rx_frame = rx_frame();
		num_angles += control.data_len / sizeof(uint16_t);
		memcpy(angles + (num_rx_frames * 50), &control.data, sizeof(control.data));
		num_rx_frames++;
	}
	
	if (num_rx_frames == 4 && another_rx_frame) {
		r_error(error_bad_message, "A scan request message had more than 4 data frames.");
	}
	
	lprintf("%d", num_angles);  // DEBUG


	// Generate a frame of data in each iteration. Every frame contains up to 100 bytes.
	// There are up to 50 readings total in a frame. At every angle 5 IR reading and 5
	// Sonar readings are stored into control.data.
	
	// Note: Very little time is given for the servo to move between iterations. So
	// the angles indicated by `angles` should be close to one another, i.e., the servo
	// should not have to jump very far in this short amount of time.
	
	// Move to the first angle, and give it plenty of time to get there:
	servo_pulse_width(angles[0]);
	wait_ms(1000);
	
	int a = 0;  // Counts the total number of angles sent.
	
	// Each iteration collects readings to fill up a data frame (i.e. readings from up
	// to five angles).
	while (a < num_angles)
	{
		int i = 0;	// Counts the number of angles included in a frame.
	
		// Each iteration collects 10 readings at a particular angle:
		while (i < 5 && a < num_angles)
		{
			servo_pulse_width(angles[a]);
			wait_ms(1);
			
			int j = 0;  // Counts the number of readings sent for this angle.
			while (j < 5) {
				tx_data[10 * i + j] = ir_raw_reading();
				j++;
			}
			while (j < 10) {
				tx_data[10 * i + j] = sonar_raw_reading();
				j++;
			}
			
			a++;
			i++;
		}
		
		// The number of bytes packed into this frame is: i (the number of angles put
		// into this frame), times 10 readings per angle, times 2 bytes per readings:
		control.data_len = i * 10 * 2;
		tx_frame(a < num_angles);
		
		txq_drain();
	}
}




/**
 * This should be called after the current message has been determined to be
 * of type `mesg_command`. It reads the Subsystem ID of the current message to
 * decide which subsystem should handle the rest of the message.
 */
static void command_handler()
{
	// Choices for functions to be called next. Notice that by the time that
	// any of these functions is called, a response message should have already
	// been started.
	static void (*subsystem_handlers[NUM_SUBSYS_CODES])() = {
		lcd_system,   // 0
		oi_system,	// 1
		sonar_system, // 2
		servo_system, // 3
		ir_system,	// 4
	};

	// Use the `subsys` code of the recieved message to choose the handler.
	uint8_t subsys = usart_rx();
	if ((subsys >= 0) && (subsys < NUM_SUBSYS_CODES)) {
		txq_enqueue(subsys);
		txq_drain();
		subsystem_handlers[subsys]();
	} else {
			lprintf("subsys received: %u", subsys); // TODO: remove
			r_error(error_bad_message, "Invalid subsystem ID.");
		
	}
}



static void seed_rng_handler() {
	#warning "TODO: seed_rng_handler() is not yet implemented"
}



/**
 * Reads the Message Type of the current message being received and calls
 * the appropriate handler.
 */
static void mesg_handler()
{
	// Choices for functions to be called next.
	static void (*mesg_handlers[NUM_MESG_CODES])() = {
		error_handler,	 // 0
		ping_handler,	  // 1
		echo_handler,	  // 2
		command_handler,   // 3
		seed_rng_handler,  // 4
		scan_handler,      //5
	};

	uint8_t mesg_id = usart_rx();
	if (0 <= mesg_id && mesg_id < NUM_MESG_CODES)
	{
		// Use the message type of the received message to choose the handler.
		// Also start a response message of the same message type.
		
		// TODO: remove "good" etc comments before committing; debugging oi.move()
		
		txq_enqueue(signal_start); // good
		txq_enqueue(mesg_id); // good; enqueues 3 for command_handler
		mesg_handlers[mesg_id](); 
		txq_enqueue(signal_stop);
		txq_drain();
	}
	else
	{
			r_error(error_bad_message, "Received an invalid Message ID byte.");
	}
}



/**
 * Calling this function will drop the rover into "control mode", in which the
 * rover gives over most of its autonomous functions to commands coming from
 * the remote control system.
 */
void control_mode()
{
	uint8_t byte;

   	lcd_init();
	init_push_buttons();

	sonar_init();
	ir_init();
	servo_init();
	oi_init(&(control.oi_state));

	usart_init();
	usart_drain_rx();
	txq_init();

	lcd_puts("Control Mode");
	wait_ms(1000);
	lcd_clear();

									  
	// Receive and handle messages from `control` indefinitely:
	while (true)
	{
		// Check for start byte indefinitely:
		byte = usart_rx();
		if (byte != signal_start) {
			sprintf(r_error_buf, "Received %u instead of expected start byte.", byte);
			r_error(error_txq, r_error_buf);
		}
		if (debug){
			lcd_putc('(');  // DEBUG: found start byte
		}
		mesg_handler();  // Calls the appropriate sequence of handlers.

		// Check for stop byte indefinitely:
		byte = usart_rx();
		if (byte != signal_stop) {
			sprintf(r_error_buf, "Received %u instead of expected stop byte.", byte);
			r_error(error_txq, r_error_buf);
		}
		if (debug){
			lcd_putc(')');  // DEBUG: found stop byte
		}
	}
}
