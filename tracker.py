from filterpy.kalman import KalmanFilter
import numpy as np

class BallTracker:

    def __init__(self):

        self.kf = KalmanFilter(dim_x=4, dim_z=2)

        self.kf.F = np.array([
            [1,0,1,0],
            [0,1,0,1],
            [0,0,1,0],
            [0,0,0,1]
        ])

        self.kf.H = np.array([
            [1,0,0,0],
            [0,1,0,0]
        ])

        self.kf.P *= 100
        self.kf.R *= 0.1
        self.kf.Q *= 0.01

    def update(self, x, y):

        self.kf.predict()

        self.kf.update(np.array([x, y]))

        return int(self.kf.x[0]), int(self.kf.x[1])
