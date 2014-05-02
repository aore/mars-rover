import sys
import math

import numpy as np
import scipy
from scipy.interpolate import LSQUnivariateSpline

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Wedge, Circle

import sentinel
import sensors
import ir
import oi
import sonar
import servo
from codes import OIStopID


DEFAULT_CALIBRATION_DATA_DIR = 'calibrate/data/default'


zorders = {
    'breadcrumbs': 0,
    'scan_field': 1,
    'scan_data': 2,
    'contours': 3
}


class Environment():
    """ Rover presents a to the user the `env` map, which depicts those
    elements of the environment which it has discovered. """

    def __init__(self):
        # Distance scan and event data is mapped onto the cartesian space
        # defined w.r.t. the robot's initial orientation. So the robot's
        # initial orientation in the real world is always represented as being
        # at the origin and as directed upward.
        self._loc = (0.0, 0.0)
        self._direction = 90.0

        # The axis onto which the environment is plotted:
        self.view = plt.figure().add_subplot(111, aspect='equal')
        self.view.set_xlim(-300, 300)
        self.view.set_ylim(-300, 300)

        # A list of locations at which the rover has previously stopped:
        self.breadcrumbs = []

        # The dangers that the rover has found so far:
        self.bumps = []
        self.cliffs = []
        self.drops = []
        self.tape = []

        # Point observations found in scans and mapped to `env` space:
        self.ir_obs = []
        self.sonar_obs = []

        # A list of line objects generated by plotting scan data regressions.
        # All contours in this list were finalized and should remain in `env`
        # indefinitely:
        self.contours = []

        # Contours that should be removed when more scan data is appended
        # because new contours will be generated.
        self.volatile_contours = []

        # A semi-circle `Wedge` object that indicates the rover's current
        # location and direction:
        self.scan_field = None
        self.update_scan_field()
        self.draw()



    

    def __del__(self):
        plt.close(self.view.figure)




    def loc(self, new_loc = None):
        """ Gets the current location, a 2-tuple of xy-coordinates, if there is
        no `new_loc` argument. Otherwise, sets `new_loc` as the current
        location and re-draws the plot. """

        if new_loc == None:
            return self._loc
        else:
            self._loc = new_loc
            self.update_scan_field()
            self.draw()




    def move(self, dist):
        """ Updates the rover's location in the Environment by translating its
        position forward by the given `dist`. """
        
        self.add_breadcumb()
        new_loc = self.conv_radial(90, dist)
        self.loc(new_loc)




    def direction(self, new_direction = None):
        """ If there is no `new_direction` argument, the current location,
        represented as a 2-tuple of xy-coordinates, is returned. Otherwise,
        sets the given 2-tuple, `new_direction`, as the current direction and
        re-draws the plot.
        """
        if new_direction == None:
            return self._direction
        else:
            self._direction = new_direction
            self.update_scan_field()
            self.draw()
        # TODO: normalize `_direction` to (-180.0, 180.0] or [0.0, 360.0)




    def rotate(self, delta):
        """ Updates rover's direction in the Environment by rotating by given
        number of degrees. Rotation is CCW if `delta` is positive and CW if
        `delta` is negative.
        """
        self.direction(self._direction + delta)




    def add_scan(self, scan_data, cartesian = False):
        """ Adds the given `scan` data (expected to have been generated by
        `rover.scan()`) to the environment and updates the plot. """

        ir_data, sonar_data = scan_data
        ir_data = self.conv_radial_arr(ir_data[:, 0], ir_data[:, 1])
        sonar_data = self.conv_radial_arr(sonar_data[:, 0], sonar_data[:, 0])
        self.ir_obs.append(ir_data)
        self.sonar_obs.append(sonar_data)
        
        point_size = 8

        col = self.view.scatter(ir_data[:, 0], ir_data[:, 1], s = point_size)
        col.set_edgecolor('none')
        col.set_facecolor('blue')
        col.set_zorder(zorders['scan_data'])
        
        col = self.view.scatter(sonar_data[:, 0], sonar_data[:, 1], s = point_size)
        col.set_edgecolor('none')
        col.set_facecolor('green')
        col.set_zorder(zorders['scan_data'])
        
        self.draw()




    def add_breadcumb(self):
        """ Adds a breadcumb """
        c = Circle(self._loc, radius = 16.25)
        c.set_facecolor('0.65')  # grey
        c.set_edgecolor('black')
        c.set_zorder(zorders['breadcrumbs'])
        c.set_fill(True)
        self.view.add_artist(c)
        self.breadcrumbs.append(c)
        self.draw()




    def add_danger(self, danger_id):
        """ Appends a new danger to the appropriate list of `env`, and updates
        the `env` view. The position at which the danger is placed is computed
        based on the rover's location and direction, but also where on the
        robot that particular danger-detection sensor is located. """
        
        # TODO: proper handling
        # The following is the temporary workaround:
        sys.stderr.write("danger found: " + str(danger_id))




    def add_contour(self, xs, ys, volatile = False):
        """ TODO """

        c = self.view.plot(xs, ys)
        if volatile == True:
            self.volatile_contours.append(c)
        else:
            self.contours.append(c)




    def finalize_contours(self):
        """ Makes all volatile contours to non-volatile. """
        self.contours.extend(self.volatile_contours)
        self._clear_volatile_contours()
        # No changes to the `Environment` plot should be necessary.




    def _clear_volatile_contours(self):
        """ Removes all volatile contours from the Environment plot and from
        the internal list. """

        # TODO:
        # for c in self.volatile_contours():
        #     remove c from view's appropriate data structure
        #c.clear()
        #self.draw()




    def update_scan_field(self):
        """ Updates the location of the `scan_field` semi-circle displayed to
        indicate its location and the direction in which it is facing. If there
        was a no previous scan field, then will be added. Should be called
        whenever either location or needs to be
        called as part of the rover's move and rotate functions.) """

        # Remove the old scan field, if there is one:
        w = self.scan_field
        if w != None:
            self.view.artists.remove(w)

        # Make a semi-circle with radius 100 at the current rover location:
        w = Wedge(self._loc, 100, self._direction - 90, self._direction + 90)
        w.set_facecolor('0.90')  # grey
        w.set_edgecolor('none')
        w.set_zorder(zorders['scan_field'])
        w.set_fill(True)

        self.view.add_artist(w)
        self.scan_field = w




    def set_bounds(self, xlim, ylim):
        """ Redraws the `env` plot with different boundaries. `xlim` and `ylim`
        are expected to be 2-tuples. """

        self.view.set_xlim(xlim[0], xlim[1])
        self.view.set_ylim(ylim[0], ylim[1])
        self.draw()




    def draw(self):
        """ Refreshes the view of the `env`. """
        self.view.relim()
        self.view.autoscale_view(True, True, True)
        self.view.figure.canvas.draw()
        self.view.figure.show()




    def conv_radial(self, theta, r):
        """ Uses the rover's current orientation in the environment (i.e. its
        current location and angle) to map a single radial point into the
        cartesian environment presented by `env` view. Returns a 2-tuple, whose
        first entry is the x location and whose second entry is the y location.
        """

        theta_prime = (theta - 90.0 + self._direction) * (np.pi / 180.0)
        return (r * np.cos(theta_prime) + self._loc[0],
                r * np.sin(theta_prime) + self._loc[1])




    def conv_radial_arr(self, thetas, rs):
        """ Uses the rover's current orientation in the environment (i.e. its
        current location and angle) to map these radial points into the
        cartesian environment presented by `env` view.

        `thetas` is an `np.ndarray` of angles (measured in degrees), and `rs` is
        a `np.ndarray` of the corresponding radial distances.

        A newly created `np.ndarray` with two columns returned. For each
        (theta, r) pair in the inputs, a single (x, y) coordinate will be in
        this returned array.
        """

        # TODO: reimplement this using `radial_to_env()` as a numpy `ufunc`.

        if len(thetas) != len(rs):
            raise ValueError("`thetas` and `rs` must be of the same length.")

        # Make the given angles w.r.t. the 0 degrees of the `env`, convert
        # them to radians, and make a copy them to the other column:
        rv = np.empty((len(rs), 2), dtype = np.float64)
        rv[:, 0] = thetas - 90.0 + self._direction
        rv[:, 0] *= np.pi / 180.0
        rv[:, 1] = rv[:, 0]

        # Find the `x` and `y` values w.r.t. the origin of `env`:
        rv[:, 0] = rs * np.cos(rv[:, 0]) + self._loc[0]
        rv[:, 1] = rs * np.sin(rv[:, 1]) + self._loc[1]

        return rv






class Scanner():
    """ Displays a radial view of the immediate surroundings as generated by
    ir and servo radial distance data from a particular orientation. """

    def __init__(self):
        # A list of 2-tuples generated by rover.scan():
        self.scans = []

        # A list of contours to be draw on the current scan:
        self.contours = []

        # Startup the axis to be used for displaying scan data:
        self.view = plt.figure().add_subplot(111, projection = 'polar')
        self.draw()


    def __del__(self):
        plt.close(self.view.figure)



    def add_scan(self, scan_data):
        """ TODO
        """
        self.scans.append(scan_data)
        
        ir_data, sonar_data = scan_data
        
        angles = ir_data[:, 0] * (np.pi / 180.0)
        rs = ir_data[:, 1]
        rs = rs[~np.isnan(rs)]
        self.view.scatter(angles, rs, 'g')

        ''' DEBUG: temporarily disabled
        angles = sonar_data[:, 0] * (np.pi / 180.0)
        rs = sonar_data[:, 1]
        rs = rs[~np.isnan(rs)]
        self.view.scatter(angles, rs, 'b')
        '''

        #self.draw()



    def gen_contours(self, plot = True):
        """ Looks at the current scan data and uses it to generate a list of
        contours. Each of these contours is meant to be the approximate contour
        of a distinct object. Each of these contours is represented by a two-
        column `np.ndarray` of radial points. In particular, the first column
        holds angles (measured in degrees) and the second holds corresponding
        radial distances (measured in cm).
        """

        raise NotImplementedError

        #for c in self.find_obj_clouds():
            #regr = self._regress_object_cloud(c)
            #xs = np.linspace()




    def find_obj_clouds(self):
        """ Finds data from each distinct object generated across all scans.
        
        TODO: debug with multiple real objects
        """

        comb_scans = ()
        
        if len(self.scans) < 1:
            # There aren't any scans
            raise NotImplementedError()
        
        comb_scans = self.scans[0][0], self.scans[0][1]
        
        # Iterate through all scans
        for i in range(1, len(self.scans)):
            comb_scans = np.append(comb_scans[0], self.scans[i][0], axis=0), np.append(comb_scans[1], self.scans[i][1], axis=0)

        # Sort each ndarray
        comb_scans = np.sort(comb_scans[0], axis=0), np.sort(comb_scans[1], axis=0)
        
        # Create list of objects. 
        # This should be a 2-tuple containing all scans with data points
        # sorted. The first element should be a two column ndarray
        # containing angles and their corresponding distances for IR.
        # The second is the same, but for sonar. 
        obj_list = []
        
        # Iterate through consolidated scans to find clumps of objects
        min_width = 3 # minimum degrees for an object to be recognized
        
        start_deg = 0
        start_deg_index = 0
        end_deg = 0
        end_deg_index = 0
                
        # Go through all IR data
        for i in range(0, len(comb_scans[0])):
        
            # If the reading is not nan for IR, save it the angle it occurs at
            if (math.isnan(comb_scans[0][i][1]) == False) and (start_deg is 0):
                # Save starting angle
                start_deg = comb_scans[0][i][0]
                start_deg_index = i
            elif ((math.isnan(comb_scans[0][i][1]) == True) or (i == len(comb_scans[0] - 1))) and (start_deg is not 0):
                # Save ending angle if the object is wide enough
                if (comb_scans[0][i][0] - start_deg > min_width):
                    end_deg = comb_scans[0][i][0]
                    end_deg_index = i
                    
                    # TODO: take care of when objects are next to each other
                    # with no NaNs between
                    # TODO: deal with when object is at very edge of scan
                    # If an object is detected by IR, add both IR and sonar data
                    obj = comb_scans[0][start_deg_index:end_deg_index], comb_scans[1][start_deg_index:end_deg_index]
                    
                    obj_list.append(obj)
                
                start_deg = 0
        
        return obj_list




    def _regress_object_cloud(cloud):
        """ Finds a regression for the given object cloud. """
        knots = np.linspace(0, 180, 61)
        return LSQUnivariateSpline(data[:, 0], data[:, 1])




    def draw(self):
        self.view.set_rmax(100)
        self.view.figure.canvas.draw()
        self.view.figure.show()





class Rover():
    """ TODO
    """

    def __init__(self, sen = None, calib_dir = None, debug = False):
        """ TODO
        """
        if debug == True:
            sen = "DEBUG"
        elif sen is None:
            sen = sentinel.Sentinel()
        elif type(sen) is str:
            sen = sentinel.Sentinel(str)
        elif type(sen) != sentinel.Sentinel:
            raise TypeError("The argument `sen` must be `None`, of type `str` "
                                                       "or of type `Sentinel`")
        self.sen = sen

        # Attempt to load the converters from `calib_dir`:
        if calib_dir == None:
            calib_dir = DEFAULT_CALIBRATION_DATA_DIR

        self.ir_conv = sensors.gen_ir_converter(calib_dir + "/ir.csv")
        self.sonar_conv = sensors.gen_sonar_converter(calib_dir + "/sonar.csv")
        self.servo_conv = sensors.gen_servo_converter(calib_dir + "/servo.csv")
        # TODO: move_conv

        self.env = Environment()
        self.scanner = Scanner()



    def __del__(self):
        del(self.env)
        del(self.scanner)




    def scan(self, start=0, end=180, updt_scan=True, updt_env=True):
        """ This calls `sensors.scan()` to receive raw data from the robot and
        converts the resulting distances using the current `ir_conv` and
        `sonar_conv`.

        This data will be collected as the servo makes a single pass from the
        `start` angle to the `end` angle. Note that both are assumed to be
        integers and measured in degrees.

        The return value is a 2-tuple, where both elements are an
        `np.ndarray` object. The first element of the pair is the ir data 
        generated by a scan, while the second element is the sonar data. Both
        arrays have angles (measured in degrees) in their first column and
        corresponding radial distances (measured in in cm) in the second
        column. The `Rover` object's converters have been used in generating
        this data.

        If and only if `updt_scan` is true, will the results be automatically
        passed to the current `Scanner` object. Similarly, if and only if
        `updt_env` is true will the results be automatically passed to the
        current `Environment` object. If and only if both of these arguments
        are false will the results be returned to the user.

        Note that the scan can happen in either direction (i.e. clockwise or
        counter-clockwise) depending on which angle is bigger than the other.
        """

        # Generate a pulse width for each angle:
        if start <= end:
            angles = [i for i in range(start, end)]
        else:
            angles = [i for i in range(end, start, -1)]

        pulse_widths = self.servo_conv(angles)

        # Perform the scan:
        ir_data, sonar_data = sensors.scan(self.sen, pulse_widths)

        # Perform the conversion from raw readings to distances.
        ir_data[:, 1] = self.ir_conv(ir_data[:, 1])
        sonar_data[:, 1] = self.sonar_conv(sonar_data[:, 1])
        
        rv = (ir_data, sonar_data)
        if updt_scan == False and updt_env == False:
            return rv
        if updt_scan == True:
            self.scanner.add_scan(rv)
        if updt_env == True:
            self.env.add_scan(rv)




    def move(self, dist = 300, speed = 90):
        """ Moves the rover, adds a breadcrumb, updates the rovers location in
        `env`, and adds to `env` any dangers that were found. """

        self._finalize_for_reorientation()

        # Move and interpret the rover's response:
        dist, stop_reason = oi.move(self.sen, dist, speed)

        # TODO: use move_conv to correct for rover sensor error.

        self.env.move(dist)

        if stop_reason != OIStopID.full_distance:
            self.env.add_danger(stop_reason)




    def rotate(self, delta):
        """ Sends a command to the `rover` to rotate by the given angle
        (measured in degrees), and updates the rover's current direction. """

        self._finalize_for_reorientation()

        oi.rotate(self.sen, delta)
        # TODO: use `rotate_conv` to correct for rover sensor error.

        self.env.rotate(delta)
        
        
        
    def servo_angle(self, angles):
        """ Sends a command to the rover to turn the servo to the given angle.
        The pulse width which is sent is determined via the calibrated
        `servo_conv`. """
        servo.pulse_width(self.sen, self.servo_conv(angles))




    def _finalize_for_reorientation(self):
        """ Scan data points and the most up-to-date contours should have been
        incrementally added to both the scan and `env`. Must be called at the
        beginning of a `move()` or `rotate()` to clear away the (soon to be
        out-of -date) scan data and to make non-volatile the current scan-
        contours.
        """

        self.scanner = Scanner()  # Start using a new scanner.
        self.env.finalize_contours()
