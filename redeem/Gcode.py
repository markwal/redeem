"""
G-code interpreter for Replicape.
For more info see:
http://reprap.org/wiki/G-code

Author: Elias Bakken
email: elias(dot)bakken(at)gmail(dot)com
Website: http://www.thing-printer.com
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
import re


class Gcode:
    """ A command received from pronterface or whatever """
    line_number = 0

    def __init__(self, packet):
        """ Init; parse the token """
        try:
            self.message = packet["message"].split(";")[0]
            self.message = self.message.strip(' \t\n\r')
            self.parent = packet["parent"] if "parent" in packet else None
            self.prot = packet["prot"] if "prot" in packet else None
            if self.prot is None:
                self.prot = self.parent.prot if self.parent else "None"
            self.has_crc = False
            self.answer = "ok"
            #print packet
            if len(self.message) == 0:
                #print packet
                #logging.debug("Empty message")
                self.gcode = "No-Gcode"
                return
            self.tokens = self.message.split(" ")
            if self.tokens[0][0] == "N":  # Ok, checksum
                line_num = re.findall(r"[\d]+", self.message)[0]
                cmd = self.message.split("*")[0]  # Command
                csc = self.message.split("*")[1]  # Command to compare with
                if int(csc) != self._getCS(cmd):
                    logging.error("CRC error!")
                # Remove crc stuff
                self.message = self.message.\
                    split("*")[0][(1+len(line_num))::].strip(" ")
                self.line_number = int(line_num)  # Set the line number
                Gcode.line_number += 1  # Increase the global counter
                self.has_crc = True

            """
            Tokenize gcode "words" per RS274/NFC v3

            Redeem's built-in help '?' after a primary word is also supported.

            M117 Exception: Text supplied to legacy malformed M117 should not
            be capitalized or stripped of its whitespace. The first leading
            space after M117 is optional (and ignored) so long as the first
            charcter is not a digit (0-9) or a period (.). Example: M117this
            will work.
            """
            match = re.match(r"(M117)(?:$|\ |(?=[^0-9.]{1}))\s?(.*)", self.message, re.IGNORECASE)
            if match:
                self.tokens = [match.group(1).upper(), match.group(2).strip(" ")]
            else:
                self.tokens = re.findall(r"[A-Z][-+]?[0-9]*\.?[0-9]*\??", \
                        "".join(self.message.split()).upper() )

            """
            Retrieve primary gcode. Exchange . for _ (if any) for Python
            class name compliance. Example: G29_1
            """
            self.gcode = self.tokens.pop(0).replace('.', '_')

        except Exception as e:
            self.gcode = "No-Gcode"
            logging.exception("Ooops: ")

    def code(self):
        """ The machinecode """
        return self.gcode

    def is_valid(self):
        return True if self.gcode != "No-Gcode" else False

    def token_letter(self, index):
        """ Get the letter """
        return self.tokens[index][0]

    def token_value(self, index):
        """ Get the value after the letter """
        return self.tokens[index][1::]

    def get_tokens(self):
        """ Return the tokens """
        return self.tokens

    def set_tokens(self, tokens):
        """ Set the tokens """
        self.tokens = tokens

    def has_letter(self, letter):
        """ Check if the letter exists as token """
        for token in self.tokens:
            if token[0] == letter:
                return True
        return False

    def get_value_by_letter(self, letter):
        for token in self.tokens:
            if token[0] == letter:
                return token[1::]
        return None

    def get_float_by_letter(self, letter, default):
        if self.has_letter(letter):
            if self.has_letter_value(letter):
                return float(self.get_value_by_letter(letter))
        return default

    def get_int_by_letter(self, letter, default):
        """ Get an int or return a default value """
        if self.has_letter(letter):
            # Convert to float first since Cura 2.1 sends M104 as 255.0
            return int(float(self.get_value_by_letter(letter)))
        return int(default)

    def has_letter_value(self, letter):
        for token in self.tokens:
            if token[0] == letter:
                if len(token) > 1:
                    return True
        return False

    def remove_token_by_letter(self, letter):
        for i, token in enumerate(self.tokens):
            if token[0] == letter:
                self.tokens.pop(i)

    def num_tokens(self):
        return len(self.tokens)

    def get_tokens_as_dict(self):
        """ Return the remaining tokans as a dict"""
        return {t[0]: t[1:] for t in self.get_tokens()}


    def _getCS(self, cmd):
        """ Compute a Checksum of the letters in the command """
        cs = 0
        for c in cmd:
            cs ^= ord(c)
        return cs

    def is_crc(self):
        """ Return True if this segment was a numbered line """
        return self.has_crc

    def get_answer(self):
        if self.parent:
            return self.parent.get_answer()
        else:
            return self.answer

    def set_answer(self, answer):
        if self.parent:
            self.parent.set_answer(answer)
        else:
            self.answer = answer

    def is_info_command(self):
        return (self.gcode[-1] == "?")
