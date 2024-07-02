# save best_params and test results to excel

import pandas as pd


def output_to_excel(df, mape, horizon_value,
                    horizon_argument, initial_argument,
                    period_argument, best_params, cap,
                    df_train_val, hospital, run_mode, cap_type,
                    min_test_date, max_test_date):

    def generate_hospital_name(hospital: str):
        if hospital == '1':
            return 'hospital_1'
        elif hospital == '2':
            return 'hospital_2'
        else:
            return "-"

    def create_filename_prefix(run_mode: str):
        if run_mode == 'test':
            return '_test_inpatients_'
        elif run_mode in ['prod','hybrid']:
            return '_prod_inpatients_'
        else:
            return "wrong 'run_mode' value"

    folder_path = './data_pool/'
    filename = create_filename_prefix(run_mode) + generate_hospital_name(hospital) + '_' + str(horizon_value) + '_days' + '.xlsx'
    file_path = folder_path + filename
    writer = pd.ExcelWriter(path=file_path, engine='xlsxwriter')
    workbook = writer.book


    if run_mode == 'test':
        df[['ds','y','y_hat','APE [%]','yhat_lower','yhat_upper']].\
            to_excel(writer, sheet_name='predictions_on_test_set',
                     index=True, startrow=0, startcol=0) # Start from cell A1
    elif run_mode in ['prod','hybrid']:
        df[['hospital','horizon','ds', 'y_hat', 'yhat_lower', 'yhat_upper']]. \
            to_excel(writer, sheet_name='forecasts_into_the_future',
                     index=True, startrow=0, startcol=0)  # Start from cell A1
    else:
        return

    cell_format_2 = workbook.add_format({'bold': True, 'font_color': 'black'})

    if run_mode == 'test':
        worksheet = writer.sheets['predictions_on_test_set']
    elif run_mode in ['prod','hybrid']:
        worksheet = writer.sheets['forecasts_into_the_future']
    else:
        return

    worksheet.autofit()

    df_train_val['ds'] = df_train_val['ds'].dt.strftime('%Y-%m-%d')
    df_train_val[['ds','y','hospital']].to_excel(writer, sheet_name='train_validation set',
                                      index=True, startrow=0, startcol=0) # Start from cell A1
    worksheet0 = writer.sheets['train_validation set']
    worksheet0.autofit()

    worksheet1 = workbook.add_worksheet('meta')

    worksheet1.write('A1', 'Hospital', cell_format_2)
    worksheet1.write('A2', hospital)
    worksheet1.write('B1', 'Prediction horizon on test set', cell_format_2)
    worksheet1.write('B2', horizon_argument)
    worksheet1.write('C1', 'Cap type', cell_format_2)
    worksheet1.write('C2', cap_type)
    worksheet1.write('D1', 'initial', cell_format_2)
    worksheet1.write('D2', initial_argument)
    worksheet1.write('E1', 'period', cell_format_2)
    worksheet1.write('E2', period_argument)
    worksheet1.write('F1', 'horizon', cell_format_2)
    worksheet1.write('F2', horizon_argument)

    if run_mode in ['test','hybrid']:
        worksheet1.write('G1', 'MAPE [%]', cell_format_2)
        worksheet1.write('G2', mape)
    else:
        worksheet1.write('G1', 'MAPE [%]', cell_format_2)
        worksheet1.write('G2', "no mape value for RUN_MODE = 'prod'")

    worksheet1.write('H1', 'changepoint_prior_scale', cell_format_2)
    worksheet1.write('H2', best_params['changepoint_prior_scale'])
    worksheet1.write('I1', 'seasonality_prior_scale', cell_format_2)
    worksheet1.write('I2', best_params['seasonality_prior_scale'])
    worksheet1.write('J1', 'daily_seasonality', cell_format_2)
    worksheet1.write('J2', best_params['daily_seasonality'])
    worksheet1.write('K1', 'growth', cell_format_2)
    worksheet1.write('K2', best_params['growth'])
    worksheet1.write('L1', 'seasonality_mode', cell_format_2)
    worksheet1.write('L2', best_params['seasonality_mode'])
    worksheet1.write('M1', 'holidays_mode', cell_format_2)
    worksheet1.write('M2', best_params['holidays_mode'])
    worksheet1.write('N1', 'cap', cell_format_2)
    worksheet1.write('N2', cap)
    worksheet1.write('O1', 'floor', cell_format_2)
    worksheet1.write('O2', 0)
    worksheet1.write('P1', 'min_test_date', cell_format_2)
    worksheet1.write('P2', min_test_date)
    worksheet1.write('Q1', 'max_test_date', cell_format_2)
    worksheet1.write('Q2', max_test_date)

    worksheet1.autofit()

    writer.close()

    return
