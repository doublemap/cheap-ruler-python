import json
import math
import unittest

from cHaversine import haversine

from cheapruler import from_tile, CheapRuler


lines_data = json.load(open('./lines.json', 'r'))

# convert coordinates from lists into tuples
lines = [[(p[0], p[1]) for p in line] for line in lines_data]

points = sum(lines, [])

ruler = CheapRuler(32.8351)
miles_ruler = CheapRuler(32.8351, 'miles')


def assertError(actual, expected, max_error):
    if math.isnan(actual) or math.isnan(expected):
        raise ValueError("NaN for actual or expected value")

    if expected == 0:
        if actual != 0:
            raise ValueError("Expected 0 but got %f" % (err,))
    else:
        err = abs((actual - expected) / expected)
        if err > max_error:
            raise ValueError("Error higher than expected: %f" % (err,))


class TestCheapRuler(unittest.TestCase):

    def test_cheapruler_constructor(self):
        self.assertRaises(ValueError, CheapRuler, 39, 'not a unit')

    def test_distance(self):
        for i in range(len(points) - 1):
            # convert haversine's meters to km
            expected = haversine((points[i][1], points[i][0]), (points[i+1][1], points[i+1][0])) / 1000
            actual = ruler.distance(points[i], points[i+1])
            print("%s, %s, %s, %s" % (points[i], points[i+1], expected, actual))
            assertError(actual, expected, 0.003)

    def test_distance_in_miles(self):
        d = ruler.distance((30.5, 32.8351), (30.51, 32.8451));
        d2 = miles_ruler.distance((30.5, 32.8351), (30.51, 32.8451));

        assertError(d / d2, 1.609344, 1e-12)
