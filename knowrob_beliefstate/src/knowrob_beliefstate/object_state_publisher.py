#!/usr/bin/env python
import rospy
import tf
from collections import defaultdict

from geometry_msgs.msg._Point import Point
from geometry_msgs.msg._Pose import Pose
from geometry_msgs.msg._Quaternion import Quaternion
from knowrob_beliefstate.srv._DirtyObject import DirtyObject, DirtyObjectResponse, DirtyObjectRequest
from std_msgs.msg._ColorRGBA import ColorRGBA
from std_srvs.srv._SetBool import SetBool, SetBoolResponse
from std_srvs.srv._Trigger import Trigger, TriggerResponse
from visualization_msgs.msg._Marker import Marker
from json_prolog import json_prolog


class ThorinObject(object):
    def __init__(self):
        self.transform = None
        self.mesh_path = ''
        self.color = ColorRGBA()

    def update_color(self, r, g, b, a):
        self.color = ColorRGBA()
        self.color.r = float(r)
        self.color.g = float(g)
        self.color.b = float(b)
        self.color.a = float(a)

    def update_transform(self, ref_frame, object_name, translation, rotation):
        self.ref_frame = str(ref_frame)
        self.object_name = str(object_name)
        # self.transform = [self.ref_frame, self.object_name, translation, rotation]
        self.transform = [self.ref_frame, self.get_short_name(), translation, rotation]

    def get_marker(self):
        marker = Marker()
        marker.header.frame_id = self.ref_frame
        marker.type = marker.MESH_RESOURCE
        marker.action = Marker.ADD
        marker.id = 1337
        marker.ns = self.get_short_name()
        marker.color = self.color
        marker.scale.x = 1
        marker.scale.y = 1
        marker.scale.z = 1
        marker.frame_locked = True
        marker.pose.position = Point(*self.transform[-2])
        marker.pose.orientation = Quaternion(*self.transform[-1])
        marker.mesh_resource = self.mesh_path[:-4] + '.dae'
        return marker

    def get_short_name(self):
        return self.object_name.split('#')[1]


class ObjectStatePublisher(object):
    def __init__(self, tf_frequency):
        rospy.wait_for_service('/json_prolog/query')
        self.tf_frequency = tf_frequency
        self.prolog = json_prolog.Prolog()
        self.tf_broadcaster = tf.TransformBroadcaster()
        self.marker_publisher = rospy.Publisher('/visualization_marker', Marker, queue_size=10)
        self.dirty_object_srv = rospy.Service('~mark_dirty_object', DirtyObject, self.dirty_cb)
        self.objects = defaultdict(lambda: ThorinObject())
        # self.test_srv = rospy.Service('~asdf', SetBool, self.test_srv_cb)

    # for testing purpose, can be deleted...
    # def test_srv_cb(self, srv_msg):
    #     objectid = 'http://knowrob.org/kb/thorin_simulation.owl#PorscheBody1'
    #     object_type = 'http://knowrob.org/kb/knowrob_assembly.owl#BasicMechanicalPart'
    #     new_transform = ['left_gripper_tool_frame', objectid, [0, 0, 0], [0, 0, 0, 1]]
    #     q = "assert_object_at_location('{}', '{}', {})".format(object_type, objectid, new_transform)
    #     print('test queue: {}'.format(q))
    #     sol = self.prolog_query(q)
    #     for s in sol:
    #         print(s)
    #     print('---------------------------------------------------')
    #     asdf = DirtyObjectRequest()
    #     asdf.object_ids = [objectid]
    #     self.dirty_cb(asdf)
    #     return SetBoolResponse()

    def dirty_cb(self, srv_msg):
        r = DirtyObjectResponse()
        r.error_code = r.SUCCESS
        for object_id in srv_msg.object_ids:
            if not self.load_object(object_id):
                r.error_code = r.UNKNOWN_OBJECT
            else:
                rospy.loginfo("object '{}' updated".format(object_id))
        self.publish_object_frames()
        self.publish_object_markers()
        return r

    def prolog_query(self, q):
        query = self.prolog.query(q)
        solutions = [x for x in query.solutions()]
        if len(solutions) > 1:
            rospy.logwarn('{} returned more than one result'.format(q))
        elif len(solutions) == 0:
            rospy.logwarn('{} returned nothing'.format(q))
        query.finish()
        return solutions

    def load_objects(self):
        self.load_object_ids()
        for object_id in self.objects.keys():
            self.load_object(object_id)
        self.publish_object_frames()
        self.publish_object_markers()

    def load_object(self, object_id):
        if object_id not in self.objects.keys():
            self.load_object_ids()
        if object_id in self.objects.keys():
            self.load_object_color(object_id)
            self.load_object_mesh(object_id)
            self.load_object_transform(object_id)
            return True
        rospy.logwarn("object with id:'{}' not found in database".format(object_id))
        return False

    def load_object_ids(self):
        q = 'get_known_object_ids(A)'
        solutions = self.prolog_query(q)
        for object_id in solutions[0]['A']:
            #TODO: remove this dirty hack when the test objects are removed from the knowledge base
            if 'Test' not in object_id:
                self.objects[object_id] = ThorinObject()
        rospy.loginfo('Loaded object ids: {}'.format(self.objects.keys()))

    def load_object_color(self, object_id):
        q = "get_object_color('{}', A)".format(object_id)
        solutions = self.prolog_query(q)
        self.objects[object_id].update_color(*solutions[0]['A'])
        rospy.logdebug("'{}' has color: {}".format(object_id, self.objects[object_id].color))

    def load_object_transform(self, object_id):
        q = "get_object_transform('{}', A)".format(object_id)
        solutions = self.prolog_query(q)
        self.objects[object_id].update_transform(*solutions[0]['A'])
        rospy.logdebug("'{}' has transform: {}".format(object_id, self.objects[object_id].transform))

    def load_object_mesh(self, object_id):
        q = "get_object_mesh_path('{}', A)".format(object_id)
        solutions = self.prolog_query(q)
        self.objects[object_id].mesh_path = str(solutions[0]['A'])
        rospy.logdebug("'{}' has mesh path: {}".format(object_id, self.objects[object_id].mesh_path))

    def publish_object_markers(self):
        for object_id, v in self.objects.items():
            self.marker_publisher.publish(v.get_marker())

    def publish_object_frames(self):
        for object_id, thorin_object in self.objects.items():
            ref_frame, object_frame, translation, rotation = thorin_object.transform
            # print(object_frame)
            self.tf_broadcaster.sendTransform(translation,
                                              rotation,
                                              rospy.Time.now(),
                                              object_frame,
                                              ref_frame)

    def loop(self):
        self.load_objects()
        rate = rospy.Rate(self.tf_frequency)
        while not rospy.is_shutdown():
            self.publish_object_frames()
            rate.sleep()


if __name__ == '__main__':
    rospy.init_node('object_state_publisher')
    hz = rospy.get_param('~hz', default='1')
    object_state_publisher = ObjectStatePublisher(int(hz))
    object_state_publisher.loop()
