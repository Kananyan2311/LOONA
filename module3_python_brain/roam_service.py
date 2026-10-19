"""
Project L.O.O.N.A. - Autonomous Idle Roam & Collision Avoidance Engine
Module: roam_service.py

Behavior:
When LOONA is idle, it wakes up periodically to "run a little bit like move a little",
exploring the area while actively avoiding people and obstacles:
  - If a person / face is detected ahead: stops safely, looks up with curious expression,
    wags tail, reverses slightly, and steers away from them.
  - If an obstacle or object is detected in front/lower sectors: stops, backs up,
    and pivots towards the clearer side (left or right).
  - Pauses to look around (pans gaze / servos), twitches ears/tail, and rests before the next nudge.
  - Fully yields to manual joystick control, E-stop, voice commands, and follow mode.
"""

import time
import random
from typing import Tuple, Optional, Dict, Any


class RoamState:
    STANDBY = "standby"              # Roaming disabled or waiting for idle
    IDLE_REST = "idle_rest"          # Pausing between moves, observing
    LOOK_AROUND = "look_around"      # Turning head / gaze to inspect path
    NUDGE_MOVE = "nudge_move"        # Moving forward gently ("run a little bit")
    AVOID_PERSON = "avoid_person"    # Backing off and turning away from human
    AVOID_OBSTACLE = "avoid_obstacle"# Reversing and steering around detected object
    PLAYFUL_PAUSE = "playful_pause"  # Twitches ears / wags tail


class RoamController:
    def __init__(self):
        self.enabled: bool = False
        self.state: str = RoamState.STANDBY
        self.state_start_time: float = time.time()
        self.state_duration: float = 3.0

        # Safe driving parameters for cute indoor roaming
        self.roam_fwd_speed: int = 120         # Gentle forward PWM speed
        self.roam_reverse_speed: int = -105    # Gentle reverse speed
        self.roam_turn_speed: int = 150        # Gentle pivot turn speed

        # Avoidance memory
        self.avoid_turn_dir: int = 1           # +1 for right turn, -1 for left turn
        self.consecutive_nudges: int = 0
        self.last_avoidance_reason: str = ""

    def set_enabled(self, enabled: bool):
        """Enables or disables autonomous roaming."""
        self.enabled = bool(enabled)
        if self.enabled:
            self._transition_to(RoamState.IDLE_REST, duration=random.uniform(2.0, 4.0))
            print("[ROAM] Autonomous Idle Roaming & Avoidance ENGAGED.")
        else:
            self.state = RoamState.STANDBY
            print("[ROAM] Autonomous Idle Roaming DISENGAGED.")

    def is_enabled(self) -> bool:
        return self.enabled

    def get_status(self) -> Dict[str, Any]:
        """Returns current roaming telemetry."""
        return {
            "enabled": self.enabled,
            "state": self.state,
            "reason": self.last_avoidance_reason,
            "nudge_count": self.consecutive_nudges
        }

    def _transition_to(self, new_state: str, duration: float):
        self.state = new_state
        self.state_start_time = time.time()
        self.state_duration = duration

    def update(self, tracking_state: Dict[str, Any], can_move: bool = True) -> Tuple[int, int, Optional[str], Optional[str]]:
        """
        Executes one tick of the autonomous roaming state machine.
        
        Args:
            tracking_state: Output from VisionTracker.get_tracking_state()
            can_move: False if manual override, following, or speech is active.
            
        Returns:
            (motor_fwd, motor_turn, emotion_or_None, servo_preset_or_None)
        """
        if not self.enabled or not can_move:
            if self.state != RoamState.STANDBY:
                self.state = RoamState.STANDBY
            return 0, 0, None, None

        now = time.time()
        elapsed = now - self.state_start_time
        nav = tracking_state.get("nav", {})
        person_ahead = nav.get("person_ahead", False)
        person_close = nav.get("person_close", False)
        center_blocked = nav.get("center_blocked", False)
        left_blocked = nav.get("left_blocked", False)
        right_blocked = nav.get("right_blocked", False)
        clear_direction = nav.get("clear_direction", "forward")

        # -----------------------------------------------------------------
        # 1. IMMEDIATE COLLISION / PERSON INTERRUPTS DURING FORWARD NUDGE
        # -----------------------------------------------------------------
        if self.state == RoamState.NUDGE_MOVE:
            # Check for person directly in path
            if person_ahead and (person_close or tracking_state.get("face_detected")):
                self.last_avoidance_reason = "Person detected ahead"
                # Steer away from whichever side person is located
                dx = tracking_state.get("dx", 0.0)
                self.avoid_turn_dir = -1 if dx > 0 else 1  # Turn opposite of person
                self._transition_to(RoamState.AVOID_PERSON, duration=1.6)
                return 0, 0, "listening", "curious_tilt"

            # Check for obstacle in front
            if center_blocked or (left_blocked and right_blocked):
                self.last_avoidance_reason = "Obstacle in path"
                if not left_blocked and right_blocked:
                    self.avoid_turn_dir = -1  # Turn left
                elif not right_blocked and left_blocked:
                    self.avoid_turn_dir = 1   # Turn right
                else:
                    self.avoid_turn_dir = random.choice([-1, 1])
                self._transition_to(RoamState.AVOID_OBSTACLE, duration=1.8)
                return 0, 0, "surprised", None

        # -----------------------------------------------------------------
        # 2. STATE MACHINE EXECUTION
        # -----------------------------------------------------------------
        if self.state == RoamState.STANDBY:
            self._transition_to(RoamState.IDLE_REST, duration=random.uniform(2.5, 4.5))
            return 0, 0, "neutral", None

        elif self.state == RoamState.IDLE_REST:
            if elapsed >= self.state_duration:
                # Decide next action: look around or nudge forward
                roll = random.random()
                if roll < 0.35 and self.consecutive_nudges > 0:
                    # Cute pause with ear / tail twitch
                    self._transition_to(RoamState.PLAYFUL_PAUSE, duration=1.2)
                    preset = "perk_ears" if random.random() < 0.5 else "wag_tail"
                    return 0, 0, "happy", preset
                elif roll < 0.70:
                    # Look around before moving
                    self._transition_to(RoamState.LOOK_AROUND, duration=random.uniform(1.2, 1.8))
                    return 0, 0, "listening", None
                else:
                    # Nudge forward
                    duration = random.uniform(1.0, 2.2)
                    self._transition_to(RoamState.NUDGE_MOVE, duration=duration)
                    self.consecutive_nudges += 1
                    return self.roam_fwd_speed, 0, "happy", None
            return 0, 0, None, None

        elif self.state == RoamState.LOOK_AROUND:
            if elapsed >= self.state_duration:
                # After looking around, if clear, nudge forward!
                if not center_blocked and not person_close:
                    duration = random.uniform(1.0, 2.0)
                    self._transition_to(RoamState.NUDGE_MOVE, duration=duration)
                    self.consecutive_nudges += 1
                    return self.roam_fwd_speed, 0, "happy", None
                else:
                    # Path obstructed, rotate towards clear side
                    turn_dir = -1 if clear_direction == "left" else 1
                    self.avoid_turn_dir = turn_dir
                    self._transition_to(RoamState.AVOID_OBSTACLE, duration=1.4)
                    return 0, int(turn_dir * self.roam_turn_speed), "neutral", None
            return 0, 0, "thinking", None

        elif self.state == RoamState.NUDGE_MOVE:
            if elapsed >= self.state_duration:
                # Completed forward nudge safely! Rest and observe
                self._transition_to(RoamState.IDLE_REST, duration=random.uniform(2.5, 5.0))
                return 0, 0, "neutral", None
            # Continue rolling forward gently
            return self.roam_fwd_speed, 0, None, None

        elif self.state == RoamState.AVOID_PERSON:
            # Back up gently for first 0.6s, then pivot away
            if elapsed < 0.6:
                return self.roam_reverse_speed, 0, "listening", None
            elif elapsed < self.state_duration:
                return 0, int(self.avoid_turn_dir * self.roam_turn_speed), "happy", None
            else:
                self.consecutive_nudges = 0
                self._transition_to(RoamState.IDLE_REST, duration=random.uniform(2.0, 3.5))
                return 0, 0, "neutral", "wag_tail"

        elif self.state == RoamState.AVOID_OBSTACLE:
            # Reverse gently for first 0.7s, then pivot away towards clear sector
            if elapsed < 0.7:
                return self.roam_reverse_speed, 0, "surprised", None
            elif elapsed < self.state_duration:
                return 0, int(self.avoid_turn_dir * self.roam_turn_speed), "curious_tilt", None
            else:
                self.consecutive_nudges = 0
                self._transition_to(RoamState.LOOK_AROUND, duration=1.2)
                return 0, 0, "neutral", None

        elif self.state == RoamState.PLAYFUL_PAUSE:
            if elapsed >= self.state_duration:
                self._transition_to(RoamState.IDLE_REST, duration=random.uniform(2.0, 4.0))
                return 0, 0, "neutral", None
            return 0, 0, "star_eyes", None

        return 0, 0, None, None


# Global singleton instance
roam_service = RoamController()

