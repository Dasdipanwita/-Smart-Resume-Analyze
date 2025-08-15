#!/usr/bin/env python3
"""
Database Connection Test Script
This script helps diagnose and fix database connection issues.
"""

import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mysql_connection():
    """Test MySQL connection with different scenarios"""
    
    print("🔍 Testing MySQL Database Connection...")
    print("=" * 50)
    
    # Get credentials from .env file
    host = os.environ.get('DB_HOST', 'localhost')
    user = os.environ.get('DB_USER', 'root')
    password = os.environ.get('DB_PASS', '')
    
    print(f"Host: {host}")
    print(f"User: {user}")
    print(f"Password: {'*' * len(password) if password else '(empty)'}")
    print()
    
    # Test 1: Connection without specific database
    print("📋 Test 1: Basic MySQL Connection (without database)")
    try:
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ SUCCESS: Basic MySQL connection works!")
        
        # Test creating database
        print("\n📋 Test 2: Creating 'sra' database")
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS sra")
            cursor.execute("SHOW DATABASES LIKE 'sra'")
            result = cursor.fetchone()
            if result:
                print("✅ SUCCESS: Database 'sra' exists or was created!")
            else:
                print("❌ FAILED: Could not create database 'sra'")
        
        connection.close()
        
        # Test 2: Connection with specific database
        print("\n📋 Test 3: Connection to 'sra' database")
        connection = pymysql.connect(
            host=host,
            user=user,
            password=password,
            db='sra',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print("✅ SUCCESS: Connection to 'sra' database works!")
        
        # Test creating table
        print("\n📋 Test 4: Creating user_data table")
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    ID INT NOT NULL AUTO_INCREMENT,
                    Name VARCHAR(100) NOT NULL,
                    Email_ID VARCHAR(50) NOT NULL,
                    resume_score VARCHAR(8) NOT NULL,
                    Timestamp VARCHAR(50) NOT NULL,
                    Page_no VARCHAR(5) NOT NULL,
                    Predicted_Field VARCHAR(25) NOT NULL,
                    User_level VARCHAR(30) NOT NULL,
                    Actual_skills VARCHAR(300) NOT NULL,
                    Recommended_skills VARCHAR(300) NOT NULL,
                    Recommended_courses VARCHAR(800) NOT NULL,
                    PRIMARY KEY (ID)
                )
            """)
            cursor.execute("SHOW TABLES LIKE 'user_data'")
            result = cursor.fetchone()
            if result:
                print("✅ SUCCESS: Table 'user_data' exists or was created!")
            else:
                print("❌ FAILED: Could not create table 'user_data'")
        
        connection.close()
        print("\n🎉 ALL TESTS PASSED! Your database is ready to use.")
        return True
        
    except pymysql.err.OperationalError as e:
        error_code = e.args[0]
        error_msg = e.args[1]
        
        print(f"❌ FAILED: {error_msg}")
        print("\n🔧 TROUBLESHOOTING SUGGESTIONS:")
        
        if error_code == 1045:  # Access denied
            print("   • Check if your password is correct")
            print("   • Try connecting with an empty password")
            print("   • Make sure MySQL user 'root' exists and has proper permissions")
            
        elif error_code == 2003:  # Can't connect to server
            print("   • Make sure MySQL server is running")
            print("   • Check if MySQL is installed")
            print("   • Try starting MySQL service")
            
        elif error_code == 1049:  # Unknown database
            print("   • Database 'sra' doesn't exist (this is normal for first run)")
            print("   • The app will create it automatically")
            
        print(f"\n💡 QUICK FIXES:")
        print(f"   1. Try empty password: Update .env file with DB_PASS=")
        print(f"   2. Start MySQL service: net start mysql (run as administrator)")
        print(f"   3. Use XAMPP/WAMP if you have it installed")
        
        return False
        
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

def suggest_alternatives():
    """Suggest alternative solutions"""
    print("\n" + "=" * 50)
    print("🔄 ALTERNATIVE SOLUTIONS:")
    print("=" * 50)
    
    print("1. 📁 Run without database (data won't be saved)")
    print("   - The app will work but won't save user data")
    print("   - Good for testing and demonstration")
    
    print("\n2. 🔧 Install/Start MySQL:")
    print("   - Download MySQL from: https://dev.mysql.com/downloads/mysql/")
    print("   - Or use XAMPP: https://www.apachefriends.org/")
    print("   - Or use WAMP: https://www.wampserver.com/")
    
    print("\n3. 🐳 Use Docker MySQL:")
    print("   - docker run --name mysql-sra -e MYSQL_ROOT_PASSWORD=1234 -p 3306:3306 -d mysql:8.0")
    
    print("\n4. ☁️ Use SQLite instead (file-based database)")
    print("   - No server required, works out of the box")

if __name__ == "__main__":
    print("🚀 Smart Resume Analyser - Database Connection Test")
    print("=" * 60)
    
    success = test_mysql_connection()
    
    if not success:
        suggest_alternatives()
    
    print("\n" + "=" * 60)
    print("Press Enter to continue...")
    input()