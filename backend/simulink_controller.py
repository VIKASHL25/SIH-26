import logging
import os
import subprocess
import threading
from typing import Optional

logger = logging.getLogger("SimulinkController")


class SimulinkController:
    """
    Controls the external MATLAB/Simulink mission replay process.

    Mission selection and simulation start are intentionally separate:
        select_mission(25) -> prepares Mission 25
        start()            -> starts Mission 25 replay
        stop()             -> stops the active replay
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        matlab_command: str = "matlab",
        stop_time: int = 1000,
    ):
        self.project_root = project_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

        self.simulink_dir = os.path.join(
            self.project_root,
            "simulink",
        )

        self.matlab_command = matlab_command
        self.stop_time = stop_time

        self.selected_mission: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None

        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def select_mission(self, mission_id: int) -> None:
        """Select a mission without starting Simulink."""

        if not isinstance(mission_id, int) or not 1 <= mission_id <= 100:
            raise ValueError("mission_id must be an integer between 1 and 100.")

        with self._lock:
            # If another mission is currently streaming, stop it first.
            if self.is_running:
                logger.info(
                    "Stopping active Simulink replay before selecting Mission %d.",
                    mission_id,
                )
                self._stop_locked()

            self.selected_mission = mission_id

            logger.info(
                "Simulink mission prepared: Mission %d",
                mission_id,
            )

    def start(self) -> None:
        """Start Simulink replay for the currently selected mission."""

        with self._lock:
            if self.selected_mission is None:
                self.selected_mission = 1
                logger.info(
                    "No mission selected; defaulting to Mission 1."
                )

            if self.is_running:
                logger.info(
                    "Simulink Mission %d is already running.",
                    self.selected_mission,
                )
                return

            mission_id = self.selected_mission

            matlab_command = (
                f"cd('{self.simulink_dir.replace(chr(92), '/')}'"
                f"); run_mission({mission_id}, {self.stop_time})"
            )

            logger.info(
                "Starting Simulink Mission %d.",
                mission_id,
            )

            logger.info(
                "MATLAB command: %s",
                matlab_command,
            )

            self.process = subprocess.Popen(
                [
                    self.matlab_command,
                    "-batch",
                    matlab_command,
                ],
                cwd=self.simulink_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            threading.Thread(
                target=self._read_output,
                args=(self.process, mission_id),
                daemon=True,
            ).start()

    def stop(self) -> None:
        """Stop the currently running Simulink replay."""

        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        if not self.is_running:
            self.process = None
            return

        process = self.process

        logger.info(
            "Stopping Simulink Mission %s (PID %s).",
            self.selected_mission,
            process.pid,
        )

        try:
            if os.name == "nt":
                subprocess.run(
                    [
                        "taskkill",
                        "/PID",
                        str(process.pid),
                        "/T",
                        "/F",
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                process.terminate()

        finally:
            self.process = None

    @staticmethod
    def _read_output(
        process: subprocess.Popen,
        mission_id: int,
    ) -> None:
        """Forward MATLAB output into the telemetry service log."""

        try:
            if process.stdout is not None:
                for line in process.stdout:
                    line = line.rstrip()
                    if line:
                        logger.info(
                            "[Simulink M%d] %s",
                            mission_id,
                            line,
                        )
        except Exception as exc:
            logger.warning(
                "Could not read Simulink output: %s",
                exc,
            )

        return_code = process.wait()

        if return_code == 0:
            logger.info(
                "Simulink Mission %d completed successfully.",
                mission_id,
            )
        else:
            logger.error(
                "Simulink Mission %d exited with code %s.",
                mission_id,
                return_code,
            )

    def close(self) -> None:
        """Cleanly stop Simulink when the telemetry service shuts down."""

        self.stop()