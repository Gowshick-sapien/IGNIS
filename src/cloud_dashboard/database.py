import os
import json
import logging
from datetime import datetime
# pyrefly: ignore [missing-import]
from influxdb_client import InfluxDBClient

logger = logging.getLogger("cloud_dashboard_db")

class CloudDashboardDB:
    """Handles read queries from InfluxDB and historical baseline lookups."""
    def __init__(self):
        self.url = os.environ.get("INFLUX_URL", "http://localhost:8086")
        self.token = os.environ.get("INFLUX_TOKEN", "ignis-super-secret-token")
        self.org = os.environ.get("INFLUX_ORG", "ignis-org")
        self.bucket = os.environ.get("INFLUX_BUCKET", "ignis-telemetry")
        
        self.client = None
        self.query_api = None
        self.baselines = {}
        self.load_historical_baselines()
        
    def connect(self):
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.query_api = self.client.query_api()

    def ping_influx(self) -> bool:
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception:
            return False

    def load_historical_baselines(self):
        """Loads baseline files for summer, winter, and monsoon."""
        base_paths = ["historical", "/app/historical", "../historical"]
        loaded = False
        for bp in base_paths:
            if os.path.exists(bp):
                try:
                    for season in ["summer", "winter", "monsoon"]:
                        file_path = os.path.join(bp, f"{season}.json")
                        if os.path.exists(file_path):
                            with open(file_path, "r") as f:
                                self.baselines[season] = json.load(f)
                    logger.info(f"Loaded seasonal baselines from directory: {bp}")
                    loaded = True
                    break
                except Exception as e:
                    logger.warning(f"Error loading baselines from {bp}: {e}")
        if not loaded:
            logger.warning("Historical seasonal baseline files not found. Using empty templates.")
            for s in ["summer", "winter", "monsoon"]:
                self.baselines[s] = {"season": s, "hourly": [{"hour": i, "temperature_c": 25.0, "humidity_pct": 50.0, "whi": 0.1} for i in range(24)]}

    def get_seasonal_baseline(self, season: str) -> dict:
        return self.baselines.get(season, self.baselines.get("summer"))

    # ==========================================
    # Flux Queries for Dashboard Snapshot
    # ==========================================
    def get_latest_zone_state(self, zone_id: str) -> dict:
        """Fetches the latest state for a specific zone."""
        if not self.query_api:
            return {"zone_id": zone_id, "state": "GREEN", "whi": 0.0, "is_state_clamped": False, "override_active": False, "timestamp": ""}
        
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1d)
          |> filter(fn: (r) => r["_measurement"] == "zone_state")
          |> filter(fn: (r) => r["zone_id"] == "{zone_id}")
          |> last()
        '''
        try:
            tables = self.query_api.query(query, org=self.org)
            record = {}
            for table in tables:
                for r in table.records:
                    record["zone_id"] = r.values.get("zone_id")
                    record["timestamp"] = r.get_time().strftime("%Y-%m-%dT%H:%M:%SZ")
                    record[r.get_field()] = r.get_value()
            if record:
                return record
        except Exception as e:
            logger.error(f"Error querying zone state: {e}")
        return {"zone_id": zone_id, "state": "GREEN", "whi": 0.0, "is_state_clamped": False, "override_active": False, "timestamp": ""}

    def get_latest_edge_telemetry(self, zone_id: str) -> list:
        """Fetches the latest readings of all edge nodes in a zone."""
        if not self.query_api:
            return []
            
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1d)
          |> filter(fn: (r) => r["_measurement"] == "telemetry")
          |> filter(fn: (r) => r["zone_id"] == "{zone_id}")
          |> toFloat()
          |> last()
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        try:
            tables = self.query_api.query(query, org=self.org)
            readings = []
            for table in tables:
                for r in table.records:
                    readings.append(r.values)
            return readings
        except Exception as e:
            logger.error(f"Error querying edge telemetry: {e}")
        return []

    def get_system_health(self, zone_id: str) -> dict:
        """Checks status of Ingestor, Broker, and Fog Node based on Influx logs."""
        health = {
            "Cloud_Broker": "ONLINE",  # Assumed ONLINE if dashboard is querying, but will check connection
            "InfluxDB": "ONLINE" if self.ping_influx() else "OFFLINE",
            "Fog_Node": "OFFLINE",
            "Cloud_Ingestor": "OFFLINE"
        }
        
        if not self.query_api:
            return health
            
        # Query health measurements written within the last 2 minutes (to tolerate container clock drift)
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -2m)
          |> filter(fn: (r) => r["_measurement"] == "system_health")
          |> filter(fn: (r) => r["_field"] == "status")
          |> group(columns: ["component"])
          |> last()
        '''
        try:
            tables = self.query_api.query(query, org=self.org)
            for table in tables:
                for r in table.records:
                    comp = r.values.get("component")
                    status = r.get_value()
                    if comp == f"fog_node_{zone_id}":
                        health["Fog_Node"] = status
                    elif comp == "cloud_ingestor":
                        health["Cloud_Ingestor"] = status
        except Exception as e:
            logger.error(f"Error querying health states: {e}")
            
        return health

    def get_recent_alerts_and_logs(self, zone_id: str, limit: int = 15) -> dict:
        """Queries recent alerts and action logs from the database."""
        result = {"alerts": [], "action_logs": [], "audit_logs": []}
        if not self.query_api:
            return result
            
        # 1. Query Alerts
        alert_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1d)
          |> filter(fn: (r) => r["_measurement"] == "alerts")
          |> filter(fn: (r) => r["zone_id"] == "{zone_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        # 2. Query Action Logs
        action_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1d)
          |> filter(fn: (r) => r["_measurement"] == "action_logs")
          |> filter(fn: (r) => r["zone_id"] == "{zone_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        # 3. Query Audit Logs
        audit_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1d)
          |> filter(fn: (r) => r["_measurement"] == "audit_logs")
          |> filter(fn: (r) => r["zone_id"] == "{zone_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {limit})
        '''
        try:
            tables = self.query_api.query(alert_query, org=self.org)
            for table in tables:
                for r in table.records:
                    result["alerts"].append({
                        "timestamp": r.get_time().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "severity": r.values.get("severity", "GREEN"),
                        "whi": r.values.get("whi", 0.0),
                        "source_node": r.values.get("source_node", "UNKNOWN")
                    })
                    
            tables = self.query_api.query(action_query, org=self.org)
            for table in tables:
                for r in table.records:
                    # Parse actions list from JSON string
                    try:
                        actions_list = json.loads(r.values.get("actions", "[]"))
                    except Exception:
                        actions_list = []
                    result["action_logs"].append({
                        "timestamp": r.get_time().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "actions": actions_list,
                        "reason": r.values.get("reason", "")
                    })
                    
            tables = self.query_api.query(audit_query, org=self.org)
            for table in tables:
                for r in table.records:
                    result["audit_logs"].append({
                        "timestamp": r.get_time().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "command_id": r.values.get("command_id", "UNKNOWN"),
                        "command": r.values.get("command", ""),
                        "issued_by": r.values.get("issued_by", ""),
                        "status": r.values.get("status", "SUCCESS"),
                        "error_reason": r.values.get("error_reason", ""),
                        "details": r.values.get("details", "")
                    })
        except Exception as e:
            logger.error(f"Error querying logs: {e}")
            
        return result

    def get_latest_performance_metrics(self, zone_id: str) -> dict:
        """Queries the latest cloud delay calculations."""
        metrics = {
            "fog_to_cloud_latency": 0.0,
            "cloud_ingestion_latency": 0.0,
            "influx_write_latency": 0.0,
            "cloud_end_to_end_latency": 0.0,
            "telemetry_rate_pps": 0.0,
            "messages_archived": 0
        }
        if not self.query_api:
            return metrics
            
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -5m)
          |> filter(fn: (r) => r["_measurement"] == "performance_metrics")
          |> last()
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        count_query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r["_measurement"] == "telemetry")
          |> filter(fn: (r) => r["_field"] == "sequence")
          |> count()
        '''
        try:
            # Latency Query
            tables = self.query_api.query(query, org=self.org)
            for table in tables:
                for r in table.records:
                    metrics["fog_to_cloud_latency"] = r.values.get("fog_to_cloud_latency", 0.0)
                    metrics["cloud_ingestion_latency"] = r.values.get("cloud_ingestion_latency", 0.0)
                    metrics["influx_write_latency"] = r.values.get("influx_write_latency", 0.0)
                    metrics["cloud_end_to_end_latency"] = r.values.get("cloud_end_to_end_latency", 0.0)
            
            # Archive Count Query
            tables = self.query_api.query(count_query, org=self.org)
            messages_archived = 0
            for table in tables:
                for r in table.records:
                    messages_archived += r.get_value()
            metrics["messages_archived"] = messages_archived
                    
            # Calculate Telemetry Packets per second (based on count in last 2 minutes)
            rate_query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: -2m)
              |> filter(fn: (r) => r["_measurement"] == "telemetry")
              |> filter(fn: (r) => r["_field"] == "sequence")
              |> count()
            '''
            tables = self.query_api.query(rate_query, org=self.org)
            total_messages_2m = 0
            for table in tables:
                for r in table.records:
                    total_messages_2m += r.get_value()
            metrics["telemetry_rate_pps"] = round(total_messages_2m / 120.0, 2)
        except Exception as e:
            logger.error(f"Error querying performance metrics: {e}")
            
        return metrics

    def get_historical_chart_data(self, zone_id: str, minutes: int = 15) -> dict:
        """Fetches historical time-series telemetry data for the dashboard charts."""
        chart_data = {"labels": [], "E11": [], "E12": [], "E13": []}
        if not self.query_api:
            return chart_data
            
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -{minutes}m)
          |> filter(fn: (r) => r["_measurement"] == "telemetry")
          |> filter(fn: (r) => r["zone_id"] == "{zone_id}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> keep(columns: ["_time", "node_id", "temperature_c", "humidity_pct", "gas_ppm"])
          |> sort(columns: ["_time"])
        '''
        try:
            tables = self.query_api.query(query, org=self.org)
            
            # Temp storage to align timelines
            time_map = {} # timestamp -> {node_id -> telemetry_dict}
            
            for table in tables:
                for r in table.records:
                    ts = r.get_time().strftime("%H:%M:%S")
                    node_id = r.values.get("node_id")
                    if ts not in time_map:
                        time_map[ts] = {}
                    time_map[ts][node_id] = {
                        "temperature_c": r.values.get("temperature_c", 0.0),
                        "humidity_pct": r.values.get("humidity_pct", 0.0),
                        "gas_ppm": r.values.get("gas_ppm", 0.0)
                    }
                    
            # Sort timestamps
            sorted_times = sorted(time_map.keys())
            chart_data["labels"] = sorted_times
            
            # Map values
            for ts in sorted_times:
                nodes_data = time_map[ts]
                for node in ["E11", "E12", "E13"]:
                    if node in nodes_data:
                        chart_data[node].append(nodes_data[node])
                    else:
                        # Append None or last known to prevent chart breaking
                        chart_data[node].append({"temperature_c": None, "humidity_pct": None, "gas_ppm": None})
        except Exception as e:
            logger.error(f"Error querying historical chart data: {e}")
            
        return chart_data

    def close(self):
        if self.client:
            self.client.close()
