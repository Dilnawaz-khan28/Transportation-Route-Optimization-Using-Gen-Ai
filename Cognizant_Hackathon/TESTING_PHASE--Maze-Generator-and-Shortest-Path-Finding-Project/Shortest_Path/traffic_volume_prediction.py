import pandas as pd
import joblib
from sklearn import tree
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

# Load the pre-trained model and feature columns
model = joblib.load('decision_tree_model.pkl')
feature_columns = joblib.load('feature_columns.pkl')

def predict_traffic(lat1, lng1, lat2, lng2):
    # Create a DataFrame for the prediction input
    prediction_input = pd.DataFrame({
        'lat1': [lat1], 
        'lng1': [lng1], 
        'lat2': [lat2], 
        'lng2': [lng2]
    })
    
    # Debugging: Print the prediction input
    print("Prediction Input DataFrame:")
    print(prediction_input)

    # Align with training feature columns
    for col in feature_columns:
        if col not in prediction_input.columns:
            prediction_input[col] = 0  # Add missing columns with default values

    prediction_input = prediction_input[feature_columns]  # Reorder columns to match training
    
    # Debugging: Print the aligned DataFrame
    print("Aligned Prediction DataFrame:")
    print(prediction_input)

    # Predict traffic volume
    try:
        prediction = model.predict(prediction_input)
        print(f"Model Prediction: {prediction}")
        return int(prediction[0])
    except Exception as e:
        print(f"Error during prediction: {e}")
        return "Error predicting traffic volume."

if __name__ == "__main__":
    print("predict_traffic function is available.")

    # Load and prepare the training data
    train_path = "c:/Users/dilna/test/Cognizant_Hackathon/input/Train.csv"
    train_set = pd.read_csv(train_path)

    # Prepare Train Data
    train_set['date_time'] = pd.to_datetime(train_set.date_time)
    train_set['year'] = train_set.date_time.dt.year
    train_set['month'] = train_set.date_time.dt.month
    train_set['day'] = train_set.date_time.dt.day
    train_set['hour'] = train_set.date_time.dt.hour

    train_copy = train_set.drop(['date_time'], axis=1)
    train_onehot = pd.get_dummies(train_copy, columns=['is_holiday', 'weather_type', 'weather_description'], 
                                  prefix=['is_holiday', 'weather_type', 'weather_desc'])
    train_onehot = train_onehot.astype(float)

    # Train and Test data
    y_train = train_onehot['traffic_volume']
    x_train = train_onehot.drop(['traffic_volume'], axis=1)

    # Split the training data for validation
    x_train_split, x_val_split, y_train_split, y_val_split = train_test_split(x_train, y_train, test_size=0.2, random_state=42)

    # Train the model
    dec_tree_reg = tree.DecisionTreeRegressor()
    dec_tree_reg.fit(x_train_split, y_train_split)

    # Validate the model
    y_val_preds = dec_tree_reg.predict(x_val_split)
    mse = mean_squared_error(y_val_split, y_val_preds)
    print(f"Validation Mean Squared Error: {mse}")

    # Save the model and feature columns
    joblib.dump(dec_tree_reg, 'decision_tree_model.pkl')
    joblib.dump(x_train.columns.tolist(), 'feature_columns.pkl')  # Ensure it's a list

    # Predict on test set and save results
    test_path = "c:/Users/dilna/test/Cognizant_Hackathon/input/Test.csv"
    test_set = pd.read_csv(test_path)
    test_set['date_time'] = pd.to_datetime(test_set.date_time)
    test_set['year'] = test_set.date_time.dt.year
    test_set['month'] = test_set.date_time.dt.month
    test_set['day'] = test_set.date_time.dt.day
    test_set['hour'] = test_set.date_time.dt.hour

    test_copy = test_set.drop(['date_time'], axis=1)
    test_onehot = pd.get_dummies(test_copy, columns=['is_holiday', 'weather_type', 'weather_description'], 
                                  prefix=['is_holiday', 'weather_type', 'weather_desc'])

    # Align features
    for col in x_train.columns:
        if col not in test_onehot.columns:
            test_onehot[col] = 0  # Add missing columns with default values
    test_onehot = test_onehot[x_train.columns]  # Reorder columns to match

    # Predict and save
    preds = dec_tree_reg.predict(test_onehot)
    preds = preds.astype(int)  # Ensure predictions are integers

    submission = pd.DataFrame({
        'date_time': test_set['date_time'],
        'traffic_volume': preds
    })

    submission.to_csv('dtreereg_final_prediction_submission.csv', index=False)
    print("Submission file created: dtreereg_final_prediction_submission.csv")
