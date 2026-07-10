import os
import logging
from datetime import datetime
# pyrefly: ignore [missing-import]
from influxdb_client import InfluxDBClient, Point, WritePrecision
# pyrefly: ignore [missing-import]
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger("cloud_ingestor_db")

class InfluxDBWrapper:
    """Manages connection and writes to the central InfluxDB Time-Series database."""
    def __init__(self):
        self.url = os.environ.get("INFLUX_URL", "http://localhost:8086")
        self.token = os.environ.get("INFLUX_TOKEN", "ignis-super-secret-token")
        self.org = os.environ.get("INFLUX_ORG", "ignis-org")
        self.bucket = os.environ.get("INFLUX_BUCKET", "ignis-telemetry")
        
        self.client = None
        self.write_api = None
        
    def connect(self):
        """Establishes connection to InfluxDB client."""
        logger.info(f"Connecting to InfluxDB at {self.url} (Org: {self.org}, Bucket: {self.bucket})")
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        
    def ping(self) -> bool:
        """Pings InfluxDB to check health."""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False

    def write_record(self, measurement: str, tags: dict, fields: dict, timestamp: str = None):
        """Writes a single measurement point to InfluxDB."""
        if not self.write_api:
            raise RuntimeError("Database connection not initialized. Call connect() first.")
            
        point = Point(measurement)
        
        # Add tags
        for k, v in tags.items():
            if v is not None:
                point = point.tag(k, str(v))
                
        # Add fields
        for k, v in fields.items():
            if v is not None:
                point = point.field(k, v)
                
        # Handle custom timestamps (expecting ISO strings or float epoch seconds)
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    # Replace Z with UTC timezone format if present
                    ts_val = datetime.strptime(timestamp.replace("Z", "+00:00"), "%Y-%m-%dT%H:%M:%S%z")
                else:
                    ts_val = datetime.utcfromtimestamp(float(timestamp))
                point = point.time(ts_val, WritePrecision.NS)
            except Exception as e:
                logger.warning(f"Failed to parse timestamp '{timestamp}', using server time. Error: {e}")
                
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)

    def close(self):
        if self.client:
            self.client.close()
            logger.info("InfluxDB connection closed.")
