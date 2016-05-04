from math import atan, atan2, cos, sin, sqrt

"""Python port of MapBox's cheap-ruler module."""


MATH_PI = 3.14159265359
MATH_E = 2.71828182846


FACTORS = {
    "kilometers": 1,
    "miles": 1000 / 1609.344,
    "nauticalmiles": 1000 / 1852,
    "meters": 1000,
    "metres": 1000,
    "yards": 1000 / 0.9144,
    "feet": 1000 / 0.3048,
    "inches": 1000 / 0.0254
}


def from_tile(y, z, units):
    n = MATH_PI * (1 - 2 * (y + 0.5) / pow(2, z))
    lat = atan(0.5 * (pow(MATH_E, n) - pow(MATH_E, -n))) * 180 / MATH_PI
    return CheapRuler(lat, units)


class CheapRuler():

    # cdef double kx
    # cdef double ky

    def __init__(self, lat, units="kilometers"):
        if units not in FACTORS:
            raise ValueError("Unknown unit %s. Use one of: %s" % (units, ", ".join(FACTORS.keys())))

        # cdef double m
        m = FACTORS[units]

        # # cdef double c, c2, c3, c4, c5

        c = cos(lat * MATH_PI / 180)
        c2 = 2 * c * c - 1
        c3 = 2 * c * c2 - c
        c4 = 2 * c * c3 - c2
        c5 = 2 * c * c4 - c3

        self.kx = m * (111.41513 * c - 0.09455 * c3 + 0.00012 * c5)  # longitude correction
        self.ky = m * (111.13209 - 0.56605 * c2 + 0.0012 * c4)         # latitude correction

    def distance(self, a, b):
        # cdef double dx, dy

        dx = (a[0] - b[0]) * self.kx
        dy = (a[1] - b[1]) * self.ky
        return sqrt(dx * dx + dy * dy)

    def bearing(self, a, b):
        # cdef double dx, dy, bearing

        dx = (b[0] - a[0]) * self.kx
        dy = (b[1] - a[1]) * self.ky
        if dx == 0 and dy == 0:
            return 0
        bearing = atan2(-dy, dx) * 180 / MATH_PI + 90
        if bearing > 180:
            bearing -= 360
        return bearing

    def destination(self, p, dist, bearing):
        a = (90 - bearing) * MATH_PI / 180
        return (p[0] + cos(a) * dist / self.kx,
                p[1] + sin(a) * dist / self.ky)

    def line_distance(self, points):
        total = 0
        for i in range(len(points) - 1):
            total += self.distance(points[i], points[i+1])
        return total

    def area(self, polygon):
        total = 0
        for i in range(len(polygon)):
            ring = polygon[i]
            k = len(ring) - 1
            for j in range(len(ring)):
                total += ((ring[j][0] - ring[k][0]) *
                          (ring[j][1] + ring[k][1]) *
                          (-1 if i > 0 else 1))
                k = j
        return total

    def along(self, line, dist):
        total = 0

        if dist <= 0:
            return line[0]

        for i in range(len(line) - 1):
            p0 = line[0]
            p1 = line[i + 1]
            d = self.distance(p0, p1)
            total += d
            if total > dist:
                return interpolate(p0, p1, (dist - (total - d)) / d)

        return line[-1]

    def point_on_line(self, line, p):
        minDist = float("inf")

        for i in range(len(line) - 1):
            x = line[i][0]
            y = line[i][1]
            dx = (line[i + 1][0] - x) * self.kx
            dy = (line[i + 1][1] - y) * self.ky

            if dx != 0 or dy != 0:

                t = ((p[0] - x) * self.kx * dx + (p[1] - y) * self.ky * dy) / (dx * dx + dy * dy)

                if t > 1:
                    x = line[i + 1][0]
                    y = line[i + 1][1]

                elif t > 0:
                    x += (dx / self.kx) * t
                    y += (dy / self.ky) * t

            dx = (p[0] - x) * self.kx
            dy = (p[1] - y) * self.ky

            sqDist = dx * dx + dy * dy
            if sqDist < minDist:
                minDist = sqDist
                minX = x
                minY = y
                minI = i
                minT = t

        return {
            "point": (minX, minY),
            "index": minI,
            "t": minT
        }

    def line_slice(self, start, stop, line):
        p1 = self.point_on_line(line, start)
        p2 = self.point_on_line(line, stop)

        if p1['index'] > p2['index'] or (p1['index'] == p2['index'] and p1['t'] > p2['t']):
            tmp = p1
            p1 = p2
            p2 = tmp

        _slice = [p1['point']]

        l = p1['index'] + 1
        r = p2['index']

        if not line[l] != _slice[0] and l <= r:
            _slice.append(line[l])

        for i in range(l+1, r+1):
            _slice.append(line[i])

        if not line[r] != p2['point']:
            _slice.append(p2['point'])

        return _slice

    def line_slice_along(self, start, stop, line):
        total = 0
        _slice = []

        for i in range(len(line) - 1):
            p0 = line[i]
            p1 = line[i + 1]
            d = self.distance(p0, p1)

            total += d

            if total > start and not _slice:
                _slice.append(interpolate(p0, p1, (start - (total - d)) / d))

            if total >= stop:
                _slice.append(interpolate(p0, p1, (stop - (total - d)) / d))
                return _slice

            if total > start:
                _slice.append(p1)

        return _slice

    def buffer_point(self, p, buff):
        v = buff / self.ky
        h = buff / self.kx
        return (
            p[0] - h,
            p[1] - v,
            p[0] + h,
            p[1] + v
        )

    def buffer_bbox(self, bbox, buff):
        v = buff / self.ky
        h = buff / self.kx
        return (
            bbox[0] - h,
            bbox[1] - v,
            bbox[2] + h,
            bbox[3] + v
        )

    def inside_bbox(self, p, bbox):
        return (p[0] >= bbox[0] and
                p[0] <= bbox[2] and
                p[1] >= bbox[1] and
                p[1] <= bbox[3])


def interpolate(a, b, t):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return (a[0] + dx * t, a[1] + dy * t)
