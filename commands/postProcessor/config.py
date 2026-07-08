from ...config import ADDIN_NAME, COMPANY_NAME

#
# Configuration for the Batch Post add-in.
# Global variables shared across the post-processing command.
#

SETTINGS_VERSION = 8

#palettes
POST_PROCESSOR_PALETTE_ID = f'{COMPANY_NAME}_{ADDIN_NAME}_post_processor_palette_id'

CMD_ID = f'{COMPANY_NAME}_{ADDIN_NAME}_postProcessorDialog'
CMD_NAME = 'Batch Post'
CMD_DESCRIPTION = 'Batch post-process Fusion CAM operations into one or more G-code files, with optional rapid restoration, multi-setup merge, and A-axis rotation.'
