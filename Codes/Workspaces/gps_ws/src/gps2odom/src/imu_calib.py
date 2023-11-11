#!/usr/bin/env python

from re import L
import rospy
from marvelmind_nav.msg import hedge_imu_fusion
from std_msgs.msg import Float64
import tf_conversions

counter = 0

def imu_callback(data):
    # rospy.loginfo(rospy.get_caller_id() + "I heard %s", data)
    global counter, imu_data
    euler = tf_conversions.transformations.euler_from_quaternion([data.qx,data.qy,data.qz,data.qw])
    imu_data.append(euler[2])
    # print(euler[2])
    # counter += 1
    if(len(imu_data) == 10):
        average = sum(imu_data)/10
        print(average)
        imu_data = []


def imu_calibration():
    rospy.init_node("imu_calib", anonymous=True)
    rospy.Subscriber("hedge_imu_fusion", hedge_imu_fusion, imu_callback)
    rospy.spin()


if __name__ == "__main__":
    imu_calibration()


#0.7114565
#0.0689285
#-0.6259739
#-0.973481

#-0.9555081
#-0.3699168

#6.21536624
#6.


















#1.49714022855