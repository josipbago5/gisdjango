import re
import sys
import math
import os
import time
from copy import deepcopy

from django.core.files.storage import FileSystemStorage

kml_head = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document id="root_doc">\n'''
kml_tail = '''</Document>\n</kml>'''
kml_body_template = '''\t<Placemark>
    <name>Line{}</name>
    <description>{}</description>
    <Point>
        <coordinates>{},{}</coordinates>
    </Point>
    </Placemark>\n'''

polylines_template = '{}_polylines.kml'
eps = 1e-4

# https://en.wikipedia.org/wiki/Decimal_degrees
# 1e-8 degrees = 1.0247cm
conversion_coef = 1.0247
quantum = 1e-7

route_points = []     # ((x, y), d)


def dist(p1, p2, m):
    if p2[0] - p1[0] < eps and p2[1] - p1[1] < eps:
        return math.fabs(p1[0] - m[0]) + math.fabs(p1[1] - m[1])
    return math.fabs((p2[1] - p1[1]) * m[0] - (p2[0] - p1[0]) * m[1] + p2[0] * p1[1] - p2[1] * p1[0]) /\
           math.sqrt((p2[1] - p1[1]) ** 2 + (p2[0] - p1[0]) ** 2)


def to_milimeters(d):
    return d / quantum * conversion_coef


def start_process(route_file, country, MEDIA_ROOT):
    x_max = -sys.float_info.max
    x_min = sys.float_info.max
    y_max = -sys.float_info.max
    y_min = sys.float_info.max
    npoints = 0

    with open(route_file, 'r') as route_file:
        start_time = time.time()
        for line in route_file.readlines():
            if line.startswith('<gx:coord>'):
                tags = line.replace('<gx:coord>', '').replace('</gx:coord>', '').replace('\n', '').split(' ')
                x, y = float(tags[0]), float(tags[1])
                route_points.append([(x, y), -1])

                # find edge route points
                if x > x_max:
                    x_max = deepcopy(x)
                if x < x_min:
                    x_min = deepcopy(x)
                if y > y_max:
                    y_max = deepcopy(y)
                if y < y_min:
                    y_min = deepcopy(y)
        # remove first and last element
        npoints = len(route_points)
        print('Read route file {0} in {1:.2f}s'.format(route_file, time.time() - start_time))

    # select real roads that are (at least partly) inside edge points and store
    selected_roads = [[(None, None), (None, None)]]
    polylines_path = country
    with open(polylines_path, 'r', encoding="utf8") as fpoly:
        start_time = time.time()
        i = 0
        for line in fpoly.readlines():
            if 'LineString' in line:
                stripped = re.sub(r'.*<coordinates>', '', line).split('</coordinates>')[0]
                coordinates = stripped.split(' ')
                for point in coordinates:
                    x, y = float(point.split(',')[0]), float(point.split(',')[1])
                    if x > x_max or x < x_min or y > y_max or y < y_min:
                        continue
                    selected_roads[i][1] = (x, y)
                    selected_roads.append([(x, y), None])
                    i += 1
        selected_roads = selected_roads[1:-1]
        print('Read polylines file {0} in {1:.2f}s'.format(polylines_path, time.time() - start_time))

    # for each route polyline find closest road line
    start_time = time.time()
    for idx, route_point in enumerate(route_points):
        min_dist = sys.float_info.max
        for road in selected_roads:
            d = dist(road[0], road[1], route_point[0])
            if d < min_dist:
                min_dist = d
        # store calculated error to route data
        m, s = divmod(time.time() - start_time, 60)
        h, m = divmod(m, 60)
        print('Calculated {0}/{1} route lines\'s errors in {2:0>2}:{3:0>2}:{4:05.2f} -> {5:.4f}cm'
              .format(idx, npoints, int(h), int(m), s, to_milimeters(min_dist)))
        route_point[1] = to_milimeters(min_dist)

    # generate new KML where you store coordinates and GPS data errors
    kml_body = ''
    print('Generating new .kml with line coordinates and GPS data errors.')
    for idx, point in enumerate(route_points):
        kml_body += kml_body_template.format(idx, point[1], point[0][0], point[0][1])
    kml_string = kml_head + kml_body + kml_tail
    print(kml_string)
    # route_path, _ = os.path.splitext(route_file)
    # gen_route_path = 'gen_' + route_path + '.kml'
    gen_filename = 'gen_file_corrected_route.kml'
    gen_filename_path = MEDIA_ROOT +  '\\' + gen_filename
    # print('Writing result to {}.'.format(gen_route_path))
    with open(gen_filename_path, 'w') as f:
        f.write(kml_string)
        #fs = FileSystemStorage()
        #filename = fs.save(gen_filename, file)
    return gen_filename_path, gen_filename
