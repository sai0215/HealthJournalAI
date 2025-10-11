# 🚀 Quick Start Guide - Health Assistant

Get up and running in 60 seconds!

## ⚡ Fastest Way to Start

### macOS/Linux (One Command)
```bash
cd "/Users/saivignesh/Downloads/Health Journal" && ./run_streamlit.sh
```

### Windows (One Command)
```cmd
cd "Health Journal" && run_streamlit.bat
```

The app will automatically open in your browser! 🎉

## 📱 What You'll See

### Screen 1: Welcome Page
```
🏥 Welcome to Health Assistant
Your AI-Powered Healthcare Companion

┌─────────────────────────────────┐
│ 📋 Enter Your Patient ID        │
│                                  │
│ ┌─────────────────────────────┐ │
│ │ P001                        │ │
│ └─────────────────────────────┘ │
│                                  │
│   [    Continue ➡️    ]         │
└─────────────────────────────────┘

Sample IDs: P001, P002, P003, P004, P005
```

### Screen 2: Patient Information
```
📋 Patient Information Review

Patient ID: P001

👤 Basic Information
Name: John Doe    Age: 45    Gender: Male

🏥 Medical History
Drug Allergies: None
Past Medical History: Hypertension

🆕 Additional Health Information
[Any new allergies or conditions?]

[    Continue to Symptoms ➡️    ]
```

### Screen 3: Symptom Assessment
```
🩺 Symptom Assessment

📝 Describe your symptoms:
┌──────────────────────────────────────────┐
│ Persistent fever for 3 days,             │
│ mild headache in the morning...          │
└──────────────────────────────────────────┘

✅ Quick Symptom Selector
☑️ Fever    ☑️ Cough      ☐ Chest Pain
☑️ Fatigue  ☐ Headache   ☐ Body Pain

[    Generate Report ➡️    ]
```

### Screen 4: Assessment Summary
```
📊 Health Assessment Summary

✅ Assessment Complete!
Your health information has been successfully processed.

🔬 Recommended Diagnostic Tests
1. 🔬 CBC (Complete Blood Count) for fever pattern
2. 😴 Thyroid function and iron panel tests

📥 [Download JSON Report] [Download Text Report]
```

## 🎯 5-Step Workflow

1. **Enter Patient ID** → System loads your records
2. **Review Info** → Verify medical history
3. **Report Symptoms** → Describe what you're feeling
4. **Get Tests** → Receive smart recommendations
5. **Download Report** → Save your assessment

## 💡 Pro Tips

### First Time Users
- Use sample Patient ID: **P001**
- Try the quick symptom checkboxes
- Download the report to see the format

### Power Users
- Combine text description + checkboxes for best results
- Be specific about symptom duration and severity
- Use the Reset button to test different scenarios

### Developers
- App has hot reload - just save and refresh
- Session state persists during development
- Check sidebar for current stage

## 🔧 Troubleshooting (30 seconds)

### "Command not found"?
```bash
# Install dependencies first
pip install -r requirements.txt
```

### "Port 8501 already in use"?
```bash
# Use a different port
streamlit run streamlit_app.py --server.port 8502
```

### "Excel file not found"?
```bash
# Make sure you're in the right directory
cd "/Users/saivignesh/Downloads/Health Journal"
```

### App not loading?
1. Check terminal for errors
2. Try force refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
3. Click "Reset Session" in sidebar

## 🎨 UI Features

### Progress Sidebar
```
🏥 Health Assistant
─────────────────
Progress
➤ 1️⃣ Patient ID
　2️⃣ Health Info
　3️⃣ Symptoms
　4️⃣ Summary
─────────────────
📊 Total Patients: 100
```

### Color Codes
- 🟢 **Green Box** = Success message
- 🔵 **Blue Box** = Information
- 🟡 **Yellow Box** = Warning
- 🔴 **Red Text** = Error

## ⌨️ Keyboard Shortcuts

While in Streamlit:
- `R` → Rerun app
- `C` → Clear cache
- `?` → Show all shortcuts
- `Ctrl+C` (in terminal) → Stop app

## 📊 Test Data Available

Sample patients in the system:
- **P001** - Basic patient
- **P002** - Patient with allergies
- **P003** - Patient with history
- **P004** - Complex case
- **P005** - Recent conditions

## 🔗 URLs You'll Use

### Local Development
- **Main App**: http://localhost:8501
- **Alternative Port**: http://localhost:8502

### File Locations
- **Project**: `/Users/saivignesh/Downloads/Health Journal`
- **App File**: `streamlit_app.py`
- **Config**: `env.template` → `.env`

## 📖 Next Steps

### After First Run
1. ✅ Explore all 4 screens
2. ✅ Download a sample report
3. ✅ Try different symptoms
4. ✅ Check the sidebar features

### Configure MongoDB (Optional)
1. Read `MONGODB_SETUP.md`
2. Get MongoDB Atlas (free)
3. Create `.env` file
4. Test with `python test_mongodb_connection.py`

### Customize the App
1. Open `streamlit_app.py`
2. Change colors, text, layout
3. Save and watch it reload
4. Read `STREAMLIT_README.md` for details

## 🎓 Learning Path

**Beginner** (5 minutes)
→ Run the app
→ Try one patient assessment
→ Download a report

**Intermediate** (15 minutes)
→ Test all sample patients
→ Try different symptom combinations
→ Read the main README.md

**Advanced** (30 minutes)
→ Configure MongoDB Atlas
→ Modify the UI (streamlit_app.py)
→ Integrate with your data

## ✨ One-Liner Commands

### Start App
```bash
./run_streamlit.sh
```

### Start on Different Port
```bash
streamlit run streamlit_app.py --server.port 8502
```

### Start Without Browser
```bash
streamlit run streamlit_app.py --server.headless=true
```

### Update Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Test MongoDB
```bash
python test_mongodb_connection.py
```

### View Logs
```bash
streamlit run streamlit_app.py --logger.level=debug
```

## 🎉 You're All Set!

The app is designed to be **intuitive** and **self-explanatory**.

Just run the command and follow the on-screen instructions.

**Stuck?** Check:
1. This guide (you're here!)
2. `README.md` (comprehensive docs)
3. `STREAMLIT_README.md` (UI details)
4. Terminal error messages

---

**Happy Assessing! 🏥**

Need help? All the documentation is in the project folder.

