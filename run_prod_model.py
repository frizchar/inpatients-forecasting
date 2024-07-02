# run prophet in production mode

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
import itertools
import warnings
import logging

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
    print("\ndf data types :\n", df.dtypes)
    print("\ndf head :\n", df.head())
    print("\ndf head :\n", df.tail())

    # sort data df by datetime column ds
    df = df.sort_values(by='ds')
    print("\n\033[92mhead of sorted data by datetime ds :\n", df.head(), "\033[00m")
    print("\n\033[91mtail of sorted data by datetime ds :\n", df.tail(), "\033[00m")

    # reset index using column 'ds' and rename the index as 'idx'
    df = df.reset_index(drop=True)
    print("\n\033[94mhead of reindexed data :\n", df.head(), "\033[00m")
    print("\n\033[94mtail of reindexed data :\n", df.tail(), "\033[00m")

    df['weekday'] = df['ds'].dt.dayofweek  # add additional regressor 'weekday'
    # df['month'] = df['ds'].dt.month  # add additional regressor 'month'
    # df['week'] = df['ds'].dt.isocalendar().week  # add additional regressor 'week'

    # define function that yields max value of the following datasets: df, future (see further down for future)
    if cap_type == 'hard':
        cap_factor = 0
    elif cap_type == 'soft':
        cap_factor = 0.08
    else:
        raise Exception("wrong 'cap_type' value")

    cap = max(df['y']) + round(cap_factor* max(df['y']))
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

    # implement cross-validation to evaluate all parameters
    for params in all_params:
        m = Prophet(**params)  # instantiate Prophet using params
        m.add_country_holidays(country_name='GR')  # add Greek holidays
        m.add_regressor('weekday')  # add to Prophet the additional regressor 'weekday'
    #    m.add_regressor('month')  # add to Prophet the additional regressor 'month'
    #    m.add_regressor('week')  # add to Prophet the additional regressor 'week'
        m.fit(df)  # fit model on train-validate set
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
    m_best = Prophet(**best_params).add_regressor('weekday').add_country_holidays(country_name='GR').fit(df)
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

    # make the forecast and process its columns
    forecast = m_best.predict(future)
    forecast['y_hat'] = forecast['yhat']
    forecast['ds'] = forecast['ds'].dt.strftime('%Y-%m-%d')  # convert column forecast['ds'] to yyyy-mm-dd format
    forecast['y_hat'] = round(forecast['y_hat']).astype('int64')
    forecast['yhat_lower'] = forecast['yhat_lower'].apply(np.floor).astype('int64')
    forecast['yhat_upper'] = forecast['yhat_upper'].apply(np.ceil).astype('int64')
    forecast['hospital'] = hospital
    forecast['horizon'] = str(horizon_value)
    forecast = forecast[['hospital','horizon','ds', 'y_hat', 'yhat_lower', 'yhat_upper']].tail(horizon_value)
    forecast.index = np.arange(1, len(forecast) + 1)  # reindex forecast starting from 1
    print('\nforecast for horizon =', horizon_argument, ' :\n', forecast)

    mape = '-'

    df['hospital'] = hospital  # add column hospital to train-validation set

    print('holidays :', m_best.train_holiday_names)

    return forecast, mape, horizon_argument, initial_argument, period_argument, best_params, cap, df
