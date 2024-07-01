# inpatients_forecasting
We are forecasting the number of hospital inpatients **_y_** for a given prediction horizon **_h_** for hospitals **(hospital_1, hospital_2)**.

The $\color{blue}prophet$ algorithm is implemented on a dataset containing the columns **ds := _date_** and **y := _number of inpatients_**.

The code iterates over _n_ .xlsx files, each one containing data for each hospital. In this implementation _n = 2_.
