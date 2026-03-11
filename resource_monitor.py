"""
Resource monitoring and idle prediction for Project Arachne.
"""
import psutil
import time
import logging
from typing import Tuple, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    cpu_percent: float
    memory_percent: float
    disk_io_count: int
    network_io_count: int
    timestamp: datetime

class ResourceMonitor:
    """Monitors system resources and predicts idle windows."""

    def __init__(self, idle_cpu_threshold: float = 15.0, idle_memory_threshold: float = 80.0):
        self.idle_cpu_threshold = idle_cpu_threshold
        self.idle_memory_threshold = idle_memory_threshold
        self.history: list[SystemStatus] = []
        self.model: Optional[RandomForestRegressor] = None

    def is_idle(self) -> bool:
        """Check if the system is currently idle."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()

        # Record current status
        current_status = SystemStatus(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_io_count=disk_io.read_count + disk_io.write_count if disk_io else 0,
            network_io_count=network_io.packets_sent + network_io.packets_recv if network_io else 0,
            timestamp=datetime.now()
        )
        self.history.append(current_status)

        # Keep only last 24 hours of data (assuming one sample per check interval)
        # We'll approximate by keeping the last 2880 samples (if checking every 30 seconds)
        if len(self.history) > 2880:
            self.history = self.history[-2880:]

        # Check idle condition
        if cpu_percent < self.idle_cpu_threshold and memory_percent < self.idle_memory_threshold:
            logger.info(f"System is idle: CPU {cpu_percent}%, Memory {memory_percent}%")
            return True
        else:
            logger.debug(f"System not idle: CPU {cpu_percent}%, Memory {memory_percent}%")
            return False

    def train_idle_predictor(self) -> None:
        """Train a model to predict idle periods."""
        if len(self.history) < 100:
            logger.warning("Not enough historical data to train predictor.")
            return

        # Prepare features: hour, day_of_week, rolling averages of cpu and memory
        data = []
        for i, status in enumerate(self.history):
            # Use past 10 samples to predict next sample's cpu and memory
            if i < 10:
                continue
            prev_cpu = [self.history[j].cpu_percent for j in range(i-10, i)]
            prev_memory = [self.history[j].memory_percent for j in range(i-10, i)]
            features = [
                status.timestamp.hour,
                status.timestamp.weekday(),
                np.mean(prev_cpu),
                np.mean(prev_memory),
                np.std(prev_cpu),
                np.std(prev_memory)
            ]
            # Target: whether the next sample will be idle
            next_cpu = self.history[i].cpu_percent if i < len(self.history)-1 else self.history[-1].cpu_percent
            next_memory = self.history[i].memory_percent if i < len(self.history)-1 else self.history[-1].memory_percent
            target = 1 if (next_cpu < self.idle_cpu_threshold and next_memory < self.idle_memory_threshold) else 0
            data.append((features, target))

        if len(data) < 50:
            logger.warning("Not enough labeled data for training.")
            return

        X, y = zip(*data)
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X, y)
        logger.info("Idle predictor model trained.")

    def predict_idle_window(self, minutes_ahead: int = 30) -> float:
        """Predict the probability of an idle window in the next `minutes_ahead` minutes."""
        if self.model is None:
            self.train_idle_predictor()
            if self.model is None:
                return 0.0

        # Use the last 10 samples to predict the future
        if len(self.history) < 10:
            return 0.0

        last_status = self.history[-1]
        prev_cpu = [s.cpu_percent for s in self.history[-10:]]
        prev_memory = [s.memory_percent for s in self.history[-10:]]

        # We'll predict for the next `minutes_ahead` minutes by assuming the same time pattern
        future_time = last_status.timestamp.timestamp() + minutes_ahead * 60
        future_dt = datetime.fromtimestamp(future_time)

        features = [
            future_dt.hour,
            future_dt.weekday(),
            np.mean(prev_cpu),
            np.mean(prev_memory),
            np.std(prev_cpu),
            np.std(prev_memory)
        ]

        prob = self.model.predict([features])[0]
        return prob