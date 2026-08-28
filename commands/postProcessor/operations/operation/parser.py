from pathlib import Path

from ...gcode_helpers import (
    code_in_list,
    is_tail_gap_line,
    line_matches_end_codes,
    update_trailing_end_sequence,
)
from ...line import Line
from ...settings.settings import Settings

class OperationParser(Line):

    def _parseFile(self, filePath: Path):
        #region Header example
        # Find the start of the header and body in the generated file

        # Parse the gcode. We expect a header like this:
        #
        # % <optional>
        # Oxxxx <optional>
        # (<comments>) <0 or more lines>
        # (<Txx tool comment>) <optional>
        # <comments or G-code initialization, up to Txx>
        #
        # This header is stripped from all files after the first,
        # except the tool comment is put in a list at the top.
        # The header ends when we find the body, which starts with:
        #
        # Txx ...   (optionally preceded by line number Nxx)
        #
        # We copy all the body, looking for the tail. The start
        # of the tail is the trailing run of end codes entered by
        # the user. The defaults are:
        # M30 - end program
        # M5 - stop spindle
        # M9 - stop coolant
        # The tail is stripped until the last operation is done.
        #
        # Do not stop at the *first* M5/M9: Fusion LinuxCNC posts M9 at
        # the start of each operation (coolant off before the tool
        # change). That would mark the whole cutting body as "tail",
        # skip rapid restoration, and drop later operations when merging.
        #
        # Rapid analysis is performed later in WriteBody once the temp
        # file is guaranteed complete.
        #endregion
        
        with filePath.open("r") as operationFile:
            line = operationFile.readline()
            self._toolCommentLine = -1
            self._tailStartLine = -1
            lineNumber = -1
            inHeader = False
            processHeader = True
            processBody = False
            while len(line) != 0:
                lineNumber += 1

                if not self._allowBlankLines and line[0] == "\n":
                    self._allowBlankLines = True

                if processHeader:
                    processHeader, inHeader = self._parseHeaderLine(line, lineNumber, inHeader)
                    processBody = not processHeader
                elif processBody:
                    self._parseBodyLine(line, lineNumber)
                line = operationFile.readline()
        return # No tail found, so probably a handmade operation

    def _parseHeaderLine(self, line: str, lineNumber: int, inHeader: bool) -> tuple[bool, bool]:
        toolComment = OperationParser._TOOL_COMMENT_REG.search(line)
        if toolComment: # We have found the tool comment line
            self._toolCommentLine = lineNumber
            return True, inHeader
        else:
            headerMatch = OperationParser._BODY_RE.match(line)
            if headerMatch:
                if headerMatch.group("G") is not None:
                    # Found a g-code, check if it is in the list of
                    # header end codes
                    if code_in_list(f"G{headerMatch.group('G')}", Settings.Get(Settings.HEADER_END_CODES)):
                        # Found the end of the header
                        self._headerEndLine = lineNumber
                        return (True, True)
                    elif inHeader: # Found a g-code that isn't in the header end codes, so we're in the body.
                        self._bodyStartLine = lineNumber
                        return (False, inHeader) 

                if headerMatch.group("M") is not None:
                    # Found an m-code, check if it is in the list of
                    # header end codes
                    if code_in_list(f"M{headerMatch.group('M')}", Settings.Get(Settings.HEADER_END_CODES)):
                        # Found the end of the header
                        self._headerEndLine = lineNumber
                        return (True, True)
                    elif inHeader: # Found an m-code that isn't in the header end codes, so we're done with the header.
                        self._bodyStartLine = lineNumber
                        return (False, inHeader) 

                if headerMatch.group("T") is not None:
                    # Definitely found the body as this is either a 
                    # tool change line or a line not in header end 
                    # codes (which matched earlier), so we're done
                    self._bodyStartLine = lineNumber
                    if self._headerEndLine == -1: 
                        self._headerEndLine = lineNumber - 1 # Definite end of header
                    return (False, inHeader)
                
                if headerMatch.group("line") is not None \
                    and headerMatch.group("line") == f"({self.name})\n":
                        # This is a comment line with the operation name, ignore it
                        # but use it as a possible end of the header.
                        self._headerEndLine = lineNumber -1
                        return (True, inHeader)
                
            return (not inHeader, inHeader)
        
    def _parseBodyLine(self, line: str, lineNumber: int):
        bodyMatch = OperationParser._BODY_RE.match(line)
        if bodyMatch:
            if bodyMatch.group("G") is not None:
                gCode = int(bodyMatch.group("G"))
                if gCode == 0:
                    lineMatch = OperationParser._PARSE_LINE_RE.match(line)
                    # We're only interested in the first rotation move.
                    # Posts without a 4-axis machine often omit G0 A0;
                    # WriteBody then injects A from setup WCS instead.
                    if not self.hasRotation and lineMatch and lineMatch.group("G") is not None and lineMatch.group("A") is not None:
                        aCode = float(lineMatch.group("A"))
                        if aCode == 0.0:
                            # Found A-axis rotation move
                            self._rotationLine = lineNumber
            if bodyMatch.group("T") is not None and self._bodyStartLine == -1:
                # found body start
                self._bodyStartLine = lineNumber

            is_end = line_matches_end_codes(line, Settings.Get(Settings.END_CODES))
            is_significant = (not is_end) and (not is_tail_gap_line(line))
            self._tailStartLine = update_trailing_end_sequence(
                self._tailStartLine,
                is_end_code=is_end,
                is_significant=is_significant,
                line_number=lineNumber,
            )
        return False
    