"""
Deterministic smooth obstacle motion, used for evaluation only.

Each obstacle follows a closed-form path in simulation time t (seconds):

    p(t) = p0 + sum_k A_k * (sin(w_k * t + phi_k) - sin(phi_k))
    v(t) =      sum_k A_k * w_k * cos(w_k * t + phi_k)

A, w, phi are drawn per axis from an RNG seeded by (movement_seed, obs_id),
so the path depends only on t and is identical on every run / process.

Guarantees:
    p(0) = p0                       (start position is the task's position)
    |p(t) - p0| <= amplitude        per axis
    |v(t)|      <= max_speed        (Euclidean)

Task file format (seed only, motion params shared by all obstacles):
    "obstacle_motion": {
        "movement_seed": 1234,
        "max_speed": 0.2,
        "amplitude": 0.3,
        "num_terms": 3
    }
"""

import zlib
import numpy as np


DEFAULT_MOTION = {
    "max_speed": 0.2,
    "amplitude": 0.3,
    "num_terms": 3,
}


class ObstacleMotion:

    def __init__(self, origin, movement_seed, obs_id,
                 amplitude=DEFAULT_MOTION["amplitude"],
                 max_speed=DEFAULT_MOTION["max_speed"],
                 num_terms=DEFAULT_MOTION["num_terms"]):
        self.origin = np.array(origin, dtype=float)

        # Stable per-obstacle seed (Python's hash() is salted per process)
        rng = np.random.default_rng(
            [int(movement_seed), zlib.crc32(str(obs_id).encode())])

        amp = rng.uniform(0.5, 1.0, (num_terms, 3))
        omega = rng.uniform(0.5, 1.5, (num_terms, 3))
        self.phase = rng.uniform(0, 2 * np.pi, (num_terms, 3))

        # sin(.) - sin(phi) lies in [-2, 2], so sum(A) = amplitude / 2 per axis
        self.amp = amp / amp.sum(axis=0) * (amplitude / 2)

        # Scale all frequencies so the speed upper bound equals max_speed
        speed_bound = np.linalg.norm((self.amp * omega).sum(axis=0))
        self.omega = omega * (max_speed / speed_bound)

    @staticmethod
    def from_task(obstacle_motion, obs_id, origin):
        """Build from a task's "obstacle_motion" dict; None means static."""
        if not obstacle_motion or obstacle_motion.get("movement_seed") is None:
            return None
        return ObstacleMotion(
            origin=origin,
            movement_seed=obstacle_motion["movement_seed"],
            obs_id=obs_id,
            amplitude=obstacle_motion.get(
                "amplitude", DEFAULT_MOTION["amplitude"]),
            max_speed=obstacle_motion.get(
                "max_speed", DEFAULT_MOTION["max_speed"]),
            num_terms=obstacle_motion.get(
                "num_terms", DEFAULT_MOTION["num_terms"]))

    def position_at(self, t):
        """t: scalar or array of shape (T,) -> (3,) or (T, 3)"""
        t = np.asarray(t, dtype=float)[..., None, None]
        offset = self.amp * (np.sin(self.omega * t + self.phase)
                             - np.sin(self.phase))
        return self.origin + offset.sum(axis=-2)

    def velocity_at(self, t):
        """t: scalar or array of shape (T,) -> (3,) or (T, 3)"""
        t = np.asarray(t, dtype=float)[..., None, None]
        vel = self.amp * self.omega * np.cos(self.omega * t + self.phase)
        return vel.sum(axis=-2)
