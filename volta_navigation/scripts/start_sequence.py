#!/usr/bin/python

import rospy
import tf
import math
from geometry_msgs.msg import Twist, Vector3
import actionlib
from actionlib_msgs.msg import GoalStatus
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from volta_navigation.srv import Goal, GoalResponse
from sensor_msgs.msg import LaserScan
from visualization_msgs.msg import Marker

class Sequence:

    def __init__(self):
        rospy.init_node("sequence")

        self.goal = [0,0]
        self.yaw = 0
        self.threshold = 0.2

        rospy.Service('goal_server', Goal, self.handle_goal)

        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.Subscriber('/scan_filtered', LaserScan, self.laser_callback)

        self.scan_data = []

        self.lidar_safe = True

        self.goal = []

        self.marker_pub = rospy.Publisher('goal_server_goal', Marker , queue_size=1, latch=True)
        self.marker_pub2 = rospy.Publisher('recieved_goal', Marker , queue_size=1, latch=True)

        self.vel_pub = rospy.Publisher('/goal_server_vel/cmd_vel', Twist, queue_size=1, latch=True)



        '''

        X and Y limits that cover the arena
        
        '''
        x_max =  1.5
        x_min = -0.83
        
        y_max =  1.19
        y_min = -1.29

        '''

        X and Y offsets to specify the soft limits 

        '''

        x_max_offset =  0.3
        x_min_offset =  0.3

        y_max_offset =  0.3
        y_min_offset =  0.3

        '''
        Soft limits
        '''

        self.soft_xmax = x_max - x_max_offset
        self.soft_xmin = x_min + x_min_offset

        self.soft_ymax = y_max - y_max_offset
        self.soft_ymin = y_min + y_min_offset

        factor = 0.5

        self.corner_xmax = x_max - x_max_offset * factor
        self.corner_xmin = x_min + x_min_offset * factor

        self.corner_ymax = y_max - y_max_offset * factor
        self.corner_ymin = y_min + y_min_offset * factor


        # self.x_max =  1.499 - 0.10
        # self.x_min = -1.187 + 0.20
        
        # self.y_max =  1.292 - 0.20
        # self.y_min = -1.325 + 0.20


        
        rospy.spin()        

    def marker_publish(self,pub):
        m = Marker()
        m.action = Marker.ADD
        m.header.frame_id = 'map'
        m.header.stamp = rospy.Time(0)
        m.ns = 'marker_test_%d' % Marker.ARROW
        m.id = 0
        m.type = Marker.ARROW
        m.pose.position.x = self.goal[0]
        m.pose.position.y = self.goal[1]
        m.pose.orientation.z = math.sin(self.yaw/2)
        m.pose.orientation.w = math.cos(self.yaw/2)
        m.scale = Vector3(0.3,0.06,0.06)
        m.color.r = 0
        m.color.g = 0
        m.color.b = 0
        m.color.a = 1.0

        if pub==1:
            m.color.b = 1
            self.marker_pub.publish(m)
        if pub==2:
            m.color.r = 1
            self.marker_pub2.publish(m)

    def laser_callback(self, msg):

        # min_dist1 = min(msg.ranges[0:360])
        # min_dist2 = min(msg.ranges[1080:1439])

        # min_dist1 = min(msg.ranges[0:360])
        # min_dist2 = min(msg.ranges[1080:1439])


        min_dist = min(msg.ranges[600:840])
           
        self.lidar_safe = True if min_dist>0.3 else False
        # if self.lidar_safe:
        #     print("far",min_dist)
            
        # else:
        #     print("Too close",min_dist)




    def get_velocity(self,distance):

        return 1/(1 + math.exp(-distance))

    def get_orientation(self):

        x, y = self.goal

        if x > self.corner_xmax :

            self.yaw = 0

            if y > self.corner_ymax :

                self.yaw = math.pi / 4

            elif y < self.corner_ymin :

                self.yaw = - math.pi / 4

        elif x < self.corner_xmin :

            self.yaw = math.pi

            if y > self.corner_ymax :

                self.yaw =  3 * math.pi / 4

            elif y < self.corner_ymin :

                self.yaw = - 3 *  math.pi / 4

        else:

            if y > self.corner_ymax :

                self.yaw = math.pi / 2

            elif y < self.corner_ymin :

                self.yaw = - math.pi / 2


    def plan_to_goal(self):

        new_goal_x , new_goal_y = self.goal[0] - self.threshold * math.cos(self.yaw) , self.goal[1] - self.threshold * math.sin(self.yaw)
        
        return new_goal_x , new_goal_y
    
    def approach_goal(self):

        listener = tf.TransformListener()
        while True:
            try:
                (trans,rot) = listener.lookupTransform('/map', '/base_link', rospy.Time(0))
                break
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                continue

        init_x, init_y = trans[0], trans[1]

        # threshold = 0.5

        threshold = math.sqrt( (init_x - self.goal[0] )**2 + (init_y - self.goal[1] )**2  )
        # print(threshold)

        
        distance_moved = 0

        rate = rospy.Rate(10.0)

        while  not rospy.is_shutdown() and  distance_moved <= threshold and self.lidar_safe:
            try:
                (trans,rot) = listener.lookupTransform('/map', '/base_link', rospy.Time(0))
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                continue

            cur_x, cur_y = trans[0], trans[1]
        
            linear = 0.2 * self.get_velocity(threshold - distance_moved)
            cmd = Twist()
            cmd.linear.x = linear
            self.vel_pub.publish(cmd)

            distance_moved= math.sqrt( (init_x-cur_x)**2 + (init_y-cur_y)**2 )
            # print("Curr:",[cur_x,cur_y])
            # print(distance_moved)

            rate.sleep()

        cmd = Twist()
        cmd.linear.x = 0

        self.vel_pub.publish(cmd)

        # print("Final",cur_x,cur_y)

    def retreat(self, threshold = 0.6):

        listener = tf.TransformListener()
        while True:
            try:
                (trans,rot) = listener.lookupTransform('/map', '/base_link', rospy.Time(0))
                break
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                continue

        init_x, init_y = trans[0], trans[1]

        # threshold = math.sqrt( (init_x - self.goal[0] )**2 + (init_y - self.goal[1] )**2  )
        threshold = 0.5     
        
        distance_moved = 0

        rate = rospy.Rate(10.0)

        while  not rospy.is_shutdown() and  distance_moved <= threshold :
            try:
                (trans,rot) = listener.lookupTransform('/map', '/base_link', rospy.Time(0))
            except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
                continue

            cur_x, cur_y = trans[0], trans[1]
        
            linear = -0.2 * self.get_velocity(threshold - distance_moved)
            cmd = Twist()
            cmd.linear.x = linear
            self.vel_pub.publish(cmd)

            distance_moved= math.sqrt( (init_x-cur_x)**2 + (init_y-cur_y)**2 )
            # print("Curr:",[cur_x,cur_y])
            # print(distance_moved)

            rate.sleep()

        cmd = Twist()
        cmd.linear.x = 0

        self.vel_pub.publish(cmd)

        # print("Final",cur_x,cur_y)
    
    def movebase_client(self,x,y):

        
        print "\n[move_base] Waiting for MoveBase server \n"
        self.client.wait_for_server()
        print "\n[move_base] MoveBase Server Up!\n"
        print "\n[move_base] Sending MoveBase Goal :[ %s , %s , %s] \n"%(x, y, self.yaw)

        move_base_goal = MoveBaseGoal()
        move_base_goal.target_pose.header.frame_id = "map"
        move_base_goal.target_pose.header.stamp = rospy.Time.now()
        move_base_goal.target_pose.pose.position.x = x
        move_base_goal.target_pose.pose.position.y = y

        #  (0, 0, sin(theta/2), cos(theta/2)).
        move_base_goal.target_pose.pose.orientation.z =  math.sin(self.yaw/2)
        move_base_goal.target_pose.pose.orientation.w =  math.cos(self.yaw/2)
        

        self.client.send_goal(move_base_goal)

        finished_within_time = self.client.wait_for_result()

        state = self.client.get_state()

        return state

        #  self.client.get_result()


    def isValid(self):
        x,y = self.goal
        if ( x <= self.soft_xmax and x >= self.soft_xmin ) and ( y <= self.soft_ymax and y >= self.soft_ymin ) :
            return True

        return False
        

    def handle_goal(self, req):


        print "\n[goal_server]: Recieved Goal (X,Y) -> ( %s,%s ) \n " %(req.x,req.y)

        self.goal = [req.x, req.y]

        self.yaw = 0
        self.get_orientation()
        self.marker_publish(2)

        valid = True
        while(not self.isValid()):
            if valid == True:
                print "\n[goal_server]: Goal outside bounds \n"
                valid = False
            self.generate_new_goal()

        print "\n[goal_server] New Safe Goal1 (X,Y): %s Yaw: %s \n"%(self.goal,self.yaw)

        if not valid:
            inter_x, inter_y = self.plan_to_goal()
            print "\n[goal_server] New Safe Goal2 (X,Y): %s Yaw: %s \n"%(self.goal,self.yaw)
        else:
            inter_x, inter_y = self.goal

        self.marker_publish(1)

        state = self.movebase_client(inter_x, inter_y)

        if state!= GoalStatus.SUCCEEDED:
            print "\n[move_base] Goal Aborted. Trying again \n"
            state = self.movebase_client(inter_x, inter_y)

        if state!= GoalStatus.SUCCEEDED:
            print "\n[goal_server] Goal Aborted Again. Aborting Attempt. "
            print(raw_input("[goal_server]: Teleop to desired goal. Enter (Y/N) to end TASK : ") )
            print "\n[goal_server] TASK COMPLETED \n"
            return 1

        if state== GoalStatus.SUCCEEDED:
            print "\n[move_base] Goal Reached \n"

        if not valid:

            print "\n[goal_server] Starting Approach \n"

            self.approach_goal()

            print "\n[goal_server] End of Approach. Have some Candy!  \n"
            
            rospy.sleep(5)

            print "\n[goal_server] Starting Retreat  \n"

            self.retreat()

            print "\n[goal_server] End of Retreat  \n"

            print "\n[goal_server] TASK COMPLETED \n"

            return 0

        else:

            print "\n[goal_server] TASK COMPLETED \n"
            
            return 0

    
    def stop(self):
        cmd = Twist()
        cmd.linear.x = 0
        self.vel_pub.publish(cmd)

    
    def generate_new_goal(self, step = 0.1):

        # x0,y0 = [0,0]
        # x1,y1 = self.goal

        # angle = math.atan2( (y1-y0),(x1-x0) )
        # dist = math.sqrt( (x1-x0)**2 + (y1-y0)**2 )
        # x_new, y_new = x0 + (dist - step)*math.cos(angle) ,y0 + (dist - step)*math.sin(angle)   
        
        # self.goal = [x_new, y_new]

        x,y = self.goal
        
        if x > self.soft_xmax :
            x = self.soft_xmax
        elif x < self.soft_xmin :
            x = self.soft_xmin

        if y > self.soft_ymax :
            y = self.soft_ymax
        elif y < self.soft_ymin :
            y = self.soft_ymin
        
        self.goal = [ x, y ]

if __name__=="__main__":
    Seq1 = Sequence()

