class ConsolePresenter:
    """
    Handles formatting and presentation of IGNIS decision records to the console.
    Keeps the logging/printing decoupled from the core decision logic.
    """
    
    # ANSI escape sequences for premium terminal styling
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Colors matching risk states
    COLOR_GREEN = "\033[38;2;40;167;69m"   # Sleek green
    COLOR_YELLOW = "\033[38;2;255;193;7m"  # Sleek yellow
    COLOR_ORANGE = "\033[38;2;253;126;20m" # Sleek orange
    COLOR_RED = "\033[38;2;220;53;69m"     # Sleek red
    
    # Alert / Highlight backgrounds
    BG_ALERT_CLAMP = "\033[48;2;255;193;7m\033[38;2;0;0;0m" # Yellow bg, black text
    BG_ACTION = "\033[48;2;220;53;69m\033[38;2;255;255;255m" # Red bg, white text

    @classmethod
    def get_state_colored(cls, state: str) -> str:
        if state == "GREEN":
            return f"{cls.COLOR_GREEN}{cls.BOLD}GREEN{cls.RESET}"
        elif state == "YELLOW":
            return f"{cls.COLOR_YELLOW}{cls.BOLD}YELLOW{cls.RESET}"
        elif state == "ORANGE":
            return f"{cls.COLOR_ORANGE}{cls.BOLD}ORANGE{cls.RESET}"
        elif state == "RED":
            return f"{cls.COLOR_RED}{cls.BOLD}RED{cls.RESET}"
        return state

    @classmethod
    def print_scenario_header(cls, scenario_name: str, description: str):
        border = "=" * 80
        print(f"\n{cls.BOLD}{cls.COLOR_ORANGE}{border}{cls.RESET}")
        print(f" {cls.BOLD}SCENARIO: {scenario_name}{cls.RESET}")
        print(f" {cls.DIM}{description}{cls.RESET}")
        print(f"{cls.BOLD}{cls.COLOR_ORANGE}{border}{cls.RESET}\n")

    @classmethod
    def print_decision_record(cls, record: dict):
        state_colored = cls.get_state_colored(record["state"])
        timestamp = record["timestamp"]
        zone_id = record["zone_id"]
        whi = record["whi"]
        conf_count = record["confirmation_count"]
        confirming_sensors = record["confirming_sensors"]
        is_clamped = record["is_state_clamped"]
        actions = record["actions_logged"]
        raw = record["raw_reading"]
        
        print(f"[{timestamp}] Zone: {cls.BOLD}{zone_id}{cls.RESET} | State: {state_colored} (WHI: {cls.BOLD}{whi:.3f}{cls.RESET}, Confirmations: {cls.BOLD}{conf_count}{cls.RESET})")
        
        # Format sensor values
        sensor_details = (
            f"  {cls.DIM}Sensors:{cls.RESET} "
            f"Temp: {raw['temperature_c']:.1f}°C | "
            f"Humid: {raw['humidity_pct']:.1f}% | "
            f"Wind: {raw['wind_speed_kmh']:.1f} km/h | "
            f"Soil: {raw['soil_moisture_pct']:.1f}% | "
            f"Gas: {raw['gas_ppm']:.1f} ppm | "
            f"Thermal Anomaly: {raw['thermal_anomaly_c']:.1f}°C"
        )
        print(sensor_details)
        
        # If there are active confirming sensors, print them
        if confirming_sensors:
            crossed = ", ".join(confirming_sensors)
            print(f"  {cls.DIM}Thresholds crossed:{cls.RESET} {cls.COLOR_YELLOW}{crossed}{cls.RESET}")
            
        # Warning if clamped
        if is_clamped:
            print(f"  {cls.BG_ALERT_CLAMP} FALSE-POSITIVE GUARD TRIGGERED {cls.RESET} "
                  f"WHI suggests elevated state, but confirmation count ({conf_count}) < 3. Clamped to YELLOW.")
            
        # Log autonomous actions if any
        if actions:
            print(f"  {cls.BG_ACTION} AUTONOMOUS ACTIONS TRIGGERED {cls.RESET}")
            for action in actions:
                print(f"    - {cls.BOLD}COMMAND -> {action.upper()}{cls.RESET}")
                
        print("-" * 80)
