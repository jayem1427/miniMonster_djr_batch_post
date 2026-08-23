from typing import TextIO

from ...file_modes import FileModes
from ...gcode_helpers import filter_merged_source_line, format_comment

class OperationTail():
    def WriteTail(self, fileHandler: TextIO):

        with self._tempFilePath.open(FileModes.READ) as operationFile:
            line = operationFile.readline()
            row = 0
            while len(line) != 0:
                if row == self._tailStartLine: # Add an extra line marking where this operation tail starts
                    if(self._allowBlankLines):
                        fileHandler.write("\n") # ensure blank line before operation tail
                    self._lineNumber = self._writeLine(fileHandler, format_comment(self.name), self._lineNumber)
                if row >= self._tailStartLine:
                    filtered = filter_merged_source_line(line)
                    if filtered is not None:
                        self._lineNumber = self._write(fileHandler, filtered, self._lineNumber)
                line = operationFile.readline()
                row += 1
        # For numeric file names
        from ...programs import Programs
        from ...settings.settings import Settings

        if Settings(Settings.NUMERIC_NAME) and Programs.Current.fileName.isnumeric():
            Programs.Current.SetFileName(str(int(Programs.Current.fileName) + 1).rjust(Settings(Settings.FILE_SEQUENCE_DIGITS), '0'))
    #endregion