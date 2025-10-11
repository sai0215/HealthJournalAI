# MongoDB Atlas Setup Guide

This application now uses MongoDB Atlas (cloud) instead of local MongoDB.

## Setup Instructions

### Option 1: Using .env File (Easiest & Recommended)

1. **Get your MongoDB Atlas connection string:**
   - Go to [MongoDB Atlas](https://cloud.mongodb.com/)
   - Sign in or create a free account
   - Create a cluster (free tier available)
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Copy the connection string

2. **Create a .env file:**
   ```bash
   cp env.template .env
   ```

3. **Edit the .env file:**
   Open `.env` in a text editor and replace the placeholder values:
   ```
   MONGODB_URI=mongodb+srv://youruser:yourpassword@cluster0.abc123.mongodb.net/health_journal?retryWrites=true&w=majority
   ```

4. **Replace placeholders:**
   - `<username>`: Your MongoDB Atlas username
   - `<password>`: Your MongoDB Atlas password
   - `<cluster>`: Your cluster address (e.g., cluster0.abc123)
   - `<database>`: Your database name (e.g., health_journal)

### Option 2: Using Environment Variable

**On macOS/Linux:**
```bash
export MONGODB_URI="mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority"
```

**On Windows:**
```cmd
set MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority
```

### Option 3: Hardcode in Configuration File

1. Open `std_hub/db/mongodb.py`
2. Find line 19 and uncomment it
3. Replace the placeholder values with your actual MongoDB Atlas connection string:

```python
mongo_uri = "mongodb+srv://myuser:mypassword@cluster0.abc123.mongodb.net/health_journal?retryWrites=true&w=majority"
```

## Example Connection String

```
mongodb+srv://healthuser:MySecurePassword123@cluster0.mongodb.net/health_journal?retryWrites=true&w=majority
```

## Testing the Connection

Run the application to test the connection:

```bash
source venv_mac/bin/activate
python app.py
```

You should see: `MongoDB Atlas is connected and running successfully.`

## Running Without MongoDB

If you don't want to use MongoDB, the application will continue to work without database logging. You'll see a warning message but the application will function normally.

## Security Notes

- Never commit your connection string to version control
- Use strong passwords
- Whitelist your IP address in MongoDB Atlas Network Access settings
- Consider using MongoDB Atlas API Keys for production

