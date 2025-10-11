# Streamlit Health Assistant UI

A modern, user-friendly web interface for the Health Journal application built with Streamlit.

## Features

✨ **Modern UI/UX**
- Clean, professional design
- Responsive layout
- Progress tracking
- Interactive forms

🏥 **Complete Workflow**
1. Patient ID entry and validation
2. Medical history review
3. Symptom assessment with quick selectors
4. Automated test recommendations
5. Downloadable reports (JSON & Text)

📊 **Key Capabilities**
- Real-time patient data lookup
- Visual symptom checklist
- Smart diagnostic test recommendations
- Session state management
- Report generation and download

## Installation

All dependencies are already installed if you've run:
```bash
pip install -r requirements.txt
```

## Running the App

### Method 1: Using the activation script

**macOS/Linux:**
```bash
source venv_mac/bin/activate
streamlit run streamlit_app.py
```

**Windows:**
```cmd
venv_mac\Scripts\activate
streamlit run streamlit_app.py
```

### Method 2: Quick launch (one command)

```bash
cd "/Users/saivignesh/Downloads/Health Journal" && source venv_mac/bin/activate && streamlit run streamlit_app.py
```

## Accessing the App

After running the command, Streamlit will automatically:
- Start a local web server
- Open your default browser to `http://localhost:8501`

If it doesn't open automatically, manually navigate to:
```
http://localhost:8501
```

## Using the App

### Step 1: Enter Patient ID
- On the welcome screen, enter a valid Patient ID
- Sample IDs: P001, P002, P003, P004, P005

### Step 2: Review Patient Information
- Verify your medical records
- Add any new allergies or conditions
- Click "Continue to Symptoms"

### Step 3: Report Symptoms
- Describe your symptoms in the text area
- Use the quick symptom selector for common symptoms
- Click "Generate Report"

### Step 4: View Summary
- Review the health assessment summary
- Check recommended diagnostic tests
- Download reports (JSON or Text format)
- Start a new assessment or exit

## Features in Detail

### 🎨 User Interface
- **Progress Sidebar**: Track your current step in the assessment
- **Color-Coded Boxes**: 
  - Green (Success): Confirmations and completions
  - Blue (Info): Helpful information and tips
  - Yellow (Warning): Important notices and alerts
  - Red (Error): Validation errors

### 📋 Patient Data
- Automatically loads from `Dummy Patient Data for OCR Use Case.xlsx`
- Displays complete medical history
- Shows drug allergies and past conditions

### 🩺 Symptom Assessment
- **Free-form text input**: Describe symptoms in detail
- **Quick checkboxes**: Select common symptoms quickly
- **Combined input**: Text and checkboxes are merged for analysis

### 🔬 Diagnostic Recommendations
Smart recommendations based on symptoms:
- Fever → CBC (Complete Blood Count)
- Cough → Chest X-Ray
- Fatigue → Thyroid and iron tests
- Headache → Neurological exam/CT scan
- Chest Pain → ECG and cardiac enzymes
- Breathing Issues → Pulmonary function tests

### 💾 Report Download
- **JSON Format**: For data integration and processing
- **Text Format**: Human-readable summary
- Includes all patient information, symptoms, and recommendations

## Keyboard Shortcuts (Streamlit)

- `R` - Rerun the app
- `C` - Clear cache
- `?` - Show keyboard shortcuts

## Configuration

### MongoDB (Optional)
The app works with or without MongoDB. To enable database logging:
1. Follow instructions in `MONGODB_SETUP.md`
2. Configure your MongoDB Atlas connection
3. Restart the app

### API Configuration
API credentials are configured in the app:
- API Key: Set in `streamlit_app.py`
- Base URL: PwC internal GenAI service
- Model: Azure GPT-4

## Troubleshooting

### Port Already in Use
If port 8501 is busy, run on a different port:
```bash
streamlit run streamlit_app.py --server.port 8502
```

### Excel File Not Found
Ensure `Dummy Patient Data for OCR Use Case.xlsx` is in the same directory as `streamlit_app.py`

### Session Issues
Click the "🔄 Reset Session" button in the sidebar to clear all session data

### Styling Issues
Force refresh your browser: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows/Linux)

## Stopping the App

To stop the Streamlit server:
- Press `Ctrl+C` in the terminal
- Or close the terminal window

## Comparison: CLI vs Streamlit

| Feature | CLI (app.py) | Streamlit |
|---------|-------------|-----------|
| Interface | Terminal text | Web browser |
| User Input | keyboard input() | Forms & buttons |
| Data Display | Plain text | Formatted tables |
| Progress Tracking | None | Visual progress bar |
| Reports | Console logs | Downloadable files |
| Session | Single run | Persistent state |
| Multi-user | No | Yes (separate sessions) |

## Development

### Modifying the App
Edit `streamlit_app.py` and save. Streamlit will prompt you to rerun automatically.

### Testing Changes
Use the "Always rerun" option in Streamlit for live updates during development.

### Adding Features
- New pages: Add to session state stages
- New forms: Use `st.form()` for grouped inputs
- Data visualization: Use `st.line_chart()`, `st.bar_chart()`, etc.

## Production Deployment

For production deployment, consider:
- **Streamlit Cloud**: Free hosting for public apps
- **Docker**: Containerize the application
- **Authentication**: Add login system with `streamlit-authenticator`
- **Database**: Enable MongoDB Atlas for persistent storage

## Support

For issues or questions:
1. Check this README first
2. Review `MONGODB_SETUP.md` for database issues
3. Check Streamlit documentation: https://docs.streamlit.io

## Credits

- Built with [Streamlit](https://streamlit.io/)
- Powered by Azure GPT-4
- MongoDB Atlas for data storage

