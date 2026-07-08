# Robotics & Autonomy

## Coordinate frames & TF
- Always name frames explicitly: `base_link` (robot body), `odom` (continuous, drifts), `map` (discrete, jumps on correction), `base_footprint`, sensor frames. TF errors are the #1 bug — a transform between the wrong frames looks plausible.
- REP-103: x forward, y left, z up; right-handed. Radians, meters, m/s, SI throughout. Quaternions for orientation (no gimbal lock); normalize before use.
- REP-105 frame tree: `map -> odom -> base_link -> sensors`. Exactly one parent per frame; TF is a tree, not a graph. Two publishers on the same child = flicker.
- `map->odom` is published by localization (AMCL/SLAM) and absorbs drift; `odom->base_link` by the odometry source and must be smooth/continuous.
- Static transforms (sensor mounts) via `static_transform_publisher`; never time-varying. Check `ros2 run tf2_tools view_frames` and `tf2_echo` when poses look wrong.

## ROS2 basics
- Node = process unit; communicate via topics (pub/sub, async, many-to-many), services (request/reply, sync, 1:1), actions (long goals: goal/feedback/result, cancelable).
- QoS must match or connections silently fail: `RELIABLE` vs `BEST_EFFORT`, `KEEP_LAST(depth)` vs `KEEP_ALL`, `VOLATILE` vs `TRANSIENT_LOCAL` (latched). Sensors → BEST_EFFORT; commands/TF static → RELIABLE + TRANSIENT_LOCAL.
- DDS is the middleware; use `ROS_DOMAIN_ID` to isolate robots on one LAN. Lifecycle nodes for deterministic bringup (configure→activate).
- Timestamp every message in the sensor frame; consumers use the stamp, not wall clock. Use `use_sim_time` with a `/clock` source in sim/rosbag.

## Sensor fusion
- Kalman filter: linear, Gaussian; predict (motion model) then update (measurement). Tune `Q` (process noise, trust in model) vs `R` (measurement noise, trust in sensor). Too-small `R` = jittery, chases noise; too-large `R` = laggy, ignores sensor.
- EKF linearizes via Jacobians (fine for mild nonlinearity, e.g. `robot_localization`); UKF uses sigma points (better for strong nonlinearity, no Jacobians). Particle filter for multimodal/non-Gaussian (AMCL).
- Fuse absolute + relative: wheel odom (drifts, smooth) + IMU (yaw drift, high-rate) + GPS/SLAM (absolute, noisy). Feed continuous sources to the `odom` output, absolute fixes to the `map` output.
- IMU: gyro integrates to angle (drifts), accel is noisy/gravity-laden. Always calibrate bias at rest; don't integrate accel to position naively.

## Localization & mapping
- Odometry-only pose diverges without bound — unbounded integration of wheel slip and scale error. Bound it with a correction source.
- SLAM (slam_toolbox, Cartographer) builds map + localizes; loop closure corrects accumulated drift. AMCL localizes in a *known* map via particle filter; needs a decent initial pose estimate.
- Scan matching (ICP/NDT) aligns consecutive LiDAR scans; degenerate in feature-poor corridors (aperture problem).

## Control
- PID: P reduces error (too high → oscillation), I removes steady-state offset (too high → windup/overshoot), D damps (amplifies noise; filter D). Tune P up to sustained oscillation, back off ~50%, add D, then minimal I.
- Add anti-windup (clamp/back-calculate integral when actuator saturates). Feedforward (known dynamics/gravity comp) does the bulk; PID only trims residual error — dramatically better tracking than PID alone.
- Cascade loops: fast inner (torque/velocity) inside slow outer (position). Inner loop bandwidth must exceed outer by ~5-10x.

## Motion planning
- Global planner on a costmap: A* (optimal, grid, admissible heuristic), Dijkstra (no heuristic), RRT/RRT* (sampling, high-DOF/continuous; RRT* asymptotically optimal). Local planner (DWA/TEB) for dynamic obstacles + kinodynamic limits.
- Costmap layers: static (map), obstacle (live sensors), inflation (buffer by robot radius + safety). Inflation radius < robot radius → clipped corners/collisions.
- Nav2 = behavior tree orchestrating planner/controller/recovery. Set robot footprint accurately; a point-robot assumption collides.

## Kinematics
- Forward kinematics (joint angles → end-effector pose) is unique; inverse kinematics (pose → joints) may have 0, multiple, or infinite solutions. Watch singularities (Jacobian loses rank → infinite joint velocity commanded).
- Differential drive: `v = r(ωL+ωR)/2`, `ω = r(ωR−ωL)/L`. Nonholonomic — can't move sideways; plan feasible paths.
- Denavit–Hartenberg parameters standardize manipulator link frames; the Jacobian maps joint velocities to end-effector twist (and, transposed, forces to joint torques).

## Perception & timing
- Camera-LiDAR-IMU must be time-synchronized (hardware trigger or PTP) and extrinsically calibrated; a few-cm/few-ms error smears fused points. Approximate-time sync policies to align multi-rate streams.
- Detection/estimation latency shifts the world estimate — compensate to the command time, don't act on stale state. Log timestamps end-to-end to find pipeline lag.

## Real-time & safety
- Hardware E-stop must cut motor power independently of software — never gate safety solely through the compute stack.
- Watchdog/deadman: command timeout (e.g. lose heartbeat >100-200ms) → stop motors. Publish velocity at a fixed rate; stale `cmd_vel` must trigger stop, not coast.
- Bound every actuator command (velocity/accel/jerk limits) before it leaves the controller.

## Gotchas -> Fix
- **Robot drifts over time**: odometry-only pose. Fix: fuse a correction source (SLAM/AMCL/GPS) via EKF; output `map->odom`.
- **TF "extrapolation into the future/past" errors**: clock skew or mismatched stamps. Fix: sync clocks (NTP/PTP), set `use_sim_time` consistently, buffer TF long enough.
- **Subscriber gets no messages though topic publishes**: QoS mismatch. Fix: align reliability/durability; use BEST_EFFORT for sensor streams.
- **PID oscillates**: P too high / D too low or noisy. Fix: lower P, add filtered D, verify loop rate is constant.
- **Integral windup after saturation**: Fix: clamp or back-calculate integral when actuator is saturated.
- **Robot clips corners / hits obstacles the planner "avoided"**: footprint or inflation radius too small. Fix: set true footprint, inflation ≥ robot radius + margin.
- **IMU yaw slowly rotates when still**: gyro bias. Fix: calibrate bias at rest, fuse a heading reference (mag/GPS).
- **Two nodes publish same TF child**: tree flicker. Fix: exactly one publisher per edge.
- **AMCL never converges**: bad initial pose or wrong map. Fix: set initial pose, verify map/scan frame alignment.
- **cmd_vel jerks then coasts on comms loss**: no deadman. Fix: watchdog stops motors on stale command.
