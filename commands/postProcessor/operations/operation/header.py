from pathlib import Path
from typing import TextIO

from .....config import PLUGIN_VERSION
from ...config import CMD_NAME
from ...file_modes import FileModes
from ...gcode_helpers import filter_merged_source_line, format_comment

class OperationHeader():
    def WriteHeaderStart(self, fileHandler: TextIO):
        with self._tempFilePath.open("r") as operationFile:
            
            file = Path(fileHandler.name).stem
            self._lineNumber = self._writeLine(fileHandler, format_comment(file), 0)
            self._lineNumber = self._writeLine(
                fileHandler,
                format_comment(f"Generated with {CMD_NAME} version {PLUGIN_VERSION}"),
                self._lineNumber,
            )

            line = operationFile.readline()
            row = 0

            while len(line) != 0:
                # It's the temporary file name, so ignore it as the 
                # real name will be written later
                if line == f"({self._tempFilePath.stem})\n": 
                    line = operationFile.readline()
                    row += 1
                    continue
                elif row == self._toolCommentLine:
                    break
                filtered = filter_merged_source_line(line)
                if filtered is not None:
                    self._lineNumber = self._write(fileHandler, filtered, self._lineNumber)
                line = operationFile.readline()
                row += 1

    def WriteToolComment(self, fileHandler: TextIO):
        with self._tempFilePath.open(FileModes.READ) as operationFile:
            line = operationFile.readline()
            row = 0
            while len(line) != 0:
                if row == self._toolCommentLine:
                    filtered = filter_merged_source_line(line)
                    if filtered is not None:
                        self._lineNumber = self._write(fileHandler, filtered, self._lineNumber)
                    break
                line = operationFile.readline()
                row += 1

    def WriteHeaderEnd(self, fileHandler: TextIO):
        with self._tempFilePath.open(FileModes.READ) as operationFile:
            line = operationFile.readline()
            row = 0
            while len(line) != 0:
                if row > self._toolCommentLine and row <= self._headerEndLine:
                    filtered = filter_merged_source_line(line)
                    if filtered is not None:
                        self._lineNumber = self._write(fileHandler, filtered, self._lineNumber)
                line = operationFile.readline()
                row += 1

    def WriteHeader(self, fileHandler: TextIO):
        self.WriteHeaderStart(fileHandler)
        self.WriteToolComment(fileHandler)
        self.WriteHeaderEnd(fileHandler)

