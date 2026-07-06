import json
import os
from src.edge_node import EdgeNode
from src.fog_node import FogNode
from src.scenario import ScenarioGenerator
from src.presenter import ConsolePresenter

def load_config(config_path: str) -> dict:
    """Loads the zone configuration JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, 'r') as f:
        return json.load(f)

def run_scenario(scenario_name: str, description: str, raw_steps: list, edge: EdgeNode, fog: FogNode):
    """Executes a scenario sequence and presents the decision trace."""
    ConsolePresenter.print_scenario_header(scenario_name, description)
    
    # Process each step in the sequence
    for step in raw_steps:
        timestamp = step["timestamp"]
        sensor_data = step["sensor_data"]
        seasonal_baseline = step["seasonal_baseline"]
        
        # 1. Edge Node generates standardized telemetry
        telemetry = edge.format_reading(sensor_data, timestamp, seasonal_baseline)
        
        # 2. Fog Node ingests telemetry and executes decision scoring
        decision_record = fog.process_reading(telemetry)
        
        # 3. Presenter displays the results
        ConsolePresenter.print_decision_record(decision_record)

def main():
    # 1. Load configuration
    config_file = os.path.join("config", "zone_config.json")
    try:
        config = load_config(config_file)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return

    # 2. Instantiate Nodes
    # Simulation Zone 4B: Simlipal Forest Division
    zone_id = config.get("zone_id", "4B")
    gps_coordinates = [21.94, 86.32] # Simlipal Core GPS
    
    # Single Edge Node cluster "E12" and Single Fog Node
    edge_node = EdgeNode(node_id="E12", zone_id=zone_id, gps=gps_coordinates)
    fog_node = FogNode(zone_id=zone_id, config=config)

    # 3. Run Scenario S1: Normal Day
    normal_steps = ScenarioGenerator.get_normal_day_scenario()
    run_scenario(
        "S1 - Normal Day",
        "Validates normal baseline operation. Environment is stable and index remains low. Expected: GREEN.",
        normal_steps,
        edge_node,
        fog_node
    )

    # Reset fog node history/state to prevent spillover between scenario runs
    fog_node = FogNode(zone_id=zone_id, config=config)
    
    # 4. Run Scenario S2: Slow-Building Risk
    slow_steps = ScenarioGenerator.get_slow_building_risk_scenario()
    run_scenario(
        "S2 - Slow-Building Risk",
        "Simulates a gradual multi-parameter environmental dry-out over hours. Expected: Transitions from GREEN to YELLOW.",
        slow_steps,
        edge_node,
        fog_node
    )

    fog_node = FogNode(zone_id=zone_id, config=config)

    # 5. Run Scenario S3: Sudden Ignition
    sudden_steps = ScenarioGenerator.get_sudden_ignition_scenario()
    run_scenario(
        "S3 - Sudden Ignition",
        "Simulates a sudden wildfire ignition with high temperatures, low humidity, CO gas release, and thermal anomaly. Expected: Escalates to RED.",
        sudden_steps,
        edge_node,
        fog_node
    )

    fog_node = FogNode(zone_id=zone_id, config=config)

    # 6. Run Scenario S4: Single Sensor Fault
    fault_steps = ScenarioGenerator.get_single_sensor_fault_scenario()
    run_scenario(
        "S4 - Single Sensor Fault",
        "Simulates a high gas spike on a single faulty sensor. WHI rises, but clamping rules restrict state to YELLOW due to lack of confirmation. Expected: Clamped to YELLOW.",
        fault_steps,
        edge_node,
        fog_node
    )

if __name__ == "__main__":
    main()
