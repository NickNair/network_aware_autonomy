cmake_minimum_required(VERSION 2.8.3)
project(volta_navigation)

find_package(catkin REQUIRED
    roscpp
    rospy
    std_msgs
    message_runtime
    message_generation
)

add_service_files(
  FILES
  Goal.srv
)

generate_messages( DEPENDENCIES std_msgs )

catkin_package ()


catkin_install_python(PROGRAMS scripts/send_goal_service.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
install(
  DIRECTORY config launch maps
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)