import mysql.connector
from mysql.connector import Error
import sys
import socket
import threading

print("PYTHON EXECUTABLE:", sys.executable)


# Database connection function with forced timeout
def get_connection():
    print("\n🔍 Attempting to connect to MySQL database...")
    print(f"   Host: localhost")
    print(f"   User: root")
    print(f"   Database: mit_hostel_solutions")
    
    # First, check if we can reach the MySQL port
    try:
        print("   Checking if MySQL port 3306 is accessible...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('localhost', 3306))
        sock.close()
        if result != 0:
            print("   ⚠️  Port 3306 is not accessible. MySQL server might not be running.")
            print("   💡 Try: net start MySQL (in PowerShell as Administrator)")
            return None
        else:
            print("   ✅ Port 3306 is accessible")
    except Exception as e:
        print(f"   ⚠️  Could not check port: {e}")
    
    # Use threading to enforce timeout since connection_timeout might not work
    connection_result = [None]
    connection_error = [None]
    
    def attempt_connection():
        try:
            print("   Connecting to database (timeout: 5 seconds)...")
            # Try with 127.0.0.1 instead of localhost (avoids IPv6 issues)
            # use_pure=True forces pure Python implementation (more reliable on Windows)
            conn = mysql.connector.connect(
                host="127.0.0.1",  # Use IP instead of localhost
                user="root",
                password="Eternal_Flame",
                database="mit_hostel_solutions",
                port=3306,
                autocommit=True,
                use_pure=True,  # Force pure Python implementation
                connect_timeout=5,  # Additional timeout parameter
                allow_local_infile=True
            )
            connection_result[0] = conn
        except Error as e:
            connection_error[0] = e
        except Exception as e:
            connection_error[0] = e
    
    # Start connection in a separate thread
    thread = threading.Thread(target=attempt_connection, daemon=True)
    thread.start()
    thread.join(timeout=5)  # Wait maximum 5 seconds
    
    if thread.is_alive():
        print("   ⏱️  Connection attempt timed out after 5 seconds!")
        print("   💡 MySQL server might not be responding or is not running")
        print("   💡 Try: net start MySQL (in PowerShell as Administrator)")
        return None
    
    if connection_error[0]:
        error = connection_error[0]
        print(f"   ❌ MySQL Error: {error}")
        if hasattr(error, 'errno'):
            print(f"   Error Code: {error.errno}")
            if error.errno == 2003:
                print("   💡 This means MySQL server is not running or not accessible")
            elif error.errno == 1045:
                print("   💡 This means username/password is incorrect")
            elif error.errno == 1049:
                print("   💡 This means the database 'mit_hostel_solutions' does not exist")
        return None
    
    if connection_result[0]:
        connection = connection_result[0]
        try:
            if connection.is_connected():
                db_info = connection.get_server_info()
                print(f"   ✅ Database connected successfully!")
                print(f"   MySQL Server version: {db_info}")
                return connection
            else:
                print("   ❌ Connection object created but not connected")
                return None
        except Exception as e:
            print(f"   ❌ Error checking connection: {e}")
            return None
    
    print("   ❌ Connection failed for unknown reason")
    return None


# Test the connection
if __name__ == "__main__":
    print("\n" + "="*50)
    print("Testing MySQL Connection")
    print("="*50)
    
    conn = get_connection()
    
    if conn:
        print("\n✅ Connection successful! You can use this connection object.")
        conn.close()
        print("Connection closed.")
    else:
        print("\n❌ Connection failed. Please check:")
        print("   1. Is MySQL server running? (net start MySQL)")
        print("   2. Does the database 'mit_hostel_solutions' exist?")
        print("   3. Are the username and password correct?")
        print("   4. Is MySQL installed and configured properly?")