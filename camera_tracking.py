import asyncio
import subprocess
import time
import cv2
import socket
from flask import request
import numpy as np
import requests
from pynput.mouse import Controller

from pylivelinkface import PyLiveLinkFace, FaceBlendShape
import math

VIDEO_DEVICES = 5

FOV_X = 40
FOV_Y = 70

RES_X = 576
RES_Y = 960

C1_X_ANGLE = 45
C1_Y_ANGLE = -60

C2_X_ANGLE = -45
C2_Y_ANGLE = -60

CAMERA_OFFSET = 245 # distance between cameras

ORIGIN_OFFSET = [0, 5, 45]
HEAD_ROTATE_OFFSET = [0, 0, -0.2]
ORIGIN_SCALE = [1, -1, 1]

MOVEMENT_TOLERANCE = 10

DATA_INTERVAL = 0.1

UDP_IP = "127.0.0.1"
UDP_PORT = 11111


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
s.connect((UDP_IP, UDP_PORT))

py_face = PyLiveLinkFace()

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
    def __init__(self, name, transform, connections):
        self.name = name
        self.transform = transform
        self.isTracked = False
        self.initialized = False
        self.camera_positions = {}
        self.connections = connections

    def add_connection(self, connection):
        self.connections.append(connection)

    def calibrate(self, camera, dot):
        self.initialized = True
        print(f"calibrating {self.name} in {camera} {dot}")
        self.camera_positions[camera] = dot


    def update(self, camera, dots):
        if self.initialized:
            closest = None
            closest_diff = 100000
            for dot in dots:
                diff = abs(self.camera_positions[camera_bank.cameras[camera].name][0] - dot[0]) + abs(self.camera_positions[camera_bank.cameras[camera].name][1] - dot[1])
                if diff < MOVEMENT_TOLERANCE and diff < closest_diff:
                    closest = dot
            if closest:
                self.camera_positions[camera_bank.cameras[camera].name] = closest
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
                diff = abs(self.camera_positions[camera_bank.cameras[camera].name][0] - dot[0]) + abs(self.camera_positions[camera_bank.cameras[camera].name][1] - dot[1])
                if diff < closest_diff:
                    closest = dot
            if closest:
                self.camera_positions[camera_bank.cameras[camera].name] = closest
                self.isTracked = True
                dots.remove(closest)
            else:
                self.isTracked = False
        return dots

    def calculate_transform(self, cameras: CameraBank):
        c1_x_angle = 0
        c1_y_angle = 0
        c2_x_angle = 0
        c2_y_angle = 0

        # Get angles
        if self.camera_positions.get('Cam1'):
            c1_x_angle = (self.camera_positions['Cam1'][0] / RES_X - 0.5) * 2 * FOV_X + C1_X_ANGLE
            # print(f"c1Xa: {c1_x_angle}")
            c1_y_angle = C1_Y_ANGLE - (self.camera_positions['Cam1'][1] / RES_Y - 0.5) * 2 * FOV_Y
            # print(f"c1Ya: {c1_y_angle}")
        if self.camera_positions.get('Cam2'):
            c2_x_angle = (self.camera_positions['Cam2'][0] / RES_X - 0.5) * 2 * FOV_X + C2_X_ANGLE
            # print(f"c2Xa: {c2_x_angle}")
            c2_y_angle = C2_Y_ANGLE - (self.camera_positions['Cam2'][1] / RES_Y - 0.5) * 2 * FOV_Y
            # print(f"c2Ya: {c2_y_angle}")

        pov_x_angle = 180 - abs(c1_x_angle) - abs(c2_x_angle)


        # Convert angles to radians
        c1_x_angle = math.radians(90-abs(c1_x_angle))
        c1_y_angle = math.radians(abs(c1_y_angle))
        c2_x_angle = math.radians(90-abs(c2_x_angle))
        c2_y_angle = math.radians(abs(c2_y_angle))
        pov_x_angle = math.radians(pov_x_angle)
        

        # Law of Tangents
        # calc H1 (distance from camera 1 to marker)
        # (CAMERA_OFFSET - H1) / (CAMERA_OFFSET + H1) = tan(0.5 * (pov_x_angle - c2_x_angle)) / tan(0.5 * (pov_x_angle + c2_x_angle))
        temp = math.tan(0.5 * (pov_x_angle - c2_x_angle)) / math.tan(0.5 * (pov_x_angle + c2_x_angle))
        # (CAMERA_OFFSET - H1) = (Camera_OFFSET * temp) + (temp * H1)
        # CAMERA_OFFSET - (Camera_OFFSET * temp) - H1 = temp * H1
        # CAMERA_OFFSET - (Camera_OFFSET * temp) = temp * H1 + H1
        # CAMERA_OFFSET - (Camera_OFFSET * temp) = (temp+1) * H1
        # (CAMERA_OFFSET - (Camera_OFFSET * temp)) / (temp+1) = H1
        h1 = (CAMERA_OFFSET - (CAMERA_OFFSET * temp)) / (temp+1)

        y = math.sin(c1_x_angle) * h1
        x = CAMERA_OFFSET - math.cos(c1_x_angle) * h1
        if not math.tan(c1_y_angle) == 0: # protect against division by zero
            z = h1 / math.tan(c1_y_angle)

        self.transform.position = [
            x*ORIGIN_SCALE[0]+ORIGIN_OFFSET[0], 
            y*ORIGIN_SCALE[1]+ORIGIN_OFFSET[1],
            z*ORIGIN_SCALE[2]+ORIGIN_OFFSET[2] - y*0.65 + x*0.7
        ]

        # if (self.name == 'head1'):
        #     print(f"X: {x:1f} Y: {y:1f} z: {z:1f}")
        #     expected = self.expected_position()
        #     print(f"Expected: {expected}")

        # if (self.name == 'head2'):
        #     print(f"X: {x:1f} Y: {y:1f} z: {z:1f}")
        #     expected = self.expected_position()
        #     print(f"Expected: {expected}")

    def expected_position(self):
        # untested math, probably wrong
        for connection in self.connections:
            if connection.marker1 == self:
                if connection.marker2.isTracked:
                    return connection.marker1.transform.position + np.dot(connection.marker1.transform.rotation, connection.offset)
            if connection.marker2 == self:
                if connection.marker1.isTracked:
                    return connection.marker2.transform.position - np.dot(connection.marker2.transform.rotation, connection.offset)

    def __str__(self):
        return f'Name: {self.name}\t|\tTracked: {self.isTracked}\t|\tTransform: {self.transform}\t|\tCamera_positions: {self.camera_positions}'
    
    def __repr__(self):
        return f'Name: {self.name}\t|\tTracked: {self.isTracked}\t|\tTransform: {self.transform}\t|\tCamera_positions: {self.camera_positions}'




async def main():
    print("Camera Bank", camera_bank)

    camera_bank.cameras["Cam1"].transform = Transform(np.array([0, 0, 0]), np.array([-20, 0, 200]))
    camera_bank.cameras["Cam1"].transform = Transform(np.array([-CAMERA_OFFSET, 0, 0]), np.array([-20, 0, 160]))

    # markers
    head1 = TrackingMarker('head1', Transform(np.array([-50, 70, -20]), np.array([0, 0, 0])), [])
    head2 = TrackingMarker('head2', Transform(np.array([-58, 70, -20]), np.array([0, 0, 0])), [])
    head3 = TrackingMarker('head3', Transform(np.array([-64, 70, -27]), np.array([0, 0, 0])), [])
    head4 = TrackingMarker('head4', Transform(np.array([-44, 70, -27]), np.array([0, 0, 0])), [])

    head1_2 = TrackingConnection(np.array([-8, 0, 0]), head1, head2)
    head1_3 = TrackingConnection(np.array([-14, 0, -7]), head1, head3)
    head1_4 = TrackingConnection(np.array([6, 0, -7]), head3, head4)
    head2_3 = TrackingConnection(np.array([-6, 0, -7]), head2, head3)
    head2_4 = TrackingConnection(np.array([14, 0, -7]), head4, head2)
    head3_4 = TrackingConnection(np.array([-20, 0, 0]), head4, head1)

    head1.add_connection(head1_2)
    head1.add_connection(head1_3)
    head1.add_connection(head1_4)
    head2.add_connection(head1_2)
    head2.add_connection(head2_3)
    head2.add_connection(head2_4)
    head3.add_connection(head1_3)
    head3.add_connection(head2_3)
    head3.add_connection(head3_4)
    head4.add_connection(head1_4)
    head4.add_connection(head2_4)
    head4.add_connection(head3_4)


    # markers
    markers = {
        'head1': head1,
        'head2': head2,
        'head3': head3,
        'head4': head4
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

            if camera == "Cam1":
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            else:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
            if data_task is None and time.time() - last_data > DATA_INTERVAL:
                data_task = fetch_anim_data()

            frame = cv2.flip(frame, 1)

            lower = 70
            upper = 255
            camera_bank.cameras[camera].mask = cv2.inRange(frame, (lower, lower, lower), (upper, upper, upper))

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
                    print("camera index", camera_bank.cameras[camera].index, camera_bank.cameras[camera].name)

                    if camera == "Cam1":
                        markers['head1'].isTracked = True
                        markers['head1'].calibrate(camera, dots[1])

                        markers['head2'].isTracked = True
                        markers['head2'].calibrate(camera, dots[2])

                        markers['head3'].isTracked = True
                        markers['head3'].calibrate(camera, dots[0])

                        markers['head4'].isTracked = True
                        markers['head4'].calibrate(camera, dots[3])
                    else:
                        markers['head1'].isTracked = True
                        markers['head1'].calibrate(camera, dots[1])

                        markers['head2'].isTracked = True
                        markers['head2'].calibrate(camera, dots[2])

                        markers['head3'].isTracked = True
                        markers['head3'].calibrate(camera, dots[0])

                        markers['head4'].isTracked = True
                        markers['head4'].calibrate(camera, dots[3])

                except:
                    print("Calibration failed")

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
            markers[marker].calculate_transform(camera_bank)


        for camera in camera_bank.cameras:
            for marker in markers:
                if markers[marker].camera_positions.get(camera_bank.cameras[camera].name) is not None:
                    position = (markers[marker].camera_positions[camera_bank.cameras[camera].name][0], markers[marker].camera_positions[camera_bank.cameras[camera].name][1])
                    cv2.circle(camera_bank.cameras[camera].mask, position, 3, (00, 0, 255), -1)
                    cv2.putText(camera_bank.cameras[camera].mask, markers[marker].name.split("ead")[1], position, cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 1)
                for connection in markers[marker].connections:
                    cv2.line(camera_bank.cameras[camera].mask, markers[connection.marker1.name].camera_positions[camera_bank.cameras[camera].name], markers[connection.marker2.name].camera_positions[camera_bank.cameras[camera].name], (255, 255, 255), 1)

        # calculate head transform from markers
        head_positions = np.array([])
        for marker in markers:
            if markers[marker].isTracked:
                head_positions = np.append(head_positions, markers[marker].transform.position)

        if len(head_positions) > 0:
            avg_position = [np.mean(head_positions[0::3]), np.mean(head_positions[1::3]), np.mean(head_positions[2::3])]
            
            # Calculate face normal using cross product of vectors between markers
            face_normal = np.cross(np.array(markers['head1'].transform.position) - np.array(markers['head2'].transform.position), np.array(markers['head1'].transform.position) - np.array(markers['head3'].transform.position))

            #calculate z and y rotation from head1 and head2
            z = math.atan2(markers['head1'].transform.position[0] - markers['head2'].transform.position[0], markers['head1'].transform.position[1] - markers['head2'].transform.position[1]) - math.pi/2
            # if z > math.pi:
            #     z -= 2*math.pi
            y = math.atan2(markers['head1'].transform.position[0] - markers['head2'].transform.position[0], markers['head1'].transform.position[2] - markers['head2'].transform.position[2]) - math.pi/2
            # if y > math.pi:
            #     y -= 2*math.pi
            
            #calculate x rotation from head1 and head3
            x = math.atan2(markers['head1'].transform.position[1] - markers['head3'].transform.position[1], markers['head1'].transform.position[2] - markers['head3'].transform.position[2])

            # print(f"x: {x:.2f} y: {y:.2f} z: {z:.2f}")

            # Calculate head transform using average position and tangent vector
            head_transform = Transform(avg_position, np.array([-x + HEAD_ROTATE_OFFSET[0], -z + HEAD_ROTATE_OFFSET[1], -y +  HEAD_ROTATE_OFFSET[2]]))

            # print({"x": head_transform.position[0], "y": head_transform.position[1], "z": head_transform.position[2]})
            # print(f"x: {x:.2f}")
        
        for camera in camera_bank.cameras:
            cv2.imshow(camera, camera_bank.cameras[camera].mask)
        # cv2.imshow(camera_bank.cameras[0], camera_bank.cameras[0].mask)

        calibrate = False

        if data_task is not None:
            data = await data_task
            data_task = None
            last_data = time.time()
            anim_data = data

        py_face.set_blendshape(FaceBlendShape.HeadYaw, head_transform.rotation[0])
        py_face.set_blendshape(FaceBlendShape.HeadPitch, head_transform.rotation[1])
        py_face.set_blendshape(FaceBlendShape.HeadRoll, head_transform.rotation[2])
        py_face.set_blendshape(FaceBlendShape.HeadX, head_transform.position[0])
        py_face.set_blendshape(FaceBlendShape.HeadY, head_transform.position[1])
        py_face.set_blendshape(FaceBlendShape.HeadZ, head_transform.position[2])
        if len(anim_data) > 1:
            py_face.set_blendshape(FaceBlendShape.Character1Talking, 1.0 if anim_data["riot"]["isTalking"] else 0.0)
            py_face.set_blendshape(FaceBlendShape.Character2Talking, 1.0 if anim_data["slimenetwork"]["isTalking"] else 0.0)
            py_face.set_blendshape(FaceBlendShape.Character3Talking, 1.0 if anim_data["filian"]["isTalking"] else 0.0)
            py_face.set_blendshape(FaceBlendShape.Character4Talking, 1.0 if anim_data["henyathegenius"]["isTalking"] else 0.0)
        py_face.set_blendshape(FaceBlendShape.MouseX, mouse.position[0])
        py_face.set_blendshape(FaceBlendShape.MouseY, mouse.position[1])

       
        s.sendall(py_face.encode())

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
