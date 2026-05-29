from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("models/yolov8n.pt")

def detect_balls(frame):

    results = model.predict(
        source=frame,
        conf=0.45,
        imgsz=640,
        verbose=False
    )

    balls = []

    for r in results:

        boxes = r.boxes

        for box in boxes:

            x1, y1, x2, y2 = box.xyxy[0]

            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            radius = int((x2 - x1) / 2)

            roi = frame[int(y1):int(y2), int(x1):int(x2)]

            balls.append({
                "x": cx,
                "y": cy,
                "r": radius,
                "roi": roi
            })

    return balls
