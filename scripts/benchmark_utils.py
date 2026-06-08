import time
import psutil
import os
import json
import threading
from datetime import datetime

class BenchmarkRunner:

    def __init__(self, name: str, results_dir: str):
        self.name = name
        self.results_dir = results_dir
        self.results = []
        os.makedirs(results_dir, exist_ok=True)

    def _monitor_resources(self, stop_event, measurements):
        process = psutil.Process()
        while not stop_event.is_set():
            try:
                mem = process.memory_info().rss / 1e9
                cpu = process.cpu_percent(interval=0.1)
                measurements.append({'mem_gb': mem, 'cpu_pct': cpu})
            except Exception:
                pass
            time.sleep(0.5)

    def run(self, query_name: str, func, *args, n_runs: int = 3, **kwargs):
        run_results = []

        for run_idx in range(n_runs):
            print(f"  [{run_idx+1}/{n_runs}] {query_name}...", end='', flush=True)

            stop_event = threading.Event()
            measurements = []
            monitor_thread = threading.Thread(
                target=self._monitor_resources,
                args=(stop_event, measurements)
            )

            mem_before = psutil.virtual_memory().used / 1e9
            t_start = time.perf_counter()
            monitor_thread.start()

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                stop_event.set()
                monitor_thread.join()
                print(f" BŁĄD: {e}")
                run_results.append({'error': str(e), 'run': run_idx})
                continue

            t_end = time.perf_counter()
            stop_event.set()
            monitor_thread.join()
            mem_after = psutil.virtual_memory().used / 1e9

            elapsed = t_end - t_start
            peak_mem = max((m['mem_gb'] for m in measurements), default=0)
            avg_cpu = sum(m['cpu_pct'] for m in measurements) / max(len(measurements), 1)

            run_result = {
                'system': self.name,
                'query': query_name,
                'run': run_idx,
                'elapsed_s': round(elapsed, 3),
                'peak_memory_gb': round(peak_mem, 2),
                'memory_delta_gb': round(mem_after - mem_before, 2),
                'avg_cpu_pct': round(avg_cpu, 1),
                'timestamp': datetime.now().isoformat()
            }
            run_results.append(run_result)
            self.results.append(run_result)

            print(f" {elapsed:.1f}s | {peak_mem:.1f} GB RAM")

        return run_results

    def save_results(self, filename=None):
        if filename is None:
            filename = f"{self.name}_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(self.results_dir, filename)
        with open(path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"Zapisano wyniki do: {path}")
        return path
