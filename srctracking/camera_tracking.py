import asyncio
import subprocess
import time
import cv2
import socket
import numpy as np
import requests
from pynput.mouse import Controller

from pylivelinktracking import PyLiveLinkTracking, TrackingDataValues
import math

VIDEO_DEVICES = 5

FOV_X = 70
FOV_Y = 40

RES_X = 960
RES_Y = 576

C1_X_ANGLE = 0
C1_Y_ANGLE = 0

C2_X_ANGLE = 0
C2_Y_ANGLE = 0

CAM_1_X_OFFSET = 90
CAM_1_Y_OFFSET = 15
CAM_1_Z_OFFSET = 96

CAM_2_X_OFFSET = 76.5 # distance between cameras

ORIGIN_OFFSET = [0, 0, 0]
HEAD_ROTATE_OFFSET = [0, 0, 0]
ORIGIN_SCALE = [1, -1, 1]

MOVEMENT_TOLERANCE = 10
MARKER_THRESHOLD = 55

DATA_INTERVAL = 0.1

UDP_IP = "127.0.0.1"
UDP_PORT = 11111

class Transform:
    def __init__(self, position, rotation):
        self.position = position
        self.rotation = rotation

    def __str__(self):
        return f'Pos:{self.position} Rot:{self.rotation}'
    
    def __repr__(self):
        return f'Pos:{self.position} Rot:{self.rotation}'
    

class Camera:
    def __init__(self, name, device_name, index, capture, transform):
        self.name = name
        self.deviceName = device_name
        self.index = index
        self.capture = capture
        self.mask = None
        self.dots = []
        self.transform = transform

    def __str__(self):
        return f'Name: {self.name}\t|\tIndex:{self.index}\t|\tMarkers: {len(self.dots)}'
    
    def __repr__(self):
        return f'Name: {self.name}\t|\tIndex:{self.index}\t|\tMarkers: {len(self.dots)}'


class CameraBank:

    def __init__(self):
        self.cameras = {}
        self.add_camera_information()
        self.num_cameras = len(self.cameras)

    def __str__(self):
        cams = ''
        points = 0
        for camera in self.cameras:
            cams += f'{self.cameras[camera]}\n'
            points += len(self.cameras[camera].dots)
        return f'--------\nCameras: {self.num_cameras}\t|\tPoints: {points/len(self.cameras)}\n{cams}'
    
    def __repr__(self):
        cams = ''
        points = 0
        for camera in self.cameras:
            cams += f'{self.cameras[camera]}\n'
            points += len(self.cameras[camera].dots)
        return f'--------\nCameras: {self.num_cameras}\t|\tPoints: {points/len(self.cameras)}\n{cams}'

    def get_camera_indexes(self) -> list[int]:
        index = 0
        camera_indexes = []
        max_numbers_of_cameras_to_check = 15
        while max_numbers_of_cameras_to_check > 0:
            capture = cv2.VideoCapture(index)
            if capture.read()[0]:
                camera_indexes.append(index)
                capture.release()
            index += 1
            max_numbers_of_cameras_to_check -= 1
        return camera_indexes

    def add_camera_information(self) -> list:
        camera_indexes = self.get_camera_indexes()
        i = 1
        for camera_index in camera_indexes:
            camera_name = subprocess.run(['cat', '/sys/class/video4linux/video{}/name'.format(camera_index)],
                                            stdout=subprocess.PIPE).stdout.decode('utf-8')
            camera_name = camera_name.replace('\n', '')
            print(camera_name)
            if (camera_name.find('Rift') != -1):
                self.cameras[f"Cam{i}"] = Camera(
                    name=f"Cam{i}",
                    device_name=camera_name,
                    index=camera_index,
                    capture=cv2.VideoCapture(camera_index),
                    transform=Transform(np.zeros(3), np.zeros(3))
                )
                i += 1


camera_bank = CameraBank()


class TrackingConnection:
    def __init__(self, offset, marker1, marker2):
        self.offset = offset
        self.marker1 = marker1
        self.marker2 = marker2

    def __str__(self):
        return 'm1:{} m2:{}'.format(self.marker1, self.marker2)
    
    def __repr__(self):
        return 'm1:{} m2:{}'.format(self.marker1, self.marker2)


class TrackingMarker:
    def __init__(self, name, position):
        self.name = name
        self.position = position
        self.isTracked = False
        self.initialized = False
        self.camera_positions = {}


    def calibrate(self, camera, dot):
        self.initialized = True
        print(f"calibrating {self.name} in {camera} {dot}")
        self.camera_positions[camera] = dot


    def update(self, camera, dots):
        if self.initialized:
            closest = None
            closest_diff = 10000000
            for dot in dots:
                diff = abs(self.camera_positions[camera][0] - dot[0]) + abs(self.camera_positions[camera][1] - dot[1])
                if diff < MOVEMENT_TOLERANCE and diff < closest_diff:
                    closest = dot
            if closest:
                self.camera_positions[camera] = closest
                self.isTracked = True
                dots.remove(closest)
            else:
                self.isTracked = False
        return dots
    
    def postUpdateFixes(self, camera, dots):
        if not self.isTracked:
            closest = None
            closest_diff = 100000
            for dot in dots:
                if camera not in self.camera_positions:
                    break
                diff = abs(self.camera_positions[camera][0] - dot[0]) + abs(self.camera_positions[camera][1] - dot[1])
                if diff < closest_diff:
                    closest = dot
            if closest:
                self.camera_positions[camera] = closest
                self.isTracked = True
                dots.remove(closest)
            else:
                self.isTracked = False
        return dots

    def calculate_position(self, cameras: CameraBank):
        c1_x_angle = 0
        c1_y_angle = 0
        c2_x_angle = 0
        c2_y_angle = 0

        # Get angles
        if self.camera_positions.get('Cam1'):
            c1_x_angle = 90+(self.camera_positions['Cam1'][0] / RES_X - 0.5) * FOV_X + C1_X_ANGLE
            # print(f"c1Xa: {c1_x_angle}")
            c1_y_angle = C1_Y_ANGLE - (self.camera_positions['Cam1'][1] / RES_Y - 0.5) * FOV_Y
            # print(f"c1Ya: {c1_y_angle}")
        if self.camera_positions.get('Cam2'):
            c2_x_angle = 90-(self.camera_positions['Cam2'][0] / RES_X - 0.5) * FOV_X + C2_X_ANGLE
            # print(f"c2Xa: {c2_x_angle}")
            c2_y_angle = C2_Y_ANGLE - (self.camera_positions['Cam2'][1] / RES_Y - 0.5) * FOV_Y
            # print(f"c2Ya: {c2_y_angle}")
    
        pov_x_angle = 180 - abs(c1_x_angle) - abs(c2_x_angle)

        # print(f"povx:{pov_x_angle:.2f}")

        # if self.name == 'head1':
        #     print(f"{self.name} pov:{pov_x_angle:.2f} c1x:{c1_x_angle:.2f} c2x:{c2_x_angle:.2f} {pov_x_angle + c1_x_angle + c2_x_angle:.2f}")

        # Convert angles to radians
        c1_x_angle = math.radians(abs(c1_x_angle))
        c1_y_angle = math.radians(abs(c1_y_angle))
        c2_x_angle = math.radians(abs(c2_x_angle))
        c2_y_angle = math.radians(c2_y_angle)
        pov_x_angle = math.radians(pov_x_angle)


        # Law of Tangents
        # calc H2 (distance from camera 2 to marker)
        # (CAM_2_X_OFFSET - H2) / (CAM_2_X_OFFSET + H2) = tan(0.5 * (pov_x_angle - c1_x_angle)) / tan(0.5 * (pov_x_angle + c1_x_angle))
        temp = math.tan(0.5 * (pov_x_angle - c2_x_angle)) / math.tan(0.5 * (pov_x_angle + c2_x_angle))
        
        # (CAM_2_X_OFFSET - H2) = (Cam_2_X_OFFSET * temp) + (temp * H2)
        # CAM_2_X_OFFSET - (Cam_2_X_OFFSET * temp) - H2 = temp * H2
        # CAM_2_X_OFFSET - (Cam_2_X_OFFSET * temp) = temp * H2 + H2
        # CAM_2_X_OFFSET - (Cam_2_X_OFFSET * temp) = (temp+1) * H2
        # (CAM_2_X_OFFSET - (Cam_2_X_OFFSET * temp)) / (temp+1) = H2
        if temp+1 == 0:
            h2 = CAM_2_X_OFFSET
        else:
            h2 = (CAM_2_X_OFFSET - (CAM_2_X_OFFSET * temp)) / (temp+1)

        # cos(c2_x_angle) = x / h2
        x = h2 * math.cos(c1_x_angle)
        # sin(c2_x_angle) = y / h2
        y = h2 * math.sin(c1_x_angle)
        # sin(c2_y_angle) = z / h2
        z = h2 * math.sin(c2_y_angle)


        self.position = [
            x*ORIGIN_SCALE[0]+ORIGIN_OFFSET[0], 
            y*ORIGIN_SCALE[1]+ORIGIN_OFFSET[1],
            z*ORIGIN_SCALE[2]+ORIGIN_OFFSET[2] #- y*0.65 + x*0.7
        ]

    def __str__(self):
        return f'Name: {self.name}\t|\tTracked: {self.isTracked}\t|\position: {self.position}\t|\tCamera_positions: {self.camera_positions}'
    
    def __repr__(self):
        return f'Name: {self.name}\t|\tTracked: {self.isTracked}\t|\position: {self.position}\t|\tCamera_positions: {self.camera_positions}'


def connect_to_live_link():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        s.connect((UDP_IP, UDP_PORT))

        livelink = PyLiveLinkTracking()    
        return s, livelink
    except Exception as e:
        print(f"Error: {e}")
        return None, None

async def main():
    print("Camera Bank", camera_bank)

    s, livelink = connect_to_live_link()
    last_connect_attempt = time.time()
    disconnected = False

    camera_bank.cameras["Cam1"].transform = Transform(np.array([CAM_2_X_OFFSET, 0, 0]), np.array([0, 0, 0]))
    camera_bank.cameras["Cam2"].transform = Transform(np.array([0, 0, 0]), np.array([0, 0, 0]))

    # markers
    ShoulderL = TrackingMarker('ShoulderL', np.array([0, 0, 0]))
    ChestTop = TrackingMarker('ChestTop', np.array([0, 0, 0]))
    ShoulderR = TrackingMarker('ShoulderR', np.array([0, 0, 0]))

    # markers
    markers = {
        'ShoulderL': ShoulderL,
        'ChestTop': ChestTop,
        'ShoulderR': ShoulderR,
    }

    global calibrate
    calibrate = True
    data_task = None
    last_data = 0
    anim_data = {}

    mouse = Controller()

    async def fetch_anim_data():
        while True:
            try:
                anim_data = requests.get("http://127.0.0.1:5275/animData").json()
                if "recalibrate" in anim_data:
                    global calibrate
                    calibrate = True
                return anim_data
            except Exception as e:
                pass

    while (1):
        for camera in camera_bank.cameras:
            ret, frame = camera_bank.cameras[camera].capture.read() # 576x960
            
            if data_task is None and time.time() - last_data > DATA_INTERVAL:
                data_task = fetch_anim_data()

            frame = cv2.flip(frame, 1)

            upper = 255
            camera_bank.cameras[camera].mask = cv2.inRange(frame, (MARKER_THRESHOLD, MARKER_THRESHOLD, MARKER_THRESHOLD), (upper, upper, upper))

            contours, _ = cv2.findContours(camera_bank.cameras[camera].mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            dots = []
            for contour in contours:
                M = cv2.moments(contour)
                if M["m00"] > 5:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    dots.append((cX, cY))
            dots.sort(key=lambda dot: dot[0])

            camera_bank.cameras[camera].mask = cv2.cvtColor(camera_bank.cameras[camera].mask, cv2.COLOR_GRAY2BGR) # put this here to draw on the mask in color
            
            if calibrate:
                try:
                    print("dots: ", dots)
                    print("camera index", camera_bank.cameras[camera].index, camera)

                    if camera == "Cam1":
                        markers['ShoulderL'].isTracked = True
                        markers['ShoulderL'].calibrate(camera, dots[0])

                        markers['ChestTop'].isTracked = True
                        markers['ChestTop'].calibrate(camera, dots[1])

                        markers['ShoulderR'].isTracked = True
                        markers['ShoulderR'].calibrate(camera, dots[2])
                    elif camera == "Cam2":
                        markers['ShoulderL'].isTracked = True
                        markers['ShoulderL'].calibrate(camera, dots[0])

                        markers['ChestTop'].isTracked = True
                        markers['ChestTop'].calibrate(camera, dots[1])

                        markers['ShoulderR'].isTracked = True
                        markers['ShoulderR'].calibrate(camera, dots[2])

                    for marker in markers:
                        markers[marker].calculate_position(camera_bank)

                except Exception as e:
                    print("Calibration failed")
                    print(e)

            for marker in markers:
                dots = markers[marker].update(camera, dots)
            for marker in markers:
                dots = markers[marker].postUpdateFixes(camera, dots)

            # Draw center lines
            cv2.line(camera_bank.cameras[camera].mask, (RES_X//2, 0), (RES_X//2, RES_Y), (25, 25, 25), 2)
            cv2.line(camera_bank.cameras[camera].mask, (0, RES_Y//2), (RES_X, RES_Y//2), (25, 25, 25), 2)

            for l in range(0, RES_X, int(RES_X / FOV_X * 10 / 2)):
                cv2.line(camera_bank.cameras[camera].mask, (l, 0), (l, RES_Y), (15, 15, 25), 1)
            for l in range(0, RES_Y, int(RES_Y / FOV_Y * 10 / 2)):
                cv2.line(camera_bank.cameras[camera].mask, (0, l), (RES_X, l), (25, 25, 25), 1)

        for marker in markers:
            markers[marker].calculate_position(camera_bank)

        for camera in camera_bank.cameras:
            for marker in markers:
                if markers[marker].camera_positions.get(camera) is not None:
                    position = (markers[marker].camera_positions[camera][0], markers[marker].camera_positions[camera][1])
                    cv2.circle(camera_bank.cameras[camera].mask, position, 3, (00, 0, 255), -1)
                    cv2.putText(camera_bank.cameras[camera].mask, markers[marker].name, position, cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 1)


        for camera in camera_bank.cameras:
            cv2.imshow(camera, camera_bank.cameras[camera].mask)

        calibrate = False

        if data_task is not None:
            data = await data_task
            data_task = None
            last_data = time.time()
            anim_data = data

        # try:
        if (disconnected):
            if (time.time() - last_connect_attempt > 5):
                s, livelink = connect_to_live_link()
                last_connect_attempt = time.time()
        else:
            livelink.set_value(TrackingDataValues.MouseX, mouse.position[0])
            livelink.set_value(TrackingDataValues.MouseY, mouse.position[1])

            if len(anim_data) > 1:
                livelink.set_value(TrackingDataValues.Aux1, 1.0 if anim_data["riot"]["isTalking"] else 0.0)
                livelink.set_value(TrackingDataValues.Aux2, 1.0 if anim_data["slimenetwork"]["isTalking"] else 0.0)
                # livelink.set_value(TrackingDataValues.Aux3, 1.0 if anim_data["guest1"]["isTalking"] else 0.0)
                # livelink.set_value(TrackingDataValues.Aux4, 1.0 if anim_data["guest2"]["isTalking"] else 0.0)
                # livelink.set_value(TrackingDataValues.Aux5, 1.0 if anim_data["guest3"]["isTalking"] else 0.0)
                # livelink.set_value(TrackingDataValues.Aux6, 1.0 if anim_data["guest4"]["isTalking"] else 0.0)

            i = 0
            for marker in markers:
                livelink.set_value(TrackingDataValues.marker1X + i*3, markers[marker].position[0] + CAM_1_X_OFFSET)
                livelink.set_value(TrackingDataValues.marker1Y + i*3, markers[marker].position[1] + CAM_1_Y_OFFSET)
                livelink.set_value(TrackingDataValues.marker1Z + i*3, markers[marker].position[2] + CAM_1_Z_OFFSET)
                i += 1

            s.sendall(livelink.encode())
        # except Exception as e:
        #     print(f"Error: Disconnected {e}")
        #     disconnected = True

        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #         break
        if cv2.waitKey(1) & 0xFF == ord('c'):
            print("Calibrating")
            calibrate = True

    s.close()
    for camera in camera_bank.cameras:
        camera.capture.release()
    cv2.destroyAllWindows()


# Run the main function within an event loop
if __name__ == "__main__":
    asyncio.run(main())
