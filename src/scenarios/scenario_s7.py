import threading
from src.scenarios.base_scenario import GenericScenario
from src.scenarios.results import ScenarioResult

class ScenarioS7(GenericScenario):
    scenario_id = "S7"
    description = "Concurrent Multi-Zone Escalation — Simulates independent fires in two parallel zones."

    def run(self) -> ScenarioResult:
        start_time = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        start_epoch = self.clock.time()
        
        zone_ids = self.yaml_data.get("target", {}).get("zone_ids", ["4A", "4B"])
        
        results = []
        threads = []
        
        def run_zone_scenario(zone_id):
            class SubScenario(GenericScenario):
                scenario_id = "S7-" + zone_id
                
            sub = SubScenario()
            sub.yaml_path = self.yaml_path
            if hasattr(self, "seed") and self.seed is not None:
                sub.seed = self.seed
            sub.setup(self.client, zone_id, self.clock)
            res = sub.run()
            sub.teardown()
            results.append(res)
            
        for zone in zone_ids:
            t = threading.Thread(target=run_zone_scenario, args=[zone])
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
            
        duration_sec = self.clock.time() - start_epoch
        end_time = self.clock.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        merged_logs = []
        merged_errors = []
        for r in results:
            merged_logs.extend(r.logs)
            merged_errors.extend(r.errors)
            
        return ScenarioResult(
            scenario=self.scenario_id,
            passed=all(r.passed for r in results) if results else False,
            duration_sec=duration_sec,
            start_time=start_time,
            end_time=end_time,
            metrics=[],
            events=[],
            logs=merged_logs,
            errors=merged_errors,
            zone_ids=zone_ids
        )
