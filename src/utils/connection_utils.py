from pymavlink import mavutil

def get_waypoint_command_type(i, l):
    if i == 0:
        return mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
    elif i == l - 1:
        return mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH
    else:
        return mavutil.mavlink.MAV_CMD_NAV_WAYPOINT