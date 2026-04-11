# Psych_505_project

This is a web-based psychology experiment application built with Python and Flask. It allows researchers to generate unique experiment links for participants, manage study groups (Time vs. Reward), and track participant results in real-time.

## Features

- **Admin Dashboard**: Generate unique participant links and monitor progress.
- **Real-time Updates**: The admin table refreshes automatically every 3 seconds to show participant progress without reloading the page.
- **Dynamic Experiment Flow**: 
    - Demographics collection.
    - Video-based instructions.
    - 11-question quiz with optional 15-second time limits per page.
- **Data Persistence**: All results are saved to a local SQLite database (`experiment_data.db`).

## Prerequisites

- Python 3.7 or higher

## Environment Setup

It is recommended to use a virtual environment to keep dependencies isolated.

1. **Open your terminal or command prompt** and navigate to the project directory:
   ```bash
   cd Psych_505_project
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - **Windows**: `venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

4. **Install Dependencies**:
   ```bash
   pip install flask
   ```

## Running the Program

1. **Start the Flask server**:
   ```bash
   python app.py
   ```
2. **Access the Admin Panel**: 
   Open your browser and go to `http://127.0.0.1:5000/admin`

## How to Use

1. **Set up a Participant**: On the Admin page, enter a Participant Number (PID) and select the Time and Reward groups. 
2. **Generate Link**: Click "Generate Link." A unique URL will appear at the top.
3. **Conduct Experiment**: Send the link to the participant. 
4. **Monitor Results**: Stay on the Admin page. As the participant answers questions and finishes the study, the table will update automatically with their demographics, scores, and status.
5. **Clear Data**: If you need to reset the study data for a new batch, use the "Clear All Data" button at the bottom of the Admin page.

## File Structure
- `app.py`: The main application logic containing the backend, database setup, and HTML templates.
- `experiment_data.db`: The SQLite database file (created automatically on first run).