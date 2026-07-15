import os
import time
import logging
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import InfluxDBWrapper
from mqtt_service import CloudMQTTService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("cloud_ingestor_main")

def main():
    logger.info("Initializing IGNIS Central Cloud Ingestor Service...")
    
    # 1. Initialize InfluxDB connection with retry backoff
    db = InfluxDBWrapper()
    connected = False
    retry_delay = 2
    
    while not connected:
        try:
            db.connect()
            # Verify write capacity by pinging
            if db.ping():
                connected = True
                logger.info("Successfully connected to InfluxDB.")
            else:
                raise ConnectionError("InfluxDB ping failed.")
        except Exception as e:
            logger.warning(f"Could not connect to InfluxDB: {e}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30) # Exponential backoff max 30s
            
    # 2. Initialize and Start MQTT Service
    service = CloudMQTTService(db)
    service.start()
    
    # 3. Main Loop: Periodically report ingestor system health and flush database buffer if offline
    try:
        while True:
            # Periodic health heartbeat write
            timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            # Log ingestor's own health state
            try:
                if db.ping():
                    service.db_online = True
                    db.write_record(
                        measurement="system_health",
                        tags={"component": "cloud_ingestor"},
                        fields={"status": "ONLINE", "details": "Ingestor main loop running normally."},
                        timestamp=timestamp
                    )
                    # Periodically try flushing the buffer
                    service.flush_buffer()
                else:
                    service.db_online = False
                    service.last_db_check_time = time.time()
            except Exception as ex:
                service.db_online = False
                service.last_db_check_time = time.time()
                logger.warning(f"Could not log ingestor health to DB: {ex}")
                
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Service interrupted by user. Shutting down...")
    finally:
        service.stop()
        db.close()
        logger.info("Cloud Ingestor shut down cleanly.")

if __name__ == "__main__":
    main()
