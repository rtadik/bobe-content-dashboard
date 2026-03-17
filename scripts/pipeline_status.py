"""Pipeline run status tracker.

Writes real-time JSON status updates during pipeline execution.
The admin/pipeline-status.html page reads this JSON to render
a visual node graph with per-topic drill-down and run history.
"""

import json
import os
import tempfile
import threading
from datetime import datetime


STATUS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "outputs",
    "pipeline-status.json",
)

MAX_RUNS = 20

# Standard phase names for full pipeline runs
FULL_PHASES = [
    "Scrape Topics",
    "Assemble Buckets",
    "Generate Content",
    "Write to Airtable",
    "Generate Images",
    "Upload to R2",
    "Update Airtable Images",
    "Finalize",
    "Deploy",
]

ANNOUNCEMENT_PHASES = [
    "Generate Content",
    "Write to Airtable",
    "Generate Images",
    "Upload to R2",
    "Translation",
    "Deploy",
]


class PipelineStatus:
    """Tracks pipeline run status and writes to JSON file."""

    def __init__(self, client_id, week_of, mode="full", status_file=None, phases=None):
        self._lock = threading.Lock()
        self._status_file = status_file or STATUS_FILE

        # Ensure output directory exists
        os.makedirs(os.path.dirname(self._status_file), exist_ok=True)

        # Determine phases for this run
        if phases:
            phase_names = phases
        elif mode == "announcement":
            phase_names = ANNOUNCEMENT_PHASES
        elif mode == "regen":
            phase_names = []  # Regen adds phases dynamically
        else:
            phase_names = FULL_PHASES

        now = datetime.now().isoformat(timespec="seconds")
        run_id = f"{now.replace(':', '-')}_{client_id}_{mode}"

        self._run = {
            "run_id": run_id,
            "client_id": client_id,
            "week_of": week_of,
            "mode": mode,
            "status": "running",
            "started_at": now,
            "finished_at": None,
            "error": None,
            "phases": [
                {
                    "name": name,
                    "status": "pending",
                    "started_at": None,
                    "finished_at": None,
                    "item_count": None,
                    "error": None,
                    "topics": [],
                }
                for name in phase_names
            ],
        }

        # Load existing runs, append this one, prune
        self._runs = self._load_runs()
        self._runs.append(self._run)
        self._prune_runs()
        self._write()

    def _get_phase(self, phase_name):
        """Find a phase by name, creating it if it doesn't exist (for regen mode)."""
        for phase in self._run["phases"]:
            if phase["name"] == phase_name:
                return phase
        # Auto-create for regen mode
        phase = {
            "name": phase_name,
            "status": "pending",
            "started_at": None,
            "finished_at": None,
            "item_count": None,
            "error": None,
            "topics": [],
        }
        self._run["phases"].append(phase)
        return phase

    def start_phase(self, phase_name):
        """Mark a phase as running."""
        with self._lock:
            phase = self._get_phase(phase_name)
            phase["status"] = "running"
            phase["started_at"] = datetime.now().isoformat(timespec="seconds")
            self._write()

    def complete_phase(self, phase_name, item_count=None):
        """Mark a phase as successfully completed."""
        with self._lock:
            phase = self._get_phase(phase_name)
            phase["status"] = "success"
            phase["finished_at"] = datetime.now().isoformat(timespec="seconds")
            if item_count is not None:
                phase["item_count"] = item_count
            self._write()

    def fail_phase(self, phase_name, error_message):
        """Mark a phase as failed."""
        with self._lock:
            phase = self._get_phase(phase_name)
            phase["status"] = "failed"
            phase["finished_at"] = datetime.now().isoformat(timespec="seconds")
            phase["error"] = str(error_message)
            self._write()

    def skip_phase(self, phase_name, reason=None):
        """Mark a phase as skipped."""
        with self._lock:
            phase = self._get_phase(phase_name)
            phase["status"] = "skipped"
            phase["finished_at"] = datetime.now().isoformat(timespec="seconds")
            if reason:
                phase["error"] = reason
            self._write()

    def update_topic(self, phase_name, topic_index, topic_name, status, error=None, bucket=None):
        """Update per-topic status within a phase."""
        with self._lock:
            phase = self._get_phase(phase_name)
            now = datetime.now().isoformat(timespec="seconds")

            # Find existing topic entry or create new one
            existing = None
            for t in phase["topics"]:
                if t["index"] == topic_index:
                    existing = t
                    break

            if existing:
                existing["status"] = status
                if error:
                    existing["error"] = str(error)
                if status in ("success", "failed"):
                    existing["finished_at"] = now
            else:
                entry = {
                    "index": topic_index,
                    "name": topic_name,
                    "bucket": bucket or "",
                    "status": status,
                    "error": str(error) if error else None,
                    "started_at": now,
                    "finished_at": now if status in ("success", "failed") else None,
                }
                phase["topics"].append(entry)

            self._write()

    def complete_run(self):
        """Mark the entire run as complete, deriving status from phases."""
        with self._lock:
            now = datetime.now().isoformat(timespec="seconds")
            self._run["finished_at"] = now

            statuses = [p["status"] for p in self._run["phases"]]
            if any(s == "failed" for s in statuses):
                if any(s == "success" for s in statuses):
                    self._run["status"] = "partial"
                else:
                    self._run["status"] = "failed"
            else:
                self._run["status"] = "success"

            self._write()

    def fail_run(self, error_message):
        """Mark the entire run as failed with a top-level error."""
        with self._lock:
            self._run["status"] = "failed"
            self._run["finished_at"] = datetime.now().isoformat(timespec="seconds")
            self._run["error"] = str(error_message)
            self._write()

    def _write(self):
        """Write current state to JSON file using atomic write."""
        data = {"runs": self._runs}
        try:
            dir_name = os.path.dirname(self._status_file)
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json.tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp_path, self._status_file)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception:
            # Status writing must never crash the pipeline
            pass

    def _load_runs(self):
        """Load existing runs from JSON file."""
        try:
            if os.path.exists(self._status_file):
                with open(self._status_file, "r") as f:
                    data = json.load(f)
                return data.get("runs", [])
        except (json.JSONDecodeError, IOError, KeyError):
            pass
        return []

    def _prune_runs(self):
        """Keep only the last MAX_RUNS runs."""
        if len(self._runs) > MAX_RUNS:
            self._runs = self._runs[-MAX_RUNS:]
