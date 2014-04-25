/*
 * movement.c
 * Contains only methods related to movement
 * Created: 1/26/2014 2:53:34 PM
 *  Author: flaviarc & DiamondStone
 */ 


// TODO: refactor out the use of global variable


enum {
	full_distance = 0,
	left_bumper = 1,
	right_bumper = 2,
	left_and_right_bumper = 3,
	front_left_cliff = 4,
	front_right_cliff = 5,
	left_cliff = 6,
	right_cliff = 7,
	// TODO: the rest of these have not been implemented
	white_tape = 8,
	left_wheel = 9,
	right_wheel = 10,
	middle_wheel = 11
} stop_flag;

#include "open_interface.h"
#include "movement.h"
#include "lcd.h"
#include "util.h"
#include <stdbool.h>
#include <math.h>


// Returns 0 if a bump is detected while making a course correction.
// Otherwise, returns a positive value.
move_t course_correction(oi_t *sensor_data)
{
	oi_update(sensor_data);
	// TODO: check for bumps and other move failures.
	move_t move = {.x = 0, .y = 0, .angle = 0, .success = 0};
	
	int backup_dist = 150;
	int lateral_dist= 250;
	oi_set_wheels(0, 0);  // stop
	
	move.y = move_dist(sensor_data, -backup_dist, 300);

	// DEBUG:
	lprintf("left: %i, right: %i", sensor_data->bumper_left, sensor_data->bumper_right);

	// If left bumper only detected, then CCW 90 degrees.
	// If right bumper only detected, then turn CW 90 degrees.
	// If both bumpers detected, then CCW 90 degrees.
	int angle = (stop_flag == left_bumper || stop_flag == left_and_right_bumper) ? -90 : 90;
	
	turn(sensor_data, angle);	
	move_dist(sensor_data, lateral_dist,300);
	move.x = angle > 0 ? lateral_dist : -lateral_dist;
	turn(sensor_data, -angle);  // turn back to the original direction, so move.angle should be 0
	move.success = 1;
	
	lcd_clear();
	return move;
}


int navigate_dist(oi_t *sensor_data, int dist) {
	int dist_traveled = 0;
	int count_moves = 0;
	move_t move = {.x = 0, .y = 0, .angle = 0};
	while (dist_traveled < dist) {
		if (count_moves != 0) {
			
			move = course_correction(sensor_data);
			if (move.success == 0) {
				return -1;  // course correction failed; bump detected while making course correction
			}
		}
		dist_traveled += move.y;  // adds a negative number
		dist_traveled += move_dist(sensor_data, dist - dist_traveled,300);
		count_moves++;
	}
	
	return count_moves - 1; // the number of bumps detected
}

///Function that detects the white strips on the floor, returns true if the white tape was detected, false otherwise
bool detectWhite (){
	
}

// distance accumulated will be zeroed before return.
// Only while attempting to move forward should it stop for the bumper sensors.
int move_dist(oi_t *sensor_data, int dist, int spd) {
	oi_update(sensor_data);
	int sum = 0;
	int velocity = (dist < 0) ? -spd: spd;  // move at indicated speed
	oi_set_wheels(velocity, velocity);
	
	//If attempting to go forward
	if (dist > 0) {
		while (sum < dist) {
			oi_update(sensor_data);
			sum += sensor_data->distance; //adds a positive value
			if (sensor_data->bumper_left || sensor_data->bumper_right) {
				
				//Bumper detection
				if (sensor_data->bumper_left && sensor_data->bumper_right) {
					stop_flag = left_and_right_bumper;
				} else if (sensor_data->bumper_left) {
					stop_flag = left_bumper;
				} else if (sensor_data->bumper_right) {
					stop_flag = right_bumper;
				}
				
				//cliff detection
				else if (sensor_data->cliff_left_signal){
					stop_flag = left_cliff;
				}
				else if (sensor_data->cliff_right_signal){
					stop_flag = right_cliff;
				}
				else if (sensor_data->cliff_frontleft_signal){
					stop_flag = front_left_cliff;
				}
				else if (sensor_data->cliff_frontright_signal){
					stop_flag = front_right_cliff;
				}
				
				//white strip detection
				else if (detectWhite()){
					stop_flag = white_tape;
				}
				
				break;
			}
			
			if (stop_flag){ //if one of the bumpers was activated, stop moving
				//#warning "Still needs to send back a signal that specifies that a bumper was activated"
				txq_enqueue(stop_flag);
				txq_enqueue(sum);
				txq_drain();
				return sum; //return the distance traveled before hitting the object
			}
		}

	//If attempting to go backwards
	} else if(dist < 0) {
		while (sum > dist) {
			oi_update(sensor_data);
			sum += sensor_data->distance;  // adds a negative value
		}
	} else {
		// dist == 0, so do nothing
	}
	
	oi_set_wheels(0, 0); // stop
	// TODO: maybe add a delay here before reading the last distance update 
	oi_update(sensor_data);
	sum += sensor_data->distance;
	return sum;
}


int turn(oi_t *sensor_data, int angle) {
	oi_update(sensor_data);
	int sum = 0;
	int speed = 100;
	// positive angle is CCW, and negative angle is CW.
	if (angle < 0) {
		// right is negative, left is positive
		oi_set_wheels(-speed, speed);
		while (sum > angle) {
			oi_update(sensor_data);
			sum += sensor_data->angle;
		}
	} else if (angle > 0) {
		// right is positive, left is negative
		oi_set_wheels(speed, -speed);
		while (sum < angle) {
			oi_update(sensor_data);
			sum += sensor_data->angle;
		}
	} else {
		// angle == 0, so do nothing
	}
	
	oi_set_wheels(0,0);
	
	return sum;
}

