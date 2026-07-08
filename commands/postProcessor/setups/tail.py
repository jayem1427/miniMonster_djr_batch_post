from ..settings.settings import Settings
from ..validation_helpers import select_single_file_tail_setup

class SetupsTail():
    @classmethod
    def WriteTail(cls):

        if Settings(Settings.OPERATIONS_GROUPING) in [Settings.OperationsGroupings.SINGLE_FILE]:
            # Use the last setup that actually has a program-end (tail) block.
            # Using the first setup with a header can skip the tail entirely.
            lastSetup = select_single_file_tail_setup(cls.selected)

            if lastSetup is not None:
                lastSetup.WriteTail()
        else: # SETUP, SETUP_AND_TOOL, PER_OPERATION
            fileName = None
            for setup in cls.selected:
                if Settings(Settings.NUMERIC_NAME) and fileName is not None:
                    setup.SetFileName(fileName)
                setup.WriteTail()
                if Settings(Settings.NUMERIC_NAME):
                    fileName = setup._operations.fileName
    