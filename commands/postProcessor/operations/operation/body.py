from typing import Optional, TextIO

from ... import runtime_options
from ...file_modes import FileModes
from ...gcode_helpers import (
    coalesce_min_distance,
    force_rapid_start_line,
    strip_feed_words,
)
from ...line import Line
from .rapidsParser import RapidsParser

class OperationBody(Line):
    def _refreshRapidsAnalysis(self):
        """
        Analyze the temp file immediately before writing.

        Fusion may still be flushing when ``_parseFile`` runs, so an earlier
        analysis can be empty even when restore-rapids is enabled. WriteBody
        runs only after every operation has posted, so the file is complete.
        """
        if not runtime_options.restore_rapid_moves:
            self._rapidsAnalysis = {}
            return
        if self._tempFilePath is None or not self._tempFilePath.exists():
            self._rapidsAnalysis = {}
            return
        minDist = coalesce_min_distance(runtime_options.rapid_moves_minimum_distance, 20)
        self._rapidsAnalysis = {
            seg["startLine"]: seg["endLine"]
            for seg in RapidsParser.analyze(RapidsParser.parseFile(self._tempFilePath), minDist=minDist)
            if seg.get("isValid") and "startLine" in seg and "endLine" in seg
        }

    def WriteBody(self, fileHandler: TextIO, rotationAngle: Optional[float] = None, preserveRotation: Optional[bool] = False):
        self._refreshRapidsAnalysis()
        with self._tempFilePath.open(FileModes.READ) as operationFile:
            line = operationFile.readline()
            row = 0
            rapidsEnds = 0
            readNextLine = False
            wroteRapidsStatus = False
            while len(line) != 0:
                if readNextLine:
                    line = operationFile.readline() 
                    row += 1
                    readNextLine = False

                if row >= self._bodyStartLine:
                    if row == self._bodyStartLine: # Add an extra line marking where this operation starts
                        if self._allowBlankLines:
                            fileHandler.write('\n') # keep blank line before operation start
                        self._lineNumber = self._writeLine(fileHandler, f"({self.name})", self._lineNumber)
                        if runtime_options.restore_rapid_moves and not wroteRapidsStatus:
                            self._lineNumber = self._writeLine(
                                fileHandler,
                                f"(Rapid restore: {len(self._rapidsAnalysis)} segment(s))",
                                self._lineNumber,
                            )
                            wroteRapidsStatus = True
                    if row + 1 in self._rapidsAnalysis: # Add rapids comments if this line is the start of a rapid move
                        rapidsEnds = self._rapidsAnalysis[row + 1]
                        self._lineNumber = self._write(fileHandler, force_rapid_start_line(line), self._lineNumber)
                        readNextLine = True
                        continue
                    if rapidsEnds and row + 1 < rapidsEnds:
                        # Intermediate rapid traverse/retract words — keep G0 modal, drop F.
                        cleaned = strip_feed_words(line.rstrip("\r\n")).rstrip() + "\n"
                        self._lineNumber = self._write(fileHandler, cleaned, self._lineNumber)
                        readNextLine = True
                        continue
                    if row + 1 == rapidsEnds:
                        rapidsEnds = 0
                        cleaned = strip_feed_words(line.rstrip("\r\n")).rstrip() + "\n"
                        self._lineNumber = self._write(fileHandler, cleaned, self._lineNumber)
                        line = "G1 (Rapid movement end)\n" # switch back to feed after the restored rapid
                    if self._matchLine(fileHandler, line, row, rotationAngle, preserveRotation):
                        readNextLine = True
                        continue

                    self._lineNumber = self._write(fileHandler, line, self._lineNumber)

                line = operationFile.readline()
                row += 1
                if self._tailStartLine != -1 and row >= self._tailStartLine:
                    break

    def _matchLine(self, fileHandler: TextIO, line: str, row: int, rotationAngle: Optional[float], preserveRotation: Optional[bool] = False) -> bool:
        lineMatch = OperationBody._PARSE_LINE_RE.match(line)
        if lineMatch:
            if lineMatch.group("G") is not None:
                gCode = lineMatch.group("G")
                if lineMatch.group("A") is not None:
                    aCode = lineMatch.group("A")
                    # Float as there can be subgroups of the command
                    if float(gCode) == 0.0 and float(aCode) == 0.0:
                        # Special handling of A-axis rotation moves.
                        # The rotation will always be 0 as the operation
                        # are always generated one by one
                        # There is a rotation added at the end making
                        # things messy, just ignore it as we don't need it.
                        # If a rotation row is found but isn't the one 
                        # expected just remove it, otherwise consider it.
                        return True if row != self._rotationLine else self._handleRotation(fileHandler, rotationAngle, preserveRotation)
        return False

    def _handleRotation(self, fileHandler: TextIO, rotationAngle: Optional[float], preserveRotation: Optional[bool] = False) -> bool:
        if preserveRotation: # This is the first setup, so we want it to rotate to 0, so we keep the rotation line as is
            return False
        elif rotationAngle is None: # No rotation provided, ignore the line as it will rotate to 0 which we don't want.
            return True
        else: # Write our own rotation code based on the provided rotation angle
            self._lineNumber = self._writeLine(fileHandler, "(Rotating A-axis between setups)", self._lineNumber)
            # Using G53 for absolute machine coordinates for safe retraction
            if Settings(Settings.SAFE_Y_RETRACTION):
                self._lineNumber = self._writeLine(fileHandler, "G90 G53 G0 Z-3 Y{yRetraction}".format(yRetraction = Settings(Settings.Y_RETRACTION_COORDINATE)), self._lineNumber)
            else:
                self._lineNumber = self._writeLine(fileHandler, "G90 G53 G0 Z-3", self._lineNumber)
            self._lineNumber = self._writeLine(fileHandler, "G90 G54 G0 A{angle}".format(angle = f"{rotationAngle:.3f}".rstrip("0").rstrip(".")), self._lineNumber)
            return True