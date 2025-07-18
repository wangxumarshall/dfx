# Feature Tracer

This project is a simple feature tracer to monitor the completeness of an operating system's features.

## How to run

### Backend

1.  Navigate to the `backend` directory:
    ```bash
    cd feature_tracer/backend
    ```
2.  Install the required dependencies:
    ```bash
    pip install Flask Flask-Cors pandas openpyxl
    ```
3.  Run the Flask application:
    ```bash
    python app.py
    ```
    The backend will be running at `http://localhost:5001`.

### Frontend

1.  Open the `feature_tracer/frontend/index.html` file in your web browser.

You should now see the feature tracer dashboard, with data populated from the backend.

## Data

The data for the feature tracer is stored in `feature_tracer/backend/features.xlsx`. You can modify this file to update the data.

## Template

You can download an empty Excel template by clicking the "Download Template" button in the top right corner of the page. This will download a file named `features_template.xlsx` with the correct headers for the `domains` and `features` sheets. You can then fill out this template and rename it to `features.xlsx` to use it as the data source.
