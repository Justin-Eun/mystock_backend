import pymysql
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect as root (Global Admin)
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "", 
    "port": 3306,
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor
}

def restrict_admin():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        try:
            with connection.cursor() as cursor:
                # 1. Revoke ALL privileges to start fresh
                logger.info("Revoking all privileges from 'admin'...")
                try:
                    cursor.execute("REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'admin'@'localhost';")
                except pymysql.err.OperationalError as e:
                    logger.warning(f"Could not revoke all (maybe user new?): {e}")

                # 2. Grant privileges ONLY on mystock
                logger.info("Granting privileges ONLY on 'mystock'...")
                cursor.execute("GRANT ALL PRIVILEGES ON mystock.* TO 'admin'@'localhost';")
                
                # 3. Flush
                cursor.execute("FLUSH PRIVILEGES;")
                
                # 4. Verification Check: What DBs exist?
                logger.info("Checking connection as root: showing all DBs...")
                cursor.execute("SHOW DATABASES;")
                dbs = cursor.fetchall()
                for db in dbs:
                    print(f" - {db['Database']}")
                    
                logger.info("Successfully restricted 'admin' to 'mystock'.")
                
        finally:
            connection.close()
    except Exception as e:
        logger.error(f"Error restricting user: {e}")

if __name__ == "__main__":
    restrict_admin()
