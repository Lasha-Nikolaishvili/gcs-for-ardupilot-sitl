import time
import pygame
from pymavlink import mavutil

def init_joystick():
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        raise RuntimeError("No joystick detected")
    joy = pygame.joystick.Joystick(0)
    joy.init()
    print(f"Joystick initialized: {joy.get_name()}")
    return joy

def connect_sitl(connection_str="udp:127.0.0.1:14550"):
    master = mavutil.mavlink_connection(connection_str)
    print("Waiting for heartbeat from SITL...")
    master.wait_heartbeat()
    print(f"Heartbeat from sys:{master.target_system} comp:{master.target_component}")

    # 1) Set mode → MANUAL
    # mode_id = master.mode_mapping()['ACRO']
    # master.mav.set_mode_send(
    #     master.target_system,
    #     mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    #     mode_id
    # )
    # wait for ACK of DO_SET_MODE
    # while True:
    #     ack = master.recv_match(type='COMMAND_ACK', blocking=True)
    #     if ack.command == mavutil.mavlink.MAV_CMD_DO_SET_MODE:
    #         print("→ Mode set to MANUAL")
    #         break

    # 2) Arm motors
    print("Arming motors (make sure throttle stick is at minimum!)")
    master.arducopter_arm()
    master.motors_armed_wait()
    print("→ Motors armed")

    return master

def scale_axis(raw, in_min=-1.0, in_max=1.0, out_min=-1000, out_max=1000):
    raw = max(min(raw, in_max), in_min)
    return int((raw - in_min) / (in_max - in_min) * (out_max - out_min) + out_min)

def scale_throttle(raw):
    # map [-1..1] → [0..1000]
    val = (raw + 1.0) / 2.0
    return int(val * 1000)

def main():
    joy    = init_joystick()
    master = connect_sitl()

    try:
        while True:
            pygame.event.pump()

            # adjust axis indices per your joystick
            raw_roll  = joy.get_axis(0)
            raw_pitch = joy.get_axis(1)
            raw_thr   = joy.get_axis(2)
            raw_yaw   = joy.get_axis(3)

            x = scale_axis(  raw_roll )      # roll
            y = scale_axis(-raw_pitch)      # pitch (invert forward→+)
            z = scale_throttle(raw_thr)     # throttle
            r = scale_axis(  raw_yaw )      # yaw
            buttons = 0                      # pack buttons if you like

            master.mav.manual_control_send(
                master.target_system,
                x, y, z, r,
                buttons
            )

            # Debug
            print(f"MC → x:{x} y:{y} z:{z} r:{r}")
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("Exiting…")
    finally:
        pygame.joystick.quit()
        pygame.quit()

if __name__ == "__main__":
    main()
