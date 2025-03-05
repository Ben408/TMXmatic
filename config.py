import os

# Base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DIR = os.path.join(BASE_DIR, 'source_files')
TARGET_DIR = os.path.join(BASE_DIR, 'target_files')

# Source file paths
XO_TMX_PATH = os.path.join(SOURCE_DIR, 'XO_TMX')
ADMIN_GUIDE_TMX_PATH = os.path.join(SOURCE_DIR, 'Admin_Guide_TMX')

# Target file paths
CLEANED_XO_TMX_PATH = os.path.join(TARGET_DIR, 'Cleaned_XO_TMX')
REMOVED_TUS_PATH = os.path.join(TARGET_DIR, 'Removed_TUs')
EMPTY_TARGET_TUS_PATH = os.path.join(TARGET_DIR, 'Empty_Target_TUs')
TRUE_DUPLICATES_PATH = os.path.join(TARGET_DIR, 'True_Duplicates')
NON_TRUE_DUPLICATES_PATH = os.path.join(TARGET_DIR, 'Non_True_Duplicates')
SENTENCE_LEVEL_TUS_PATH = os.path.join(TARGET_DIR, '')
VNDLY_TMX_PATH = os.path.join(TARGET_DIR, 'VNDLY_TMX')

# Common functions
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Ensure all target directories exist
for path in [CLEANED_XO_TMX_PATH, REMOVED_TUS_PATH, EMPTY_TARGET_TUS_PATH, 
             TRUE_DUPLICATES_PATH, NON_TRUE_DUPLICATES_PATH, SENTENCE_LEVEL_TUS_PATH, 
             VNDLY_TMX_PATH]:
    ensure_dir(path)

# Add any other common configurations or functions here
