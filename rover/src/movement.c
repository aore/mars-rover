/*
 * movement.c
 * Contains only methods related to movement
 * Created: 1/26/2014 2:53:34 PM
 *  Author: flaviarc & DiamondStone
 */ 


// TODO: refactor out the use of global variable


#include "open_interface.h"
#include "control.h"
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
	
	movement_data_t movement_data = move_dist(sensor_data, -backup_dist, 300);
	
	move.y = movement_data.travelled;

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
		movement_data_t move = move_dist(sensor_data, dist - dist_traveled,300);
		dist_traveled += move.travelled;
		count_moves++;
	}
	
	return count_moves - 1; // the number of bumps detected
}


// Distance accumulated will be zeroed before return.
// Only while attempting to move forward should it stop for the bumper sensors.
movement_data_t move_dist(oi_t *sensor_data, int dist, int spd)
{
	oi_update(sensor_data);
	int sum = 0;
	int velocity = (dist < 0) ? -spd: spd;  // Move at indicated speed
	oi_set_wheels(velocity, velocity);
	stop_flag = full_distance;

	movement_data_t rv;
	
	//If attempting to go forward
	if (dist > 0) {
		while ((sum < dist) && !stop_flag) {
			oi_update(sensor_data);
			sum += sensor_data->distance; // Adds a positive value
			
				
			// Bumper detection
			if (sensor_data->bumper_left && sensor_data->bumper_right) {
				stop_flag = left_and_right_bumper;
				break;
			} else if (sensor_data->bumper_left) {
				stop_flag = left_bumper;
				break;
			} else if (sensor_data->bumper_right) {
				stop_flag = right_bumper;
				break;
			}
				
			// Cliff detection
			else if (sensor_data->cliff_left) {
					stop_flag = left_cliff;
					break;
			}else if (sensor_data->cliff_right) {
					stop_flag = right_cliff;
					break;
			} else if (sensor_data->cliff_frontleft) {
						stop_flag = front_left_cliff;
						break;
			} else if (sensor_data->cliff_frontright) {
				stop_flag = front_right_cliff;
				break;
			}
								
			// White strip detection
			else if (sensor_data->cliff_frontleft_signal > 600){
				stop_flag = white_tape_front_left;
				break;
			} else if (sensor_data->cliff_frontright_signal > 600){
				stop_flag = white_tape_front_right;
				break;
			}else if (sensor_data->cliff_frontright > 600){
				stop_flag= white_tape_right;
				break;
			} else if (sensor_data ->cliff_frontleft > 600){
				stop_flag = white_tape_left;
				break;
			}
		}//while
	
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
		
	rv.travelled = sum;
	rv.flag = stop_flag;
	
	return rv;
}


rotation_data_t turn(oi_t *sensor_data, int angle) {
	
	rotation_data_t rt;
	
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
	
	rt.rotated = sum;
	
	return rt;
}

