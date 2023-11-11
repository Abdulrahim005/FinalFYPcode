#include "ros.h"
#include <geometry_msgs/Twist.h>
#include <geometry_msgs/Quaternion.h>
#include "I2Cdev.h"
#include "MPU6050_6Axis_MotionApps612.h"
#include "Wire.h"

MPU6050 mpu;

#define INTERRUPT_PIN 2  // use pin 2 on Arduino Uno & most boards

// MPU control/status vars
bool dmpReady = false;  // set true if DMP init was successful
uint8_t mpuIntStatus;   // holds actual interrupt status byte from MPU
uint8_t devStatus;      // return status after each device operation (0 = success, !0 = error)
uint16_t packetSize;    // expected DMP packet size (default is 42 bytes)
uint16_t fifoCount;     // count of all bytes currently in FIFO
uint8_t fifoBuffer[64]; // FIFO storage buffer

// orientation/motion vars
Quaternion q;           // [w, x, y, z]         quaternion container

volatile bool mpuInterrupt = false;     // indicates whether MPU interrupt pin has gone high
void dmpDataReady() {
  mpuInterrupt = true;
}

float wheel1;
float wheel2;
float wheel1_pwm;
float wheel2_pwm;
float demandx;
float demandz;
float speed_act_left; // actual left wheel speed in m/s
float speed_act_right; // actual right wheel speed in m/s

int motor1A = 6, motor1B = 5;
int motor2A = 10, motor2B = 9;


// ** ROS callback & subscriber **
void velCallback(  const geometry_msgs::Twist& vel)
{
  demandx = vel.linear.x; // m/s
  demandz = vel.angular.z; // rad/s
}

ros::NodeHandle nh;
geometry_msgs::Quaternion quat_msg;
ros::Publisher quat_publisher("imu_quaternion", &quat_msg);
ros::Subscriber<geometry_msgs::Twist> sub("cmd_vel_arduino" , velCallback);     //create a subscriber for ROS cmd_vel topic

// ** Setup **
void setup() {

  Wire.begin();
  Wire.setClock(400000); // 400kHz I2C clock. Comment this line if having compilation difficulties
  mpu.initialize();
  pinMode(INTERRUPT_PIN, INPUT);
  devStatus = mpu.dmpInitialize();

  // supply your own gyro offsets here, scaled for min sensitivity
  mpu.setXGyroOffset(38);
  mpu.setYGyroOffset(-76);
  mpu.setZGyroOffset(14);
  mpu.setXAccelOffset(2497);
  mpu.setYAccelOffset(1271);
  mpu.setZAccelOffset(1545);

  // make sure it worked (returns 0 if so)
  if (devStatus == 0) {
    // Calibration Time: generate offsets and calibrate our MPU6050
    mpu.CalibrateAccel(6);
    mpu.CalibrateGyro(6);
    mpu.setDMPEnabled(true);

    attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), dmpDataReady, RISING);
    mpuIntStatus = mpu.getIntStatus();
    dmpReady = true;

    // get expected DMP packet size for later comparison
    packetSize = mpu.dmpGetFIFOPacketSize();
  }

  //  nh.getHardware()->setBaud(115200);/
  nh.initNode();              // init ROS
  nh.subscribe(sub);          // subscribe to cmd_vel
  nh.advertise(quat_publisher); // publisher for yaw angle


  pinMode(motor1A, OUTPUT);     // motor PWM pins
  pinMode(motor1B, OUTPUT);
  pinMode(motor2A, OUTPUT);
  pinMode(motor2B, OUTPUT);

}
void loop() {
  nh.spinOnce();        // make sure we listen for ROS messages and activate the callback if there is one

  // if programming failed, don't try to do anything
  if (dmpReady) {
    // read a packet from FIFO
    if (mpu.dmpGetCurrentFIFOPacket(fifoBuffer)) { // Get the Latest packet
      nh.spinOnce();        // make sure we listen for ROS messages and activate the callback if there is one
      mpu.dmpGetQuaternion(&q, fifoBuffer);
      nh.spinOnce();        // make sure we listen for ROS messages and activate the callback if there is one
      quat_msg.x = q.x;
      quat_msg.y = q.y;
      quat_msg.z = q.z;
      quat_msg.w = q.w;
      quat_publisher.publish(&quat_msg);
    }
  }

  nh.spinOnce();        // make sure we listen for ROS messages and activate the callback if there is one

  // work out the two values for differential drive of each wheel
  wheel1 = demandx + (demandz);
  wheel2 = demandx - (demandz);
  wheel1 = constrain(wheel1, -0.5, 0.5); //0.5(or -0.5)m/s calculated max speed of the motor
  wheel2 = constrain(wheel2, -0.5, 0.5);
  // mapping from m/s to pwm
  wheel1_pwm = (abs(wheel1) * 180) / 0.5;
  wheel2_pwm = (abs(wheel2) * 180) / 0.5;
  // drive motors
  if (wheel1 > 0) {
    analogWrite(motor1A, wheel1_pwm);
    analogWrite(motor1B, 0);
    // analogWrite(3, wheel1_pwm); TO BE ADDED IF WE NEED AN ARDUINO PIN FOR EACH MOTOR
    //analogWrite(5, 0);
  }
  else if (wheel1 < 0) {
    analogWrite(motor1B, wheel1_pwm);
    analogWrite(motor1A, 0);
  }
  else {
    analogWrite(motor1A, 0);
    analogWrite(motor1B, 0);
  }
  // other motor
  if (wheel2 < 0) {
    analogWrite(motor2B, wheel2_pwm);
    analogWrite(motor2A, 0);
  }
  else if (wheel2 > -0) {
    analogWrite(motor2A, wheel2_pwm);
    analogWrite(motor2B, 0);
  }
  else {
    analogWrite(motor2A, 0);
    analogWrite(motor2B, 0);
  }

  nh.spinOnce();        // make sure we listen for ROS messages and activate the callback if there is one
} // end of main loop
