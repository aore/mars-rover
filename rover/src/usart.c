
// Code adapted from Atmel Data sheet page 176, 180. Changed to use macros that refer to the USART unit 0.

#include "usart.h"
#include <avr/io.h>
#include <avr/interrupt.h>
#include <stdbool.h>

void usart_init(uint8_t type)
{
	unsigned int baud;
	bool double_rate = 0;
	if (type == 0) {
		// configure for serial connection
		baud = 25;  // Code for baud rate 38.4k without double speed.
	} else if (type == 1) {
		// configure for bluetooth connection
		baud = 34;  // Code for baud rate 57.6k at double speed.
		double_rate = 1;
	} else {
		return;  // error: type not defined
	}
	
	/* Set baud rate */
	UBRR0H = (unsigned char)(baud>>8);
	UBRR0L = (unsigned char)baud;

	/*Enable double speed? */
	UCSR0A = double_rate ? 0b00000010 : 0b00000000;

	/* Enable receiver and transmitter */
	 UCSR0B = 0b00011000;
	/* Set frame format: 8data, 2stop bit */
	UCSR0C = 0b00001110;
}

uint8_t usart_rx(void)
{
	/* Wait for data to be received */
	while ( !(UCSR0A & (1<<RXC0)) )
	;
	/* Get and return received data from buffer */
	return UDR0;
}

void usart_tx(uint8_t data)
{
	/* Wait for empty transmit buffer */
	while ( !( UCSR0A & (1<<UDRE)) )
		;
	/* Put data into buffer, sends the data */
	UDR0 = data;
}
	
void usart_tx_buf(char *buf) {
	for (char *cur = buf; *cur != '\0'; cur++) {
		usart_tx(*cur);
	}
}


void usart_RX_ISR_enable() {
	UCSR0B |= 0b10000000;
}


void usart_RX_ISR_disable() {
	UCSR0B &= 0b01111111;
}
