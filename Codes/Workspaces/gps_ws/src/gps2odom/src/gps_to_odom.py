#!/usr/bin/env python

import rospy
from marvelmind_nav.msg import hedge_pos_ang
from nav_msgs.msg import Odometry
from std_msgs.msg import Float64
from geometry_msgs.msg import Quaternion
import geometry_msgs.msg
import tf_conversions
import tf2_ros

odom_msg = Odometry()

def gps_callback(data):
    # rospy.loginfo(rospy.get_caller_id() + "I heard %s", data)
    odom_msg.pose.pose.position.x = data.x_m #hedgehog offset 
    odom_msg.pose.pose.position.y = data.y_m
    odom_msg.pose.pose.position.z = data.z_m


def imu_callback(msg):
    odom_msg.pose.pose.orientation.x = msg.x
    odom_msg.pose.pose.orientation.y = msg.y
    odom_msg.pose.pose.orientation.z = msg.z
    odom_msg.pose.pose.orientation.w = msg.w


def gps2odom_converter():
    rospy.init_node("gps2odom", anonymous=True)
    rospy.Subscriber("hedge_pos_ang", hedge_pos_ang, gps_callback)
    rospy.Subscriber("imu_quaternion", Quaternion, imu_callback)
    odom_pub = rospy.Publisher("odom_gps", Odometry, queue_size=10)
    rate = rospy.Rate(100)  # 10hz

    tf_br_odom = tf2_ros.TransformBroadcaster()
    tf_msg_odom = geometry_msgs.msg.TransformStamped()

    tf_br_map = tf2_ros.StaticTransformBroadcaster()
    tf_msg_map = geometry_msgs.msg.TransformStamped()

    while not rospy.is_shutdown():
        odom_msg.header.stamp = rospy.Time.now()
        odom_msg.header.frame_id = "odom_gps"
        odom_msg.child_frame_id = "base_link_gps"
        odom_pub.publish(odom_msg)

        tf_msg_odom.header.stamp = rospy.Time.now()
        tf_msg_odom.header.frame_id = "odom_gps"
        tf_msg_odom.child_frame_id = "base_link_gps"
        tf_msg_odom.transform.translation.x = odom_msg.pose.pose.position.x
        tf_msg_odom.transform.translation.y = odom_msg.pose.pose.position.y
        tf_msg_odom.transform.translation.z = odom_msg.pose.pose.position.z
        tf_msg_odom.transform.rotation.x = odom_msg.pose.pose.orientation.x
        tf_msg_odom.transform.rotation.y = odom_msg.pose.pose.orientation.y
        tf_msg_odom.transform.rotation.z = odom_msg.pose.pose.orientation.z
        tf_msg_odom.transform.rotation.w = odom_msg.pose.pose.orientation.w
        tf_br_odom.sendTransform(tf_msg_odom)

        tf_msg_map.header.stamp = rospy.Time.now()
        tf_msg_map.header.frame_id = "map"
        tf_msg_map.child_frame_id = "odom_gps"

        tf_msg_map.transform.translation.x = 6 # robot in map 
        tf_msg_map.transform.translation.y = 6
        tf_msg_map.transform.translation.z = 0

        quat = tf_conversions.transformations.quaternion_from_euler(0, 0, 0)
        tf_msg_map.transform.rotation.x = quat[0]
        tf_msg_map.transform.rotation.y = quat[1]
        tf_msg_map.transform.rotation.z = quat[2]
        tf_msg_map.transform.rotation.w = quat[3]

        tf_br_map.sendTransform(tf_msg_map)

        rate.sleep()

    # spin() simply keeps python from exiting until this node is stopped
    rospy.spin()


if __name__ == "__main__":
    gps2odom_converter()
