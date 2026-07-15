from src.scenarios.base_scenario import GenericScenario

class ScenarioS1(GenericScenario):
    scenario_id = "S1"
    description = "Normal Day — Slow natural drift within normal bounds. Everything stays GREEN."

class ScenarioS2(GenericScenario):
    scenario_id = "S2"
    description = "Slow-Building Risk — Environmental parameters drift towards dangerous levels."

class ScenarioS3(GenericScenario):
    scenario_id = "S3"
    description = "Sudden Ignition — Starts normal, then a sudden fire breaks out."
