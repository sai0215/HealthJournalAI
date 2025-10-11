from pathlib import Path
import traceback
from uuid import uuid4


def get_folder_names(path:str):

    # Replace with the specific path you want
    specific_path = Path(path)

    # Get all directories in the specific path
    folder_names = [folder.name for folder in specific_path.iterdir() if folder.is_dir()]
    return folder_names


def get_error_result(e,extra_context:str=None):
    error_traceback = traceback.format_exc()
    final_res = {"error":str(e),
                     "iserror":True, 
                     "error_traceback":error_traceback,
                     "context":extra_context,
                     }
    return final_res


def get_uuid():
    """generate uuid"""
    return str(uuid4())