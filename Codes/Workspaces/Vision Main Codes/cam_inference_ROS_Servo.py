# TO DO:
# choose the nearest slug and lock to it
import cv2
import numpy as np
import datetime
import time
import sys

# import matplotlib.pyplot as plt

import torch

torch.cuda.empty_cache()
import torch.backends.cudnn as cudnn

from models.common import DetectMultiBackend
from utils.general import (
    LOGGER,
    check_file,
    check_img_size,
    check_imshow,
    check_requirements,
    colorstr,
    increment_path,
    non_max_suppression,
    print_args,
    scale_coords,
    strip_optimizer,
    xyxy2xywh,
)
from utils.torch_utils import select_device
from utils.augmentations import letterbox

# ROS Imports:
import rospy

# from cv_bridge import CvBridge, CvBridgeError
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from std_msgs.msg import Bool


class Inference:
    """ """

    def __init__(self, iou, conf, model_path, img_size, classes):
        """ """
        # Camera source
        self.cap = cv2.VideoCapture()
        self.cap.open(0)

        # Model params
        self.iou_thres = iou
        self.conf_thres = conf
        self.model_path = model_path
        self.img_size = img_size
        self.classes = classes
        self.half = False

        self._load_model()
        self.image_sub = rospy.Subscriber("/image_raw", Image, self.camera_callback)
        self.cmd_vel_pub = rospy.Publisher("/cmd_vel_vision", Twist, queue_size=10)
        self.servo_pub = rospy.Publisher("/Servo", Bool, queue_size=1)
        self.servo = Bool()
        self.servo = False
        self.twist_object = Twist()

    def _load_model(self):
        """ """
        self.device = select_device("")
        self.model = DetectMultiBackend(
            self.model_path, device=self.device, dnn=False, data=None
        )
        self.stride, names, pt, jit, onnx, engine = (
            self.model.stride,
            self.model.names,
            self.model.pt,
            self.model.jit,
            self.model.onnx,
            self.model.engine,
        )
        self.imgsz = check_img_size(self.img_size, s=self.stride)  # check image size

        # Half
        # half &= (pt or jit or onnx or engine) and device.type != 'cpu'  # FP16 supported on limited backends with CUDA
        # if pt or jit:
        #     self.model.model.half() if half else model.model.float()

        self.model.warmup(imgsz=(1, 3, 416, 416))  # , half=self.half)  # warmup

    def _pt_inference(self, im0):
        """ """
        # LetterBox
        img = letterbox(im0, self.img_size, stride=self.stride, auto=True and True)[0]

        # Convert
        img = img.transpose((2, 0, 1))
        # img = np.ascontiguousarray(img)

        # To tensor format
        im = torch.from_numpy(img).to(self.device)
        im = im.half() if self.half else im.float()  # uint8 to fp16/32
        im /= 255  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim

        # Inference
        pred = self.model(im, augment=False, visualize=False)

        # NMS
        pred = non_max_suppression(
            pred, self.conf_thres, self.iou_thres, None, False, max_det=1000
        )

        # Process predictions
        for i, det in enumerate(pred):  # per image
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0.shape).round()

        return det.cpu().numpy()

    def _display_result(self, predictions, rgb_img):
        """ """
        # Only when we have a detection or slug

        # # Detect only 1 slug at a time to go to
        # print(np.array(predictions, (,)))
        print(len(predictions))
        # if len > 1 =>  take only first element and convert it back to 2D array
        if len(predictions) > 1:
            predictions = predictions[0]
            predictions = np.reshape(predictions, (1, len(predictions)))

        print([predictions])
        for pred in predictions:
            cv2.putText(
                rgb_img,
                f"{self.classes[pred[5].astype(np.uint)]} - {int(pred[4]*100)}",
                (int(pred[0]), int(pred[1])),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            ### ROI Rec 2

            # rectangle over the slug
            cv2.rectangle(
                rgb_img,
                (int(pred[0]), int(pred[1])),
                (int(pred[2]), int(pred[3])),
                (0, 255, 0),
            )

            # Find centroid of the slug
            cx_slug = pred[0] + 0.5 * (pred[2] - pred[0])
            cy_slug = pred[1] + 0.5 * (pred[3] - pred[1])
            print("cx_slug", cx_slug, " cy_slug", cy_slug)
            # Draw centroid
            cv2.circle(rgb_img, (int(cx_slug), int(cy_slug)), 6, (40, 0, 155), -1)

            # center robot with centroid of the slug
            ## find angle from the slug centroid to the roi centroid

            # theta = sin()

            ### problem: sensitive or need a threshold

            ## OR rotate until slug centroid reach lines roi (sim to line follower)
            # if cx_slug not in range(self.threshold_range[0], self.threshold_range[1]):
            #     print("rotate")
            # threshold[0] the left line [1] is the right line
            # slug centroid to the left of the c_roi

            if (
                cx_slug > self.collection_threshold_range_width[0]
                and cx_slug < self.collection_threshold_range_width[1]
                and cy_slug > self.collection_threshold_range_height[0]
                and cy_slug < self.collection_threshold_range_height[1]
            ):
                self.twist_object.linear.x = 0
                self.twist_object.angular.z = 0
                self.servo = True
                print(
                    "im hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhere"
                )

            else:
                if cx_slug < self.threshold_range[0]:
                    print("rotate left")
                    self.twist_object.angular.z = 0.20
                    self.twist_object.linear.x = 0.0
                # slug on the right
                elif cx_slug > self.threshold_range[1]:
                    print("rotate right")
                    self.twist_object.angular.z = -0.20
                    self.twist_object.linear.x = 0.0
                else:
                    print("move forward")
                    self.twist_object.linear.x = 0.15
                    self.twist_object.angular.z = 0.0
                self.servo = False
            self.servo_pub.publish(self.servo)
            self.cmd_vel_pub.publish(self.twist_object)
            # print("cx_slug", cx_slug, "self.width/2", self.width / 2)
            print(
                "threshold_range[0]",
                self.threshold_range[0],
                "threshold_range[1]",
                self.threshold_range[1],
            )

            # if cx_slug in range(self.threshold_range[0], self.threshold_range[1]):
            # else:
            # print("move forward")
            # move forward to the slug until slug reaching our roi

            cv2.imshow("Prediction", rgb_img)
            cv2.waitKey(1)

    def run_img(self):
        """ """
        try:

            self.twist_object.linear.x = 0.2
            self.twist_object.angular.z = 0
            self.servo = False
            self.servo_pub.publish(self.servo)
            # while True:
            # ret, frame = self.cap.read()
            frame = self.cv_image
            predictions = self._pt_inference(frame.copy())
            print(predictions)

            threshold = 40
            # self.width = self.cv_image.shape(1)  # float `width`
            # self.height = self.cv_image.shape(0)  # float `height`
            self.height, self.width, self.channels = self.cv_image.shape

            self.collection_threshold_range_width = [
                int(self.width / 2) - 50,
                int(self.width / 2) + 50,
            ]
            self.collection_threshold_range_height = [
                int(self.height / 2) + 150,
                int(self.height / 2) + 300,
            ]

            # ROI
            cv2.putText(
                frame,
                "Collection ROI",
                (int(self.width / 2) - 50, int(self.height / 2) + 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 0),
                1,
                cv2.LINE_AA,
            )
            # cv2.rectangle(
            #     frame,
            #     (int(self.width / 2) - 50, int(self.height / 2) + 150),
            #     (int(self.width / 2) + 50, int(self.height / 2) + 300),
            #     (0, 255, 0),
            # )
            cv2.rectangle(
                frame,
                (
                    self.collection_threshold_range_width[0],
                    self.collection_threshold_range_height[0],
                ),
                (
                    self.collection_threshold_range_width[1],
                    self.collection_threshold_range_height[1],
                ),
                (0, 255, 0),
            )

            # print(threshold,width,height)
            self.threshold_range = [
                int(self.width / 2 - threshold),
                int(self.width / 2 + threshold),
            ]
            cv2.rectangle(
                frame,
                (self.threshold_range[0], 0),
                (self.threshold_range[1], 480),
                (255, 0, 0),
            )

            print("width, height:", self.width, self.height)
            print(
                "cmd_vel_send: ",
                self.twist_object,
            )

            if len(predictions):
                self._display_result(predictions, frame.copy())
                print("entered predictions")
            else:
                self.cmd_vel_pub.publish(self.twist_object)

                print("entered else")
                cv2.imshow("Prediction", frame)
                cv2.waitKey(1)

            print("collection range width: ", self.collection_threshold_range_width)
            print("collection range height: ", self.collection_threshold_range_height)

        except KeyboardInterrupt:
            print("\nExiting camera inference...")
            pass

    def run2(self):
        """ """
        try:
            while True:
                ret, frame = self.cap.read()
                predictions = self._pt_inference(frame.copy())
                print(predictions)

                threshold = 40

                # ROI of Collection Area
                cv2.putText(
                    frame,
                    "Collection ROI",
                    (int(self.width / 2) - 50, int(self.height / 2) + 150),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 0, 0),
                    1,
                    cv2.LINE_AA,
                )

                cv2.rectangle(
                    frame,
                    (
                        self.collection_threshold_range_width[0],
                        self.collection_threshold_range_height[0],
                    ),
                    (
                        self.collection_threshold_range_width[1],
                        self.collection_threshold_range_height[1],
                    ),
                    (0, 255, 0),
                )

                # print(threshold,width,height)
                self.threshold_range = [
                    int(self.width / 2 - threshold),
                    int(self.width / 2 + threshold),
                ]
                # ROI Forward
                cv2.rectangle(
                    frame,
                    (self.threshold_range[0], 0),
                    (self.threshold_range[1], 480),
                    (255, 0, 0),
                )

                print("width, height:", self.width, self.height)

                if len(predictions):
                    self._display_result(predictions, frame.copy())
                else:
                    cv2.imshow("Prediction", frame)
                    cv2.waitKey(1)

                print("testtttt")

        except KeyboardInterrupt:
            print("\nExiting camera inference...")
            pass

    def imgmsg_to_cv2(self, img_msg):
        if img_msg.encoding != "bgr8":
            rospy.logerr(
                "This Coral detect node has been hardcoded to the 'bgr8' encoding.  Come change the code if you're actually trying to implement a new camera"
            )
        dtype = np.dtype("uint8")  # Hardcode to 8 bits...
        dtype = dtype.newbyteorder(">" if img_msg.is_bigendian else "<")
        image_opencv = np.ndarray(
            shape=(
                img_msg.height,
                img_msg.width,
                3,
            ),  # and three channels of data. Since OpenCV works with bgr natively, we don't need to reorder the channels.
            dtype=dtype,
            buffer=img_msg.data,
        )
        # If the byt order is different between the message and the system.
        if img_msg.is_bigendian == (sys.byteorder == "little"):
            image_opencv = image_opencv.byteswap().newbyteorder()
        return image_opencv

    def camera_callback(self, data):
        print("we are in the callback")

        self.cv_image = self.imgmsg_to_cv2(data)

        # cv2.namedWindow("Image", cv2.WINDOW_NORMAL)
        # cv2.imshow("Image", self.cv_image)
        # cv2.waitKey(10)
        self.run_img()
        # We get image dimensions and crop the parts of the image we dont need
        # Bare in mind that because its image matrix first value is start and second value is down limit.
        # Select the limits so that it gets the line not too close, not too far and the minimum portion possible
        # To make process faster.

        # height, width, channels = self.cv_image.shape

        # descentre = 160
        # rows_to_watch = 100

        # crop_img = cv_image[
        #     (height) / 2 + descentre : (height) / 2 + (descentre + rows_to_watch)
        # ][1:width]

        # Convert from RGB to HSV
        # # hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)

        # error_x = cx - width / 2
        # # twist_object = Twist()
        # # twist_object.angular.z = 5
        # # this code to follow the line
        # twist_object.linear.x = 0.1
        # twist_object.angular.z = -error_x / 50

        # # rospy.loginfo("ANGULAR VALUE SENT===>" + str(twist_object.angular.z))

    def clean_up(self):
        # cap.release()
        cv2.destroyAllWindows()


def main():
    iou = 0.2
    conf = 0.3
    img_size = [416, 416]
    model_path = (
        "/home/nabil/vision_ws/src/pipelinev5/src/yolov5/models/slugs_yolov5s.pt"
        # "/home/nabil/vision_ws/src/pipelinev5/src/yolov5/runs-20220423T095241Z-001/runs/train/exp4/weights/new_slugs_yolov5s.pt"
        #'/home/nabil/vision_ws/src/pipelinev5/src/yolov5/runs-20220423T095241Z-001/runs/train/exp5/weights/new_slugs_yolov5m.pt'
    )

    classes = [
        "spexal",
        "rhu",
        "peach",
        "car",
        "motorcycle",
        "airplane",
        "bus",
        "train",
        "truck",
        "boat",
        "traffic light",
        "fire hydrant",
        "stop sign",
        "parking meter",
        "bench",
        "slug",
    ]
    # classes = [
    #     "spexal",
    #     "rhu",
    #     "peach",
    #     "car",
    #     "motorcycle",
    #     "airplane",
    #     "bus",
    #     "train",
    #     "truck",
    #     "boat",
    #     "traffic light",
    #     "fire hydrant",
    #     "stop sign",
    #     "parking meter",
    #     "ketchup",
    #     "slug",
    # ]

    rospy.init_node("detection_node", anonymous=False)

    inferenece = Inference(iou, conf, model_path, img_size, classes)

    rate = rospy.Rate(10)
    ctrl_c = False

    def shutdownhook():
        # works better than the rospy.is_shut_down()
        inferenece.clean_up()
        rospy.loginfo("shutdown time!")
        ctrl_c = True

    rospy.on_shutdown(shutdownhook)

    while not ctrl_c:
        rate.sleep()


if __name__ == "__main__":
    main()
    rospy.loginfo("testing after main")
