# -*- coding: utf-8 -*-
"""new_airpollution_app.py

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1_RlrACAsI-jqq9Y_36zEDd2k-HJaGhbC
"""

# app.py

import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
import io # For in-memory file operations (downloading plots)
import joblib # For saving/loading models and scalers
import os # Import os for path joining

# Scikit-learn imports for models and preprocessing
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score, classification_report, confusion_matrix


# --- GLOBAL DATA AND MODEL LOADING ---
# This section loads your fully preprocessed data and trained models/scalers once when the app starts.

# Define the base path for your data and models in Google Drive
# IMPORTANT: MAKE SURE THIS PATH IS EXACTLY WHERE YOU SAVED YOUR FILES.
# Using 'analyzed_data1.csv' as per your last provided path.
GOOGLE_DRIVE_BASE_PATH = "/content/drive/MyDrive/data sets/Merged cities/"

@st.cache_data # Cache the DataFrame loading for performance
def load_and_preprocess_data_for_app(): # Renamed to be more descriptive
    try:
        # Load the saved, fully preprocessed DataFrame from the absolute path
        df_app = pd.read_csv(os.path.join(GOOGLE_DRIVE_BASE_PATH, "analyzed_data1.csv")) # CORRECTED FILE NAME AND PATH USAGE

        # --- CRITICAL FIXES FOR DATA TYPES AFTER CSV LOAD ---
        # Ensure 'Date' is datetime (often saved as string in CSV)
        if 'Date' in df_app.columns:
            df_app['Date'] = pd.to_datetime(df_app['Date'], errors='coerce')
            df_app.dropna(subset=['Date'], inplace=True) # Drop rows where Date conversion failed

        # Ensure 'year_month' is handled correctly if needed for plotting or other logic
        if 'year_month' in df_app.columns:
            try:
                df_app['year_month'] = df_app['year_month'].astype(str).str.replace(r'(\d{4})-(\d{2})', r'\1-\2-01').astype('datetime64[ns]').dt.to_period('M')
            except Exception as e:
                st.warning(f"Could not convert 'year_month' to PeriodDtype. Keeping as string/object. Error: {e}")

    except FileNotFoundError:
        st.error(f"Error: 'analyzed_data1.csv' not found at {os.path.join(GOOGLE_DRIVE_BASE_PATH, 'analyzed_data1.csv')}. Please ensure the file exists there.")
        st.stop() # Stop the app if data can't be loaded
    return df_app

@st.cache_resource # Use cache_resource for models/scalers as they are objects (loaded once)
def load_trained_models_and_scaler(): # Renamed to load_trained_models_and_scaler
    trained_model_reg = None
    trained_scaler = None
    trained_model_clf = None

    try:
        trained_model_reg = joblib.load(os.path.join(GOOGLE_DRIVE_BASE_PATH, 'linear_regression_model.pkl'))
    except FileNotFoundError:
        st.warning(f"Warning: 'linear_regression_model.pkl' not found at {os.path.join(GOOGLE_DRIVE_BASE_PATH, 'linear_regression_model.pkl')}. Regression model functionality will be limited.")
    except Exception as e:
        st.error(f"Error loading regression model: {e}")

    try:
        trained_scaler = joblib.load(os.path.join(GOOGLE_DRIVE_BASE_PATH, 'standard_scaler.pkl'))
    except FileNotFoundError:
        st.warning(f"Warning: 'standard_scaler.pkl' not found at {os.path.join(GOOGLE_DRIVE_BASE_PATH, 'standard_scaler.pkl')}. Scaling functionality will be limited.")
    except Exception as e:
        st.error(f"Error loading scaler: {e}")

    try:
        trained_model_clf = joblib.load(os.path.join(GOOGLE_DRIVE_BASE_PATH, 'random_forest_clf_model.pkl'))
    except FileNotFoundError:
        st.warning(f"Warning: 'random_forest_clf_model.pkl' not found at {os.path.join(GOOGLE_DRIVE_BASE_PATH, 'random_forest_clf_model.pkl')}. Classification model functionality will be limited.")
    except Exception as e:
        st.error(f"Error loading classification model: {e}")

    return trained_model_reg, trained_scaler, trained_model_clf

# Global variables for loaded data, models, scaler
app_data = load_and_preprocess_data_for_app() # Corrected function call
trained_reg_model, trained_scaler, trained_clf_model = load_trained_models_and_scaler() # Corrected function call

# --- Page 1: Data Overview ---
def data_overview(data): # 'data' here is app_data from global scope
    st.title("📊 1. Data Overview")
    st.write("This page provides a structured overview of the **fully preprocessed and engineered dataset** you are working with.")

    num_rows = st.sidebar.slider("Number of rows to preview", min_value=5, max_value=50, value=5, step=5)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📐 Dataset Shape")
        st.metric(label="Rows", value=data.shape[0])
        st.metric(label="Columns", value=data.shape[1])

    with col2:
        st.subheader("🧬 Data Types")
        buffer = io.StringIO()
        data.info(buf=buffer)
        s = buffer.getvalue()
        st.text(s)

    with st.expander("🔍 Preview Sample Data"):
        st.dataframe(data.head(num_rows))

    with st.expander("📈 Summary Statistics"):
        st.dataframe(data.describe(include='all'))

    with st.expander("🚫 Missing Values Check"):
        missing_values_summary = data.isnull().sum().rename('Missing Count').to_frame()
        missing_values_summary['% of Total Values'] = (missing_values_summary['Missing Count'] / data.shape[0]) * 100
        st.dataframe(missing_values_summary[missing_values_summary['Missing Count'] > 0].sort_values(by='Missing Count', ascending=False))
        if missing_values_summary['Missing Count'].sum() == 0:
            st.success("✅ No missing values found in the processed dataset!")
        else:
            st.error("❌ Warning: Missing values are still present in the processed dataset. This should be addressed during preprocessing.")

    # ---- Categorical Column Distribution (Now using one-hot encoded bools) ----
    boolean_cols = data.select_dtypes(include='bool').columns.tolist()

    if len(boolean_cols) > 0:
        st.subheader("🧮 One-Hot Encoded Feature Distribution (Boolean Counts)")
        st.info("Since categorical features were one-hot encoded, their distributions are shown as boolean counts (True/False).")

        selected_bool_col = st.selectbox("Select a one-hot encoded (boolean) column to visualize", boolean_cols, key="bool_dist_select")

        bool_counts = data[selected_bool_col].value_counts().reset_index()
        bool_counts.columns = [selected_bool_col, 'Count']

        plt.figure(figsize=(8, 5))
        sns.barplot(data=bool_counts, x=selected_bool_col, y='Count', palette='pastel', hue=selected_bool_col, legend=False)
        plt.title(f"Distribution of {selected_bool_col}")
        st.pyplot(plt.gcf())
        plt.clf()
    else:
        st.info("No boolean (one-hot encoded) columns found for distribution plot in this section.")

    st.write("---") # Separator


# --- Page 2: Exploratory Data Analysis (EDA) ---
def eda(data): # 'data' here is app_data from global scope
    st.title("📊 2. Exploratory Data Analysis (EDA)")
    st.write("This section provides visual insights into the dataset.")

    # Features (from fully processed data) - ensure these are the features used in model training if applicable
    features_for_eda_selection = [col for col in data.columns if col not in ['pollution_category', 'PM2.5', 'Date', 'year_month']] # Exclude more columns relevant to final cleanup
    numeric_data_for_selectboxes = data[features_for_eda_selection].select_dtypes(include=np.number).columns.tolist() # Select only numeric features

    if not numeric_data_for_selectboxes:
        st.warning("No suitable numeric columns available for EDA. Ensure your data is processed and features are selected.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📉 Correlation Heatmap",
        "📊 Histogram",
        "🔁 Scatter Plot",
        "📦 Box Plot (Numeric vs. Boolean)",
        "📈 Line Chart (Time Series)"
    ])

    # Tab 1: Correlation Heatmap
    with tab1:
        st.subheader("Correlation Heatmap")
        st.caption("Shows pairwise correlation between selected numeric features.")

        key_features_for_heatmap = [
            'PM2.5', 'PM10', 'SO2', 'NO2', 'CO', 'O3',
            'TEMP', 'PRES', 'DEWP', 'RAIN', 'WSPM',
            'PM2.5_lag_1h', 'PM2.5_lag_24h',
            'PM2.5_rolling_mean_6h', 'PM2.5_rolling_mean_24h',
            'hour_sin', 'hour_cos', 'wd_sin', 'wd_cos',
            'is_weekend',
            # Add a few key one-hot encoded station/season/dayofweek if desired, e.g.:
            # 'station_Dingling', 'season_Winter', 'day_of_week_name_Monday'
        ]
        available_features_for_heatmap = [f for f in key_features_for_heatmap if f in data.columns and pd.api.types.is_numeric_dtype(data[f])]

        if len(available_features_for_heatmap) > 1:
            corr = data[available_features_for_heatmap].corr()
            plt.figure(figsize=(12, 10))
            sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5, cbar_kws={'shrink': .8})
            plt.title("Selected Feature Correlation Heatmap")
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            st.pyplot(plt.gcf())
            plt.clf()
        else:
            st.info("Not enough selected features for a correlation heatmap. Please ensure your data has sufficient numeric columns.")

    # Tab 2: Histogram
    with tab2:
        st.subheader("Histogram")
        hist_col = st.selectbox("Select a column for histogram", numeric_data_for_selectboxes, key="hist")
        bins = st.slider("Number of bins", min_value=5, max_value=100, value=30)

        plt.figure(figsize=(10, 6))
        sns.histplot(data[hist_col], kde=True, bins=bins, color='orange')
        plt.title(f"Histogram of {hist_col}")
        st.pyplot(plt.gcf())
        plt.clf()

    # Tab 3: Scatter Plot
    with tab3:
        st.subheader("Scatter Plot")
        x_scatter = st.selectbox("X-axis", numeric_data_for_selectboxes, key="scatter_x")
        y_scatter = st.selectbox("Y-axis", numeric_data_for_selectboxes, key="scatter_y")

        if x_scatter and y_scatter and x_scatter != y_scatter: # Ensure both selected and different
            plt.figure(figsize=(10, 6))
            sns.scatterplot(x=data[x_scatter], y=data[y_scatter], alpha=0.6, s=10)
            plt.title(f"{x_scatter} vs {y_scatter}")
            st.pyplot(plt.gcf())
            plt.clf()
        else:
            st.info("Please select different columns for X and Y axes.")

    # Tab 4: Box Plot
    with tab4:
        st.subheader("Box Plot (Numeric vs. Categorical/Boolean)")

        boolean_cols_for_boxplot_x = data.select_dtypes(include='bool').columns.tolist()
        original_categorical_cols = data.select_dtypes(include=['object', 'category']).columns.tolist()

        cat_col_options = []
        if boolean_cols_for_boxplot_x:
            cat_col_options.extend(boolean_cols_for_boxplot_x)
        if original_categorical_cols:
            cat_col_options.extend(original_categorical_cols)

        if cat_col_options:
            cat_col_for_boxplot = st.selectbox("Select Categorical/Boolean Column (X-axis)", cat_col_options)
            num_col_for_boxplot = st.selectbox("Select Numeric Column (Y-axis)", numeric_data_for_selectboxes, key="boxplot_y")

            if num_col_for_boxplot:
                plt.figure(figsize=(10, 6))
                sns.boxplot(x=data[cat_col_for_boxplot], y=data[num_col_for_boxplot])
                plt.xticks(rotation=45)
                plt.title(f"{num_col_for_boxplot} Distribution across {cat_col_for_boxplot}")
                st.pyplot(plt.gcf())
                plt.clf()
            else:
                st.info("Please select a numeric column for the Y-axis.")
        else:
            st.info("No suitable categorical or boolean columns found for box plotting X-axis.")


    # Tab 5: Line Chart (for time series)
    with tab5:
        st.subheader("Line Chart (Time Series)")
        if 'Date' in data.columns and pd.api.types.is_datetime64_any_dtype(data['Date']):
            line_col = st.selectbox("Select Numeric Column to Plot Over Time", numeric_data_for_selectboxes, key="linechart_y")

            if line_col:
                plt.figure(figsize=(12, 6))
                sns.lineplot(x=data['Date'], y=data[line_col], errorbar=None)
                plt.title(f"{line_col} Over Time")
                plt.xlabel("Date")
                plt.ylabel(line_col)
                plt.xticks(rotation=45)
                st.pyplot(plt.gcf())
                plt.clf()
        else:
            st.info("Datetime column 'Date' not found or not in correct format. Ensure it's in your processed dataset for time series plots.")


# Page 3: Modeling and Prediction
def modeling_and_prediction(data):
    st.title("🤖 3. Modeling and Prediction")
    st.write("Here you can train and evaluate different machine learning models for air quality prediction.")

    global trained_reg_model, trained_scaler, trained_clf_model

    st.subheader("1. Prediction Task & Model Loading")

    prediction_task = st.radio("Choose Prediction Task:", ["PM2.5 Regression", "AQI Classification"])

    use_pretrained_model = False
    if prediction_task == "PM2.5 Regression" and trained_reg_model is not None:
        use_pretrained_model = st.checkbox("Use Pre-trained Regression Model (if available)", value=True)
    elif prediction_task == "AQI Classification" and trained_clf_model is not None:
        use_pretrained_model = st.checkbox("Use Pre-trained Classification Model (if available)", value=True)
    else:
        st.warning("No pre-trained model found for this task. A new model will be trained.")
        use_pretrained_model = False

    st.subheader("2. Target and Feature Selection")

    target_variable = ''
    potential_features = []

    if prediction_task == "PM2.5 Regression":
        target_variable = 'PM2.5'
        potential_features = [col for col in data.columns if col not in ['PM2.5', 'pollution_category', 'Date', 'year_month']]
        st.info("Target: PM2.5 (Regression).")

    else: # AQI Classification
        target_variable = 'pollution_category'
        potential_features = [col for col in data.columns if col not in ['pollution_category', 'PM2.5', 'Date', 'year_month']]
        st.info("Target: AQI (Classification).")

    st.write(f"Selected Target Variable: **{target_variable}**")

    default_selected_features = [f for f in ['PM2.5_lag_1h', 'PM10', 'TEMP', 'WSPM', 'NO2', 'CO', 'O3', 'PM2.5_rolling_mean_6h', 'hour_sin', 'is_weekend'] if f in potential_features]
    selected_features = st.multiselect("🧮 Select Feature Variables", potential_features, default=default_selected_features)

    if not selected_features:
        st.warning("Please select at least one feature variable.")
        return

    X = data[selected_features]
    y = data[target_variable]

    st.subheader("3. Data Splitting (Chronological)")
    test_size_ratio = st.slider("Test Set Size (e.g., 0.2 for 20%)", min_value=0.1, max_value=0.5, value=0.2, step=0.05)

    split_point = int(len(X) * (1 - test_size_ratio))
    X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
    y_train, y_test = y.iloc[:split_point], y.iloc[split_point:]

    st.write(f"Train set shape: {X_train.shape}")
    st.write(f"Test set shape: {X_test.shape}")

    st.subheader("4. Feature Scaling")
    st.write("Numerical features will be scaled using StandardScaler.")

    numerical_features_to_scale = X_train.select_dtypes(include=np.number).columns.tolist()
    features_to_scale = [col for col in numerical_features_to_scale if not (X_train[col].nunique() <= 2 and X_train[col].isin([0, 1]).all())]

    X_train_scaled = X_train.copy()
    X_test_scaled = X_test.copy()

    if use_pretrained_model and trained_scaler is not None:
        scaler = trained_scaler
        st.info("Using pre-trained StandardScaler.")
    else:
        scaler = StandardScaler()
        st.info("Fitting and using new StandardScaler.")

    X_train_scaled[features_to_scale] = scaler.fit_transform(X_train[features_to_scale])
    X_test_scaled[features_to_scale] = scaler.transform(X_test[features_to_scale])

    st.success("Features scaled successfully!")

    st.subheader("5. Model Selection & Training")

    model = None

    if prediction_task == "PM2.5 Regression":
        model_options = ["Linear Regression", "Decision Tree Regressor", "K-Nearest Neighbors", "Random Forest Regressor"]
        chosen_model_type = st.selectbox("Choose a Regression Model", model_options)

        if chosen_model_type == "Linear Regression":
            model = LinearRegression()
        elif chosen_model_type == "Decision Tree Regressor":
            model = DecisionTreeRegressor(random_state=42)
        elif chosen_model_type == "K-Nearest Neighbors":
            n_neighbors_knn = st.slider("KNN: Number of Neighbors", min_value=1, max_value=20, value=5, step=1, key="knn_n")
            model = KNeighborsRegressor(n_neighbors=n_neighbors_knn)
        elif chosen_model_type == "Random Forest Regressor":
            n_estimators_rfr = st.slider("RFR: Number of Trees", min_value=50, max_value=500, value=100, step=50, key="rfr_n")
            model = RandomForestRegressor(n_estimators=n_estimators_rfr, random_state=42, n_jobs=-1)

    else: # AQI Classification
        model_options = ["Random Forest Classifier"]
        chosen_model_type = st.selectbox("Choose a Classification Model", model_options)

        if chosen_model_type == "Random Forest Classifier":
            n_estimators_rfc = st.slider("RFC: Number of Trees", min_value=50, max_value=500, value=100, step=50, key="rfc_n")
            model = RandomForestClassifier(n_estimators=n_estimators_rfc, random_state=42, n_jobs=-1, class_weight='balanced')

    if use_pretrained_model:
        if prediction_task == "PM2.5 Regression" and trained_reg_model is not None:
            if chosen_model_type == "Linear Regression":
                model = trained_reg_model
                st.info(f"Using pre-trained {chosen_model_type} model.")
            else:
                st.warning(f"Pre-trained model type ({type(trained_reg_model).__name__}) does not match selected '{chosen_model_type}'. Training new model.")
                if model is not None: model.fit(X_train_scaled, y_train)
        elif prediction_task == "AQI Classification" and trained_clf_model is not None:
            if chosen_model_type == "Random Forest Classifier":
                model = trained_clf_model
                st.info(f"Using pre-trained {chosen_model_type} model.")
            else:
                st.warning(f"Pre-trained model type ({type(trained_clf_model).__name__}) does not match selected '{chosen_model_type}'. Training new model.")
                if model is not None: model.fit(X_train_scaled, y_train)
        else:
            st.warning("Pre-trained model not found or does not match task/type. Training a new model.")
            if model is not None: model.fit(X_train_scaled, y_train)
    else:
        st.write("Training a new model based on selected parameters...")
        if model is not None: model.fit(X_train_scaled, y_train)

    if model is None:
        st.error("Model could not be instantiated or loaded. Please check your selections and file paths.")
        return

    st.success("Model training/loading complete!")

    y_pred = model.predict(X_test_scaled)

    st.subheader("6. Model Performance Evaluation")

    if prediction_task == "PM2.5 Regression":
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        st.metric("RMSE", f"{rmse:.2f}")
        st.metric("MAE", f"{mae:.2f}")
        st.metric("R² Score", f"{r2:.2f}")

        st.subheader("7. Predicted vs Actual Plot (Full Test Set)")
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x=y_test, y=y_pred, alpha=0.6, s=10)
        plt.xlabel("Actual PM2.5")
        plt.ylabel("Predicted PM2.5")
        plt.title(f"Actual vs Predicted PM2.5 ({chosen_model_type})")
        plt.grid(True)
        st.pyplot(plt.gcf())
        plt.clf()

        st.subheader("8. Regression Line Plot (Actual vs Predicted)")
        plt.figure(figsize=(10, 6))
        sns.regplot(x=y_test, y=y_pred, scatter_kws={'alpha':0.3, 's':10}, line_kws={'color':'red'})
        plt.xlabel("Actual PM2.5")
        plt.ylabel("Predicted PM2.5")
        plt.title(f"Regression Line ({chosen_model_type})")
        plt.grid(True)
        st.pyplot(plt.gcf())
        plt.clf()

    else: # AQI Classification
        accuracy = accuracy_score(y_test, y_pred)
        st.metric("Accuracy", f"{accuracy:.4f}")

        st.subheader("Classification Report")
        st.text(classification_report(y_test, y_pred))

        st.subheader("Confusion Matrix")
        cm = confusion_matrix(y_test, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=model.classes_, yticklabels=model.classes_)
        plt.title(f'Confusion Matrix ({chosen_model_type})')
        plt.xlabel('Predicted Label')
        plt.ylabel('True Label')
        st.pyplot(plt.gcf())
        plt.clf()


    st.subheader("9. Feature Importance")
    if hasattr(model, 'feature_importances_') and chosen_model_type not in ["Linear Regression", "K-Nearest Neighbors"]:
        importance = model.feature_importances_
        feature_importance_df = pd.DataFrame({
            'Feature': X.columns,
            'Importance': importance
        }).sort_values(by='Importance', ascending=False)
        st.dataframe(feature_importance_df)

        plt.figure(figsize=(10, min(len(feature_importance_df.head(15))*0.6, 10)))
        sns.barplot(x='Importance', y='Feature', data=feature_importance_df.head(15), palette='viridis')
        plt.title("Top 15 Feature Importance")
        st.pyplot(plt.gcf())
        plt.clf()
    elif chosen_model_type == "Linear Regression":
        st.subheader("9. Feature Coefficients (Linear Regression)")
        if hasattr(model, 'coef_'):
            coef_df = pd.DataFrame({'Feature': X.columns, 'Coefficient': model.coef_}).sort_values(by='Coefficient', ascending=False)
            st.dataframe(coef_df)
            plt.figure(figsize=(10, min(len(coef_df)*0.6, 10)))
            sns.barplot(x='Coefficient', y='Feature', data=coef_df.head(15), palette='coolwarm')
            plt.title("Top 15 Feature Coefficients")
            st.pyplot(plt.gcf())
            plt.clf()

    st.subheader("10. Download Results & Model")
    results_df = pd.DataFrame({"Actual": y_test, "Predicted": y_pred})
    csv_data_predictions = results_df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Predictions CSV", csv_data_predictions, file_name="predictions.csv", mime="text/csv")

    if st.button("💾 Save Trained Model & Scaler"):
        model_filename = f"{chosen_model_type.lower().replace(' ', '_')}_model.pkl"
        scaler_filename = "standard_scaler.pkl"

        if scaler is not None:
             joblib.dump(scaler, scaler_filename)
             st.success(f"Scaler saved as {scaler_filename}")
        joblib.dump(model, model_filename)
        st.success(f"Model saved as {model_filename}")

        with open(model_filename, 'rb') as f:
            st.download_button(f"Download {chosen_model_type} Model", f, file_name=model_filename, mime="application/octet-stream")
        if scaler is not None:
            with open(scaler_filename, 'rb') as f:
                st.download_button("Download StandardScaler", f, file_name=scaler_filename, mime="application/octet-stream")

def main():
    st.set_page_config(page_title="Beijing Air Pollution Analysis App", layout="wide")
    data = load_data()
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Data Overview", "EDA", "Modeling and Prediction"])
    if page == "Data Overview":
        data_overview(data)
    elif page == "EDA":
        eda(data)
    elif page == "Modeling and Prediction":
        modeling_and_prediction(data)
    if __name__ == "__main__":
      main()