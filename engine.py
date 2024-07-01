import run_test_model as rtm
import run_prod_model as rpm
import output
import time


def run_engine(run_mode: str, hospital: int, horizon_value: int, cap_type: str):
    start_time = time.time()

    hospital = str(hospital)

    initial_argument_value = 780  # determine the initial training period for the cross validation
    # rtm.run_model(hospital, horizon_value, initial_argument_value)

    if run_mode == 'test':
        df, mape, horizon_argument, initial_argument, period_argument, best_params, cap, df_train_val = \
            rtm.run_model(hospital, horizon_value, initial_argument_value, cap_type)
        min_test_date = min(df['ds'])
        max_test_date = max(df['ds'])
    elif run_mode == 'prod':
        df, mape, horizon_argument, initial_argument, period_argument, best_params, cap, df_train_val = \
            rpm.run_model(hospital, horizon_value, initial_argument_value, cap_type)
        min_test_date = '-'
        max_test_date = '-'
    elif run_mode == 'hybrid':
        df, mape, horizon_argument, initial_argument, period_argument, best_params, cap, df_train_val = \
            rpm.run_model(hospital, horizon_value, initial_argument_value, cap_type)
        # for RUN_MODE = 'hybrid' get A)min/max test dates and B)mape value from 'test'
        df_test, mape = rtm.run_model(hospital, horizon_value, initial_argument_value, cap_type)[:2]
        min_test_date = min(df_test['ds'])
        max_test_date = max(df_test['ds'])
    else:
        print("wrong 'run_mode' value")
        exit(1)

    output.output_to_excel(df, mape, horizon_value, horizon_argument,
                           initial_argument, period_argument, best_params,
                           cap, df_train_val, hospital, run_mode, cap_type,
                           min_test_date, max_test_date)

    end_time = time.time()
    print('\ntotal runtime :', round((end_time - start_time)/60, 2), ' mins')
