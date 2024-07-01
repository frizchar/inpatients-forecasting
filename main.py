import engine


RUN_MODE = 'hybrid'         # determine RUN_MODE: 'prod', 'test', 'hybrid'
HOSPITAL_list = [1, 2]      # list containing the hospital IDs for which we'll predict the number of inpatients
HORIZON_VALUE = 14          # determine the number of days for the prediction (namely the prediction horizon)
CAP_TYPE = 'hard'           # determine CAP_TYPE: 'hard', 'soft'

if __name__ == "__main__":
    for HOSPITAL in HOSPITAL_list:
        engine.run_engine(RUN_MODE, HOSPITAL, HORIZON_VALUE, CAP_TYPE)
