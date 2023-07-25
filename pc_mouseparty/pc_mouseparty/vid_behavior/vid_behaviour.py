import os
import re
import operator
import traceback
import warnings
import pathlib
import h5py
import math
import numpy as np
import pandas as pd
import moviepy.editor as mpy
from moviepy.editor import *
from medpc2excel.medpc_read import medpc_read
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from collections import defaultdict


def get_mouse_sides(locations):
    '''
    takes in locations
    returns (left mouse index, right mouse index)
    '''
    if locations[0,1,0,0] > locations[0,1,0,1]:
        # if mouse 0 has a greater starting x value for its nose,
        # then it is the right mouse
        return (1, 0)
    else:
        return (0, 1)
    

def smooth_diff(node_loc, win=25, poly=3):
    """
    node_loc is a [frames, 2] array

    win defines the window to smooth over

    poly defines the order of the polynomial
    to fit with
    """
    node_loc_vel = np.zeros_like(node_loc)

    for c in range(node_loc.shape[-1]):
        node_loc_vel[:, c] = savgol_filter(node_loc[:, c], win, poly, deriv=1)

    node_vel = np.linalg.norm(node_loc_vel,axis=1)

    return node_vel


def smooth_diff_one_dim(node_loc, win=25, poly=3):
    """
    node_loc is a [frames] array

    win defines the window to smooth over

    poly defines the order of the polynomial
    to fit with

    """
    node_loc_vel = np.zeros_like(node_loc)

    node_loc_vel[:] = savgol_filter(node_loc[:], win, poly, deriv=1)

    return node_loc_vel


def get_distances_between_mice(locations, node_index):
    # confirmed does what i want it to
    """
    takes in locations and node index
    returns a list of distances between the nodes of the two mice
    """
    c_list = []
    left_mouse, right_mouse = get_mouse_sides(locations)
    for i in range(len(locations)):

        (x1, y1) = (locations[i, node_index, 0, left_mouse],
                    locations[i, node_index, 1, left_mouse])
        # x , y coordinate of nose for mouse 1
        (x2, y2) = (locations[i, node_index, 0, right_mouse],
                    locations[i, node_index, 1, right_mouse])
        # x and y coordinate of nose of mouse 2
        # solve for c using pythagroean theory
        a2 = (x1 - x2) ** 2
        b2 = (y1 - y2) ** 2
        c = math.sqrt(a2 + b2)
        if x1 > x2:
            c_list.append(-1*c)
        else:
            c_list.append(c)
    return c_list


def get_distances_between_nodes(locations, node_index1, node_index2):
    # CONFIRMED THAT IT WORKS in terms of doing the math by hand
    """
    takes in locations and node indexes of the two body parts you want
    within mice distances for

    returns nested lists, list[0] is the distances within track1
    list[1] is the distances within track2

    """
    c_list = []
    m1_c_list = []
    m2_c_list = []
    left_mouse, right_mouse = get_mouse_sides(locations)
    for i in range(len(locations)):
        x1, y1 = locations[i, node_index1, 0, 0], locations[i, node_index1, 1, left_mouse]
        # x , y coordinate of node 1 for mouse 1
        x2, y2 = locations[i, node_index2, 0, 0], locations[i, node_index2, 1, left_mouse]
        # x, y coordiantes of node 2 for mouse 1
        x3, y3 = locations[i, node_index1, 0, 1], locations[i, node_index1, 1, right_mouse]
        # x and y coordinate of node 1 of mouse 2
        x4, y4 = locations[i, node_index2, 0, 1], locations[i, node_index2, 1, right_mouse]
        # solve for c using pythagroean theory
        a2 = (x1 - x2) ** 2
        b2 = (y1 - y2) ** 2
        a2_m2 = (x3 - x4) ** 2
        b2_m2 = (y3 - y4) ** 2
        c2 = math.sqrt(a2_m2 + b2_m2)
        c1 = math.sqrt(a2 + b2)
        m1_c_list.append(c1)
        m2_c_list.append(c2)
    c_list.append(m1_c_list)
    c_list.append(m2_c_list)
    return c_list


def get_speeds(locations, node_index):

    node_loc_1 = locations[:,node_index,:,0]
    # node loc (x,y) of node of mouse 1
    node_loc_2 = locations[:,node_index,:,1]
    # x,y's of node of mouse 2
    m1_vel = smooth_diff(node_loc_1)
    m2_vel = smooth_diff(node_loc_2)
    velocities = [m1_vel,m2_vel]
    return velocities


def get_velocities(locations, node_index):

    left_mouse, right_mouse = get_mouse_sides(locations)
    node_loc_left = locations[:, node_index, 0, left_mouse]
    # node loc (x,y) of node of mouse 1
    node_loc_right = (locations[:, node_index, 0, right_mouse]) * (-1)
    # x,y's of node of mouse 2

    m1_vel = smooth_diff_one_dim(node_loc_left)
    m2_vel = smooth_diff_one_dim(node_loc_right)
    velocities = [m1_vel, m2_vel]
    return velocities


def get_angles(locations, node_index_1, node_index_2, node_index_3):
    """
    takes in locations and three nodes, calculates angle between the
    three points
    with the second node being the center point
    i.e. node_1 = nose , node_2 = ear , node_3 = thorax
    returns [[list of angles for mouse 1][list of angles for mouse 2]]
    """
    angles_all_mice = []
    frame, nodes, axes, mice = locations.shape

    for mouse in range(mice):
        angles = []
        for i in range(len(locations)):
            a = np.array([locations[i, node_index_1, 0, mouse], locations[i, node_index_1, 1, mouse]])
            b = np.array([locations[i, node_index_2, 0, mouse], locations[i, node_index_2, 1, mouse]])
            c = np.array([locations[i, node_index_3, 0, mouse], locations[i, node_index_3, 1, mouse]])
            ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0]))
            if ang < 0:
                angles.append(ang + 360)
            else:
                angles.append(ang)
        angles_all_mice.append(angles)
    return angles_all_mice


def cluster_dic(labels):
    """
    takes in a list of labels (hdbscan labels)
    and returns a dictionary {cluster:[list of frames]}
    """
    clusters = {}
    print(labels)
    # if a cluster key already exists in the dictionary, append its value
    # (list) with the new frame (i)
    for i in range(len(labels)):
        if labels[i] in clusters:
            temp_val = clusters[labels[i]]
            temp_val.append(i)
            clusters[labels[i]] = temp_val
        # if the cluser does not have a unique key yet, create one, who
        else:
            clusters[labels[i]] = [i]
    return clusters


# create temp list of frames for the range you are on so you only have to open
# each video once
def make_clip(list_of_frames, framedic):
    vid_to_frames_dict = {}
    frames = []
    # video name , value list of frame from that video in this cluster
    # string : list of integers
    for frame in list_of_frames:
        for key, value in framedic.items():
            start = value[0]
            stop = value[1]
            if frame in range(start, stop):
                if key in vid_to_frames_dict:
                    vid_to_frames_dict[key].append(frame)
                else:
                    vid_to_frames_dict[key] = [frame]
                break
    for key in vid_to_frames_dict:
        vid = VideoFileClip(key)
        for frame in vid_to_frames_dict[key]:
            start_of_vid_frame = framedic[key][0]
            frames.append(vid.get_frame((frame - start_of_vid_frame)/30))
        vid.close()

    clip = mpy.ImageSequenceClip(frames, fps=30)
    return clip


def contact(node_array_m1, node_array_m2, epsilon):
    """
    given two node location arrays for mouse 1 and mouse 2 in one dimension,
    nose nodes recommended for tube test in the x dimension,
    returns a boolean of the number of frames of the trial/video
    true = contact, false = no contact
    epsilon = threshold for closeness that defines a contact
    """
    contact_array = [0] * len(node_array_m1)
    # get left mouse
    # left of screen in 0 on x axis
    if node_array_m1[0] > node_array_m2[0]:
        left_array = node_array_m2
        right_array = node_array_m1
        print('LEFT MOUSE IS MOUSE 2')
    else:
        left_array = node_array_m1
        right_array = node_array_m2
        print('LEFT MOUSE IS MOUSE 1')
    for i in range(len(node_array_m1)):
        if abs(node_array_m1[i] - node_array_m2[i]) < epsilon:
            contact_array[i] = True
        if left_array[i] > right_array[i]:
            contact_array[i] = True
        else:
            contact_array[i] = False
    return contact_array