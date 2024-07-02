# run prophet in test mode

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import itertools
import warnings
import logging
from datetime import date
from datetime import timedelta
import fetch_data


warnings.filterwarnings('ignore')
logger = logging.getLogger('cmdstanpy')
logger.addHandler(logging.NullHandler())
logger.propagate = False
logger.setLevel(logging.CRITICAL)


def run_model(hospital: str, horizon_value_arg: int, initial_argument_value_arg: int, cap_type: str):
    # fetch the final dataset
    df = fetch_data.pull_dataset(hospital)
    print('df.shape :\n', df.shape)
    print("\ndf data types with ds as datetime :\n", df.dtypes)
    print("\ndf head with ds as datetime :\n", df.head())

    # sort data df by datetime column ds
    df = df.sort_values(by='ds')
    print("\n\033[92mhead of sorted data by datetime ds :\n", df.head(), "\033[00m")
    print("\n\033[91mtail of sorted data by datetime ds :\n", df.tail(), "\033[00m")

    # reset index using column 'ds' and rename the index as 'idx'
    df = df.reset_index(drop=True)
    print("\n\033[94mhead of reindexed data :\n", df.head(), "\033[00m")
    print("\n\033[94mtail of reindexed data :\n", df.tail(), "\033[00m")

    df['weekday'] = df['ds'].dt.dayofweek  # add additional regressor 'weekday'

    # define function that yields max value of the following datasets: df, future (see further down for future)
    if cap_type == 'hard':
        cap_factor = 0
    elif cap_type == 'soft':
        cap_factor = 0.08
    else:
        raise Exception("wrong 'cap_type' value")

    cap = max(df['y']) + round(cap_factor * max(df['y']))
    # define max & min values for target variable df['y']
    df['cap'] = cap
    df['floor'] = 0

    # create the parameter grid for hyperparameter tuning
    param_grid = {
        'growth': ['logistic'],
        'seasonality_mode': ['multiplicative'],
        'holidays_mode': ['multiplicative'],
        'changepoint_prior_scale': [0.01, 0.025, 0.04, 0.05, 0.1, 0.5],
        'seasonality_prior_scale': [1.5, 2.2, 4.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        'daily_seasonality': [True],
    }

    # Generate all combinations of parameters
    all_params = [dict(zip(param_grid.keys(), v)) for v in itertools.product(*param_grid.values())]
    rmses = []  # Store the RMSEs for each params here
    mapes = []  # Store the MAPEs for each params here

    # define cross-validation arguments
    horizon_value = horizon_value_arg
    horizon_argument = str(horizon_value) + ' days'
    # initial_argument_value = int(0.921*len(df))
    initial_argument_value = initial_argument_value_arg
    initial_argument = str(initial_argument_value) + ' days'
    period_argument = horizon_argument

    # generate train-validate & test subsets based on split_date
    split_date = str(date.today() - timedelta(days=horizon_value+1))
    df_train_val = df.loc[(df['ds'] <= split_date)]
    df_test = df.loc[(df['ds'] > split_date)]
    print("\n\033[92mtail of df_train_val :\n", df_train_val.tail(), "\033[00m")
    pd.set_option('display.max_rows', None)
    print("\n\033[91mfull test subset df_test :\n", df_test, "\033[00m")


    # implement cross-validation to evaluate all parameters
    for params in all_params:
        m = Prophet(**params)  # instantiate Prophet using params
        m.add_country_holidays(country_name='GR')  # add Greek holidays
        m.add_regressor('weekday')  # add to Prophet the additional regressor 'weekday'
        m.fit(df_train_val)  # fit model on train-validate set
        df_cv = cross_validation(m, initial=initial_argument, period=period_argument, horizon=horizon_argument,
                                 parallel="threads")
        df_p = performance_metrics(df_cv, rolling_window=1)
        rmses.append(df_p['rmse'].values[0])
        mapes.append(round(100 * df_p['mape'].values[0], 2))

    # Find the best parameters
    pd.set_option('display.max_columns', None)
    tuning_results = pd.DataFrame(all_params)
    # tuning_results['rmse'] = rmses
    tuning_results['mape'] = mapes
    print('tuning results :\n', tuning_results)

    # print best params
    # best_params = all_params[np.argmin(rmses)]
    best_params = all_params[np.argmin(mapes)]
    print('best params :', best_params)
    print('best params dtype:', type(best_params))
    print('df_cv for best params :\n', df_cv.head())

    # instantiate prophet model based on best parameter set best_params
    m_best = Prophet(**best_params).add_regressor('weekday').add_country_holidays(country_name='GR').fit(df_train_val)
    # create future
    future = m_best.make_future_dataframe(periods=horizon_value, freq='D')
    # define max & min future values for future
    future['cap'] = cap
    future['floor'] = 0
    print('\nfuture :\n', future.tail(horizon_value))

    # add to future additional regressors 'weekday', 'month', 'week'
    future['weekday'] = future['ds'].dt.dayofweek
    # future['month'] = future['ds'].dt.month
    # future['week'] = future['ds'].dt.isocalendar().week

    # make the forecast
    forecast = m_best.predict(future)
    print('\nforecast :\n', forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(horizon_value))

    test_predictions = forecast.iloc[-len(df_test):]['yhat']
    test_predictions = round(test_predictions).astype('int64')

    # enhance the test set df_test
    df_test['y_hat'] = test_predictions
    df_test['weekday'] = df_test['ds'].dt.dayofweek
    df_test['ds'] = df_test['ds'].dt.strftime('%Y-%m-%d')  # convert column df_test['ds'] to yyyy-mm-dd format
    df_test['APE [%]'] = round(100 * abs(test_predictions - df_test['y']) / df_test['y'], 1)
    df_test['yhat_lower'] = forecast['yhat_lower'].apply(np.floor).astype('int64')
    df_test['yhat_upper'] = forecast['yhat_upper'].apply(np.ceil).astype('int64')
    df_test.drop(['cap', 'floor'], axis = 1, inplace=True)
    print('\ndf_test for horizon =', horizon_argument, ' :\n', df_test)

    mape = round(df_test['APE [%]'].mean(), 1)
    print('\ndf_test : MAPE [%] :', mape)

    df_train_val['hospital'] = hospital  # add column hospital to train-validation set

    print('holidays :', m_best.train_holiday_names)

    return df_test, mape, horizon_argument, initial_argument, period_argument, best_params, cap, df_train_val
