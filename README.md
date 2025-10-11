# 🏥 Health Journal - AI-Powered Healthcare Assistant

A comprehensive healthcare management system with AI-powered symptom analysis, patient record management, and diagnostic test recommendations.

## 🌟 Features

### ✨ Modern Web Interface (NEW!)
- **Streamlit-powered UI** - Beautiful, responsive web application
- **Interactive Forms** - Easy-to-use patient intake and symptom reporting
- **Progress Tracking** - Visual workflow from patient ID to final report
- **Downloadable Reports** - Export assessments in JSON or text format

### 🏥 Healthcare Management
- **Patient Record Management** - Load and display patient medical history
- **Symptom Analysis** - AI-powered analysis using Azure GPT-4
- **Smart Recommendations** - Automated diagnostic test suggestions
- **Medical History Tracking** - Drug allergies and past conditions

### ☁️ Cloud Integration
- **MongoDB Atlas** - Cloud database for persistent storage
- **Azure GPT-4** - Advanced AI language model integration
- **Flexible Configuration** - Environment-based settings

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or download the project
cd "Health Journal"

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Streamlit Web App (Recommended)

**macOS/Linux:**
```bash
./run_streamlit.sh
```

**Windows:**
```cmd
run_streamlit.bat
```

**Manual Launch:**
```bash
source venv_mac/bin/activate  # On Windows: venv_mac\Scripts\activate
streamlit run streamlit_app.py
```

The app will automatically open in your browser at `http://localhost:8501`

### 3. Alternative: Run CLI Version

```bash
source venv_mac/bin/activate  # On Windows: venv_mac\Scripts\activate
python app.py
```

## 📁 Project Structure

```
Health Journal/
├── streamlit_app.py          # 🆕 Modern Web UI (Streamlit)
├── app.py                     # Original CLI application
├── project.py                 # Project configuration
├── requirements.txt           # Python dependencies
│
├── std_hub/                   # Core modules
│   ├── llm.py                # AI/LLM integration
│   ├── llm_logs.py           # Logging functionality
│   ├── utils.py              # Utility functions
│   ├── constants.py          # Configuration constants
│   └── db/
│       └── mongodb.py        # MongoDB Atlas connection
│
├── Data Files/
│   ├── Dummy Patient Data for OCR Use Case.xlsx
│   ├── HealthMapping.csv
│   ├── mappings.csv
│   └── SlotsMapping.csv
│
├── Documentation/
│   ├── README.md             # This file
│   ├── STREAMLIT_README.md   # Streamlit UI guide
│   ├── MONGODB_SETUP.md      # MongoDB configuration
│   └── CHANGES_SUMMARY.md    # Change log
│
├── Launchers/
│   ├── run_streamlit.sh      # macOS/Linux launcher
│   └── run_streamlit.bat     # Windows launcher
│
└── Configuration/
    ├── env.template          # Environment template
    └── test_mongodb_connection.py
```

## 💻 Two Ways to Use

### Option 1: Streamlit Web UI (Recommended) 🆕

**Features:**
- ✅ Beautiful web interface
- ✅ Interactive forms and buttons
- ✅ Visual progress tracking
- ✅ Downloadable reports
- ✅ Multi-user support
- ✅ Session management

**Launch:**
```bash
./run_streamlit.sh  # or run_streamlit.bat on Windows
```

**Access:** `http://localhost:8501`

### Option 2: Command Line Interface

**Features:**
- ✅ Terminal-based interaction
- ✅ Text input prompts
- ✅ Console output
- ✅ Async workflow

**Launch:**
```bash
python app.py
```

## 📖 Usage Guide

### Streamlit Web App Workflow

1. **Enter Patient ID**
   - Input your Patient ID (e.g., P001, P002, P003)
   - System validates and loads patient records

2. **Review Patient Information**
   - View medical history
   - Check drug allergies and past conditions
   - Add any new health information

3. **Report Symptoms**
   - Describe symptoms in detail
   - Use quick checkboxes for common symptoms
   - System combines all inputs

4. **View Assessment Summary**
   - Review recommended diagnostic tests
   - See complete health assessment
   - Download reports (JSON/Text)

### Sample Patient IDs for Testing

- `P001` - Sample patient 1
- `P002` - Sample patient 2
- `P003` - Sample patient 3
- `P004` - Sample patient 4
- `P005` - Sample patient 5

## 🔧 Configuration

### MongoDB Atlas (Optional)

The application works with or without MongoDB. To enable:

1. **Create MongoDB Atlas account** (free tier available)
2. **Get connection string** from Atlas dashboard
3. **Configure:**

```bash
# Option 1: Use .env file (recommended)
cp env.template .env
# Edit .env with your connection string

# Option 2: Set environment variable
export MONGODB_URI="mongodb+srv://user:pass@cluster.mongodb.net/db"
```

4. **Test connection:**
```bash
python test_mongodb_connection.py
```

See `MONGODB_SETUP.md` for detailed instructions.

### API Configuration

API credentials are configured in the code:
- **API Key:** PwC internal GenAI service key
- **Base URL:** `https://genai-sharedservice-apac.pwcinternal.com/v1`
- **Model:** `azure.gpt-4o-2024-11-20`

## 📦 Dependencies

- **pandas** - Data manipulation and analysis
- **openpyxl** - Excel file reading
- **langchain-openai** - LangChain OpenAI integration
- **openai** - OpenAI API client
- **pymongo** - MongoDB driver
- **python-dotenv** - Environment variable management
- **streamlit** - 🆕 Web UI framework

Install all:
```bash
pip install -r requirements.txt
```

## 🧪 Testing

### Test MongoDB Connection
```bash
python test_mongodb_connection.py
```

### Test Streamlit App
```bash
streamlit run streamlit_app.py
```

## 📊 Diagnostic Recommendations

The system provides smart test recommendations based on symptoms:

| Symptom | Recommended Tests |
|---------|------------------|
| Fever | CBC (Complete Blood Count) |
| Cough | Chest X-Ray |
| Fatigue | Thyroid function, Iron panel |
| Headache | Neurological exam, CT scan |
| Chest Pain | ECG, Cardiac enzymes |
| Breathing Issues | Pulmonary function tests |

## 🛠️ Troubleshooting

### Streamlit won't start
- Check if port 8501 is available
- Try different port: `streamlit run streamlit_app.py --server.port 8502`

### Excel file not found
- Ensure `Dummy Patient Data for OCR Use Case.xlsx` is in project root
- Check file name and extension

### MongoDB connection issues
- App works without MongoDB
- See `MONGODB_SETUP.md` for configuration
- Check firewall settings for MongoDB Atlas

### Import errors
- Activate virtual environment first
- Run: `pip install -r requirements.txt`

## 📝 Development

### Adding Features

**To Streamlit UI:**
1. Edit `streamlit_app.py`
2. Add new stages to session state
3. Create new UI components
4. Test with `streamlit run streamlit_app.py`

**To Core Logic:**
1. Edit modules in `std_hub/`
2. Update both `streamlit_app.py` and `app.py` if needed
3. Test both interfaces

### Code Structure

- `streamlit_app.py` - Web UI entry point
- `app.py` - CLI entry point
- `std_hub/llm.py` - AI integration layer
- `std_hub/db/mongodb.py` - Database layer
- `project.py` - Project initialization

## 🚢 Deployment

### Local Development
```bash
streamlit run streamlit_app.py
```

### Production Options

1. **Streamlit Cloud** - Free hosting for public apps
2. **Docker** - Containerized deployment
3. **Heroku** - Platform as a Service
4. **AWS/Azure** - Cloud infrastructure

### Docker Example
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py"]
```

## 📚 Documentation

- **STREAMLIT_README.md** - Detailed Streamlit UI guide
- **MONGODB_SETUP.md** - MongoDB Atlas configuration
- **CHANGES_SUMMARY.md** - Recent changes and migrations
- **env.template** - Environment configuration template

## 🤝 Contributing

1. Test your changes with both interfaces
2. Update documentation as needed
3. Follow existing code style
4. Add comments for complex logic

## ⚠️ Important Notice

This application is for **informational and educational purposes only**. It does not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare professionals for medical decisions.

## 📄 License

Internal use for PwC projects.

## 🎯 Roadmap

- [x] CLI application
- [x] MongoDB Atlas integration
- [x] Streamlit web interface
- [x] Report download functionality
- [ ] User authentication
- [ ] Multi-language support
- [ ] Advanced analytics dashboard
- [ ] Mobile responsive design
- [ ] Real-time chat with AI
- [ ] Integration with EHR systems

## 📞 Support

For issues or questions:
1. Check relevant documentation files
2. Review error messages carefully
3. Test with sample patient data
4. Verify all dependencies are installed

---

**Built with ❤️ using Python, Streamlit, and Azure AI**

*Last Updated: 2025-01-11*

