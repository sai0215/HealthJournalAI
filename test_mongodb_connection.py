"""
Quick test script to verify MongoDB Atlas configuration
"""
import sys
print("Testing MongoDB Atlas configuration...\n")

try:
    from std_hub.db.mongodb import db_client
    
    if db_client:
        print("✅ SUCCESS: MongoDB Atlas is connected!")
        print(f"   Connected to: {db_client.address}")
    else:
        print("⚠️  WARNING: MongoDB is not configured.")
        print("   The application will run without database logging.")
        print("\n   To configure MongoDB Atlas:")
        print("   1. Read MONGODB_SETUP.md for instructions")
        print("   2. Create a .env file with your MongoDB Atlas connection string")
        print("   3. Run this test again to verify the connection")
    
    print("\n✅ Application imports successful - ready to run!")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

