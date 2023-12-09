import rospy
from sensor_msgs.msg import Image
import cv2

cap = cv2.VideoCapture(0)
print(cap.isOpened())


def cv2_to_imgmsg(cv_image):
    img_msg = Image()
    img_msg.height = cv_image.shape[0]
    img_msg.width = cv_image.shape[1]
    img_msg.encoding = "bgr8"
    img_msg.is_bigendian = 0
    img_msg.data = cv_image.tostring()
    img_msg.step = (
        len(img_msg.data) // img_msg.height
    )  # That double line is actually integer division, not a comment
    return img_msg


def talker():
    pub = rospy.Publisher("/image_raw", Image, queue_size=1)
    rospy.init_node("image", anonymous=False)
    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        ret, frame = cap.read()
        # cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
        # cv2.imshow("Image", frame)
        # cv2.waitKey(10)
        if not ret:
            break

        msg = cv2_to_imgmsg(frame)
        pub.publish(msg)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        if rospy.is_shutdown():
            cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        talker()
    except rospy.ROSInterruptException:
        pass
