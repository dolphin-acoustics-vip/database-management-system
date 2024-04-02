import os

with open(os.path.expanduser("~/.bashrc"), "a") as outfile:
    """
    WARNING: THIS SCRIPT WILL OVERRIDE THE FOUR ENVIRONMENT VARIABLES
    LISTED BELOW. USE WITH CAUTION.
    
    WARNING: ENSURE ALL THE ENVIRONMENT VARIABLES ARE SET BEFORE RUNNING.
    
    WARNING: ENSURE ALL SENSITIVE DATA IS REMOVED FROM THIS FILE BEFORE
    COMMITTING ANY CHANGES TO GIT.
    """
    
    host="localhost" # SET/VERIFY BEFORE RUNNING
    user="root" # SET/VERIFY BEFORE RUNNING
    password=None # SET/VERIFY BEFORE RUNNING
    database=None # SET/VERIFY BEFORE RUNNING
     
    outfile.write("export STADOLPHINACOUSTICS_HOST="+host+"\n")
    outfile.write("export STADOLPHINACOUSTICS_USER="+user+"\n")
    outfile.write("export STADOLPHINACOUSTICS_PASSWORD="+password+"\n")
    outfile.write("export STADOLPHINACOUSTICS_DATABASE="+database+"\n")