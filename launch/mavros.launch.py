#!/usr/bin/env python3

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from launch_ros.parameter_descriptions import ParameterFile


def generate_launch_description():
    pkg_name = "mrs_uav_px4_api"
    this_pkg_path = get_package_share_directory(pkg_name)

    OLD_PX4_FW = os.getenv("OLD_PX4_FW", "false") == "true"
    PX4_IP = os.getenv("PX4_IP", "")
    USE_SIM_TIME = os.getenv("USE_SIM_TIME", "false") == "true"
    UAV_NAME = os.getenv("UAV_NAME", "uav1")

    # Extract UAV ID number (e.g., uav1 -> 1, uav2 -> 2)
    try:
        uav_id = int("".join(filter(str.isdigit, UAV_NAME)))
    except ValueError:
        uav_id = 1

    # Calculate MAVROS ports for simulation:
    # uav1: local_bind = 14006, target_px4 = 14005
    # uav2: local_bind = 14008, target_px4 = 14007
    mavros_local_port = 14006 + (uav_id - 1) * 2
    px4_target_port = 14005 + (uav_id - 1) * 2

    if USE_SIM_TIME or PX4_IP != "":
        target_ip = PX4_IP if PX4_IP else "127.0.0.1"
        default_fcu_url = f"udp://:{mavros_local_port}@{target_ip}:{px4_target_port}"
    else:
        rate = 921600 if OLD_PX4_FW else 2000000
        default_fcu_url = f"/dev/pixhawk:{rate}"

    default_garmin_id = "33" if OLD_PX4_FW else "0"
    default_garmin_orientation = "0" if OLD_PX4_FW else "PITCH_270"

    uav_name = LaunchConfiguration("uav_name")
    fcu_url = LaunchConfiguration("fcu_url")
    gcs_url = LaunchConfiguration("gcs_url")
    tgt_system = LaunchConfiguration("tgt_system")
    config_yaml = LaunchConfiguration("config_yaml")
    use_sim_time = LaunchConfiguration("use_sim_time")
    frame_namespace = LaunchConfiguration("frame_namespace")

    launch_arguments = [
        DeclareLaunchArgument(
            "uav_name",
            default_value=UAV_NAME,
        ),
        DeclareLaunchArgument(
            "fcu_url",
            default_value=default_fcu_url,
            description="FCU URL used by MAVROS",
        ),
        DeclareLaunchArgument(
            "gcs_url",
            default_value="tcp-l://",
            description="GCS URL used by MAVROS",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value=os.getenv("USE_SIM_TIME", "false"),
            description="Whether MAVROS should use sim time",
        ),
        DeclareLaunchArgument(
            "config_yaml",
            default_value=os.path.join(this_pkg_path, "config", "mavros_px4_config.yaml"),
            description="Path to the MAVROS PX4 config YAML file",
        ),
        DeclareLaunchArgument(
            "garmin_id",
            default_value=default_garmin_id,
            description="Distance sensor ID reported by MAVROS for the Garmin",
        ),
        DeclareLaunchArgument(
            "garmin_orientation",
            default_value=default_garmin_orientation,
            description="Garmin sensor orientation enum used by MAVROS",
        ),
        DeclareLaunchArgument(
            "tgt_system",
            default_value=str(uav_id),
            description="Target system ID for MAVROS",
        ),
        DeclareLaunchArgument(
            "frame_namespace",
            default_value=[uav_name, "/mavros"],
            description="Namespace prefix for frame IDs and other identifiers mavros owns",
        ),
    ]

    mavros_node = Node(
        package="mavros",
        executable="mavros_node",
        namespace=[uav_name, "/mavros"],
        output="screen",
        parameters=[
            {"fcu_url": fcu_url},
            {"gcs_url": gcs_url},
            {"tgt_system": tgt_system},
            {"tgt_component": 1},
            {"fcu_protocol": "v2.0"},
            {"use_sim_time": use_sim_time},
            {"base_link_frame_id": [frame_namespace, "/base_link"]},
            {"odom_frame_id": [frame_namespace, "/odom"]},
            {"map_frame_id": [frame_namespace, "/map"]},
            ParameterFile(this_pkg_path + "/config/mavros_plugins.yaml", allow_substs=True),
            ParameterFile(config_yaml, allow_substs=True),
        ],
        remappings=[
            ("/diagnostics", "diagnostics"),
            (["/uas", tgt_system, "/mavlink_source"], "mavlink/source"),
            (["/uas", tgt_system, "/mavlink_sink"], "mavlink/sink"),
        ],
    )

    return LaunchDescription(launch_arguments + [mavros_node])