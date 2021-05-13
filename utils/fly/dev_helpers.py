from os import walk, path


def determine_dir_structure(output_analysis_id_dir):
    """
    The directory structure during analysis is somewhat obscure.
    If the file path in the code is incorrect, this method will be called to
    help build the debugging message.
    """
    for root, dirs, files in walk(output_analysis_id_dir):
        for f in files:
            print(path.join(root, f))
