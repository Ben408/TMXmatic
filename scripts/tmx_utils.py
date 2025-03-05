import PythonTmx

def from_tmx(file_path):
    """Load a TMX file and return a TMX object"""
    try:
        return PythonTmx.Tmx(file_path)
    except Exception as e:
        raise Exception(f"Error loading TMX file: {e}")

def to_tmx(tmx_obj, output_path):
    """Save a TMX object to a file"""
    try:
        tmx_obj.save(output_path)
        return output_path
    except Exception as e:
        raise Exception(f"Error saving TMX file: {e}")

def validate_tmx(file_path):
    """Validate TMX file structure"""
    try:
        tmx = from_tmx(file_path)
        return True, tmx
    except Exception as e:
        return False, str(e) 