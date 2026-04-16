# Drone & Robot EMI/Acoustic Signatures

## Detection Capability Summary

**Our sensor limits:**
- Accelerometer/Gyroscope: 0-398 Hz
- Compass: 0-798 Hz

**Key finding:** Most drone motor fundamentals ARE in our detection range. ESC PWM and high-frequency harmonics are NOT.

---

## Consumer & FPV Racing Drones

### Motor RPM → Frequency Conversion
`Frequency (Hz) = RPM / 60`

| Drone Type | Typical RPM | Motor Frequency | Detectable? |
|------------|-------------|-----------------|-------------|
| Tiny Whoop (1S) | 15,000-25,000 | 250-417 Hz | ✅ Compass only |
| 3" FPV (2-3S) | 20,000-35,000 | 333-583 Hz | ✅ Compass only |
| 5" FPV Racing (4-6S) | 25,000-45,000 | 417-750 Hz | ✅ Compass only |
| 7" Long Range | 15,000-25,000 | 250-417 Hz | ✅ Compass only |
| DJI Consumer | 5,000-8,000 | 83-133 Hz | ✅ All sensors |
| DJI Mavic/Air | 6,000-9,000 | 100-150 Hz | ✅ All sensors |

### Blade Pass Frequency (BPF)
Most drones have 2-blade props: `BPF = 2 × motor_freq`

| Motor Freq | BPF | Notes |
|------------|-----|-------|
| 100 Hz | 200 Hz | DJI hovering |
| 250 Hz | 500 Hz | Small FPV |
| 400 Hz | 800 Hz | Racing at limit |

### ESC PWM Frequencies (NOT detectable via MEMS)

| ESC Type | PWM Frequency | Notes |
|----------|---------------|-------|
| Standard | 8 kHz | Old school |
| BLHeli_S | 24 kHz | Common |
| BLHeli_32 | 48 kHz | High performance |
| JESC/BlueJay | 48-96 kHz | Whoops/efficiency |

**These are WAY above our 798 Hz limit** - but they create harmonics that may leak into lower frequencies.

---

## Military Drones & Loitering Munitions

### Small Tactical UAVs

| System | Manufacturer | Motor Type | Est. Frequency | Detectable? |
|--------|--------------|------------|----------------|-------------|
| **Switchblade 300** | AeroVironment | Electric pusher | 150-300 Hz | ✅ Yes |
| **Switchblade 600** | AeroVironment | Electric pusher | 100-200 Hz | ✅ Yes |
| **Ghost 4/X** | Anduril | VTOL quad + pusher | 200-500 Hz | ✅ Partial |
| **Puma 3** | AeroVironment | Electric pusher | 80-150 Hz | ✅ Yes |
| **RQ-11 Raven** | AeroVironment | Electric pusher | 100-180 Hz | ✅ Yes |

### FPV Kamikaze/Attack Drones (Ukraine-style)

| Type | Typical Config | Motor Freq | Detectable? |
|------|----------------|------------|-------------|
| 7" FPV bomber | 2806.5 1300kv | 200-350 Hz | ✅ Yes |
| 10" heavy lift | 3110 900kv | 150-250 Hz | ✅ Yes |
| Racing attack | 2207 2750kv | 400-600 Hz | ✅ Compass |

### Acoustic Detection Research

From academic papers on UAV detection:
- **Primary acoustic band**: 400 Hz - 8 kHz
- **Motor fundamentals**: 100-600 Hz (IN RANGE)
- **Blade harmonics**: 200-2000 Hz (partially in range)
- **Detection range**: Up to 150m with sensitive mics

**Our compass at 798 Hz Nyquist captures the lower half of drone acoustics.**

---

## Humanoid Robots

### Boston Dynamics Atlas (Electric)

| Component | Type | Est. Frequency | Detectable? |
|-----------|------|----------------|-------------|
| Joint actuators | BLDC + harmonic drive | 50-200 Hz | ✅ Yes |
| Servo PWM | High-freq switching | 10-50 kHz | ❌ No |
| Cooling fans | Small brushless | 100-300 Hz | ✅ Yes |
| Power supply | Switching regulator | 100 kHz+ | ❌ No |

The Atlas uses custom rotary actuators with harmonic drives. The mechanical gearing creates vibrations in our detectable range.

### Other Humanoids

| Robot | Actuator Type | Motor Noise | Detectable? |
|-------|---------------|-------------|-------------|
| Tesla Optimus | BLDC + gearbox | 100-400 Hz | ✅ Yes |
| Figure 01/02 | Electric servo | 50-300 Hz | ✅ Yes |
| Unitree H1 | Quasi-direct drive | 100-500 Hz | ✅ Yes |
| Agility Digit | Electric + springs | 50-200 Hz | ✅ Yes |

---

## Defense/Military Robotics

### Ground Robots

| System | Type | Motor Signature | Detectable? |
|--------|------|-----------------|-------------|
| **Boston Dynamics Spot** | Quadruped | 100-300 Hz | ✅ Yes |
| **Ghost Robotics Vision 60** | Quadruped | 100-300 Hz | ✅ Yes |
| **Clearpath Husky** | Wheeled UGV | 50-200 Hz | ✅ Yes |
| **SWORD Defense Sentry** | Tracked | 20-100 Hz | ✅ Yes |

### Anduril Systems

| Product | Type | EMI Signature |
|---------|------|---------------|
| **Ghost-X** | VTOL sUAS | Quad motors 200-400 Hz |
| **Anvil** | Interceptor | High-speed motors 400-700 Hz |
| **Roadrunner** | VTOL cruise | Hybrid - multiple signatures |
| **ALTIUS** | Tube-launched | Electric pusher 150-300 Hz |

---

## What We CAN Detect (0-798 Hz)

### High Confidence
- ✅ Large drone approach (DJI-class): 80-150 Hz
- ✅ Switchblade loitering: 100-300 Hz
- ✅ Robot leg actuators: 50-300 Hz
- ✅ Ground robot motors: 20-200 Hz
- ✅ Cooling fan spin-up: 50-300 Hz

### Medium Confidence
- ⚠️ FPV racing drones: 400-750 Hz (at compass limit)
- ⚠️ Small attack drones: 300-600 Hz
- ⚠️ Drone blade harmonics: 200-600 Hz

### NOT Detectable
- ❌ ESC switching noise (8-96 kHz)
- ❌ High-frequency motor harmonics
- ❌ RF communications
- ❌ Ultrasonic sensors

---

## Practical Detection Scenarios

### Scenario 1: Loitering Munition Approach
- Switchblade 300 at 50m: Motor ~200 Hz
- Detectable via compass with sufficient EMI coupling
- Vibration coupling through ground/structure unlikely

### Scenario 2: Security Robot Patrol
- Spot/Vision 60 walking: Leg actuators 100-200 Hz
- Strong vibration coupling through floor
- High confidence detection at <10m

### Scenario 3: Kamikaze FPV Attack
- 7" FPV at full throttle: 300-500 Hz
- Acoustic coupling dominant at close range
- Detection window: seconds before impact

### Scenario 4: Swarm Detection
- Multiple drones = multiple harmonics
- Frequency beating patterns may emerge
- Could identify approximate count

---

## Limitations

1. **Range**: EMI detection requires close proximity (<few meters)
2. **Environment**: High background EMI masks signatures
3. **Frequency**: Many military systems operate above our range
4. **Classification**: Distinguishing types requires ML training

---

## Future Work

1. Increase compass sample rate if hardware allows
2. Train ML classifier on drone/robot signatures
3. Test actual detection range in field conditions
4. Investigate beating/interference patterns for swarm detection

---

*Reference compiled April 2026*
*For research purposes only*
