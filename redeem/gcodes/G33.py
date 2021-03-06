"""
GCode G33
Autocalibrate delta printer

License: GNU GPL v3: http://www.gnu.org/copyleft/gpl.html

 Redeem is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 Redeem is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Redeem.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging

import numpy as np

from GCodeCommand import GCodeCommand

try:
    from Gcode import Gcode
    from Path import Path
except ImportError:
    from redeem.Gcode import Gcode
    from redeem.Path import Path


class G33(GCodeCommand):

    def execute(self, g):
        num_factors = g.get_int_by_letter("F", 4)
        if num_factors < 3 or num_factors > 4:
            logging.error("G33: Invalid number of calibration factors.")

        # we reuse the G29 macro for the autocalibration purposes
        gcodes = self.printer.config.get("Macros", "G29").split("\n")
        self.printer.path_planner.wait_until_done()
        for gcode in gcodes:        
            G = Gcode({"message": gcode, "prot": g.prot})
            self.printer.processor.execute(G)
            self.printer.path_planner.wait_until_done()

        # adjust probe heights
        print_head_zs = np.array(self.printer.probe_heights[:len(self.printer.probe_points)])

        # Log the found heights
        logging.info("G33: Found heights: "+str(np.round(print_head_zs, 2)))

        simulate_only = g.has_letter("S")

        # run the actual delta autocalibration
        params = self.printer.path_planner.autocalibrate_delta_printer(
                    num_factors, simulate_only,
                    self.printer.probe_points, print_head_zs)
        logging.info("G33: Finished printer autocalibration\n")

        if g.has_letter("P"):
            # dump the dictionary to log file
            logging.debug(str(params)) 
            
            #pretty print to printer output
            self.printer.send_message(g.prot, "delta calibration : L = %g"%params["L"])
            self.printer.send_message(g.prot, "delta calibration : r = %g"%params["r"])
            self.printer.send_message(g.prot, "delta calibration : A_tangential = %g"%params["A_tangential"])
            self.printer.send_message(g.prot, "delta calibration : B_tangential = %g"%params["B_tangential"])
            self.printer.send_message(g.prot, "delta calibration : C_tangential = %g"%params["C_tangential"])
            self.printer.send_message(g.prot, "delta calibration : offset_x = %g"%params["offset_x"])
            self.printer.send_message(g.prot, "delta calibration : offset_y = %g"%params["offset_y"])
            self.printer.send_message(g.prot, "delta calibration : offset_z = %g"%params["offset_z"])
        
        return

    def get_description(self):
        return "Autocalibrate a delta printer"

    def get_long_description(self):
        return """
Do delta printer autocalibration by probing the points defined in
the G29 macro and then performing a linear least squares optimization to
minimize the regression residuals.

Parameters:

Fn  Number of factors to optimize:
    3 factors (endstop corrections only)
    4 factors (endstop corrections and delta radius) (Default)
    6 factors (endstop corrections, delta radius, and two tower
                angular position corrections)
    7 factors (endstop corrections, delta radius, two tower angular
                position corrections, and diagonal rod length)

S   Do NOT update the printer configuration.

P   Print the calculated variables"""

    def is_buffered(self):
        return True

    def get_test_gcodes(self):
        return ["G33 F4"]

