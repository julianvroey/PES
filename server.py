from flask import Flask, render_template, redirect, url_for, request, session, flash, Response, jsonify
from threading import Thread, Lock
import cv2
import numpy as np
import pytesseract
import re
import json
import os


app = Flask(__name__)
app.secret_key = '1234'

view_app = Flask(__name__)

KNOWN_WIDTH_OLD = 145
KNOWN_HEIGHT_OLD = 45
REAL_RATIO_OLD = KNOWN_WIDTH_OLD / KNOWN_HEIGHT_OLD
KNOWN_WIDTH_NEW = 235 
KNOWN_HEIGHT_NEW = 53
REAL_RATIO_NEW = KNOWN_WIDTH_NEW / KNOWN_HEIGHT_NEW
FOCAL_LENGTH_OLD = 550   
FOCAL_LENGTH_NEW = 550  
MIN_AREA = 500
MAX_ROTATION = 15

text_ = None
distance_ = None
deviation_ = None
side_ = None
calibrate_distance = None
calibrate_deviation = 20
DELTA_DISTANCE = 5
MAX_DEVIATION = 20
CALIBRATION_FILE = 'calibration_data.json'

CENTER = 1
LEFT = 0
RIGHT = 2

IMG_ESTACIONE = 0
IMG_FRENE = 1
IMG_ADELANTE = 2
IMG_CORRIJA_ROTAR = 3
IMG_CORRIJA_IZQUIERDA = 4
IMG_CORRIJA_DERECHA = 5


def load_calibration():
    """Carga la distancia calibrada desde un archivo JSON."""
    if os.path.exists(CALIBRATION_FILE):
        with open(CALIBRATION_FILE, 'r') as file:
            data = json.load(file)
            return data.get('calibrated_distance', None)
    return None

def save_calibration(distance):
    """Guarda la distancia calibrada en un archivo JSON."""
    with open(CALIBRATION_FILE, 'w') as file:
        json.dump({'calibrated_distance': distance}, file)

calibrate_distance = load_calibration()

# Funciones auxiliares
def load_users():
    with open('users.json', 'r') as file:
        return json.load(file)

def get_distance_to_center(rect_center, image_center):
    return np.sqrt((rect_center[0] - image_center[0]) ** 2 + (rect_center[1] - image_center[1]) ** 2)

def calculate_distance(known_width, focal_length, pixel_width):
    return (known_width * focal_length) / pixel_width

def gen_frames(index):
    global text_, distance_, deviation_, side_
    cap = cv2.VideoCapture(int(index))
    while True:
        success, frame = cap.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        image_center = (frame.shape[1] // 2, frame.shape[0] // 2)
        width_third = frame.shape[1] // 3
        matched_contour = None
        matched_metric = float('inf')

        for contour in contours:
            if cv2.contourArea(contour) > MIN_AREA:
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                if len(approx) == 4 and cv2.isContourConvex(approx):
                    x, y, w, h = cv2.boundingRect(approx)
                    
                    if w > h:
                        rot_rect = cv2.minAreaRect(contour)
                        rect_angle = rot_rect[2]
                        if rect_angle < -45:
                            rect_angle += 90
                        elif rect_angle > 45:
                            rect_angle -= 90

                        if not (-MAX_ROTATION <= rect_angle <= MAX_ROTATION):
                            continue

                        rect_center = (x + w // 2, y + h // 2)
                        distance_to_center = get_distance_to_center(rect_center, image_center)
                        metric = distance_to_center - 0.5 * cv2.contourArea(contour) 

                        roi = blur[y:y + h, x:x + w]
                        _, binary = cv2.threshold(roi, 55, 255, cv2.THRESH_BINARY_INV)
                        kernel = np.ones((1, 1), np.uint8)
                        plate = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

                        text = pytesseract.image_to_string(plate, config="--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                        text = re.sub(r'[^A-Z0-9]', '', text) 

                        if len(text) == 6:
                            real_ratio = REAL_RATIO_OLD
                            real_width = KNOWN_WIDTH_OLD
                            focal_length = FOCAL_LENGTH_OLD
                        else:#elif len(text) == 7:
                            real_ratio = REAL_RATIO_NEW
                            real_width = KNOWN_WIDTH_NEW
                            focal_length = FOCAL_LENGTH_NEW
                        #else :
                            #continue

                        if metric < matched_metric:
                            matched_metric = metric
                            matched_contour = contour
                            matched_width = max(rot_rect[1])  
                            matched_height = min(rot_rect[1])
                            observed_ratio = matched_width / matched_height
                            matched_text = text
                            matched_rect_center_x = rect_center[0]

        if matched_contour is not None:
            if matched_rect_center_x < width_third :
                side_ = 1
                color = (0, 0, 255)
            elif matched_rect_center_x > 2 * width_third :
                side_ = 2
                color = (0, 0, 255)
            else:
                side_ = 0
                color = (0, 255, 0)

            cv2.drawContours(frame, [matched_contour], -1, (255, 0, 0), 2)
            x, y, w, h = cv2.boundingRect(matched_contour)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            text_ = matched_text
            distance_ = f"{round(calculate_distance(real_width, focal_length, matched_width) / 10, 1)} cm"
            deviation_ = f"{round(np.degrees(np.arccos(min(observed_ratio / real_ratio, 1))), 1)} °" 
        else:
            text_ = "-"
            distance_ = "-"
            deviation_ = "-"

        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('menu'))
        else:
            flash('Credenciales inválidas.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/menu', methods=['GET', 'POST'])
def menu():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user_file = f'{username}_devices.json'

    if not os.path.exists(user_file):
        with open(user_file, 'w') as file:
            json.dump([], file)

    with open(user_file, 'r') as file:
        devices = json.load(file)

    if request.method == 'POST':
        if 'add_device' in request.form:
            name = request.form['name']
            index = request.form['index']
            devices.append({'name': name, 'index': index})
            
        elif 'delete_device' in request.form:
            index = int(request.form['delete_device'])
            devices = [d for d in devices if d['index'] != str(index)]

        with open(user_file, 'w') as file:
            json.dump(devices, file)

    return render_template('menu.html', devices=devices)

@app.route('/device/<int:index>')
def device(index):
    global text_, distance_, deviation_
    if 'username' not in session:
        return redirect(url_for('login'))
    username = session['username']
    devices = f'{username}_devices.json'
    with open(devices, 'r') as f:
        data = json.load(f)
    device_name = next((d['name'] for d in data if d['index'] == index), 'Desconocido')

    return render_template('device.html', 
                           device_name=device_name, 
                           text=text_, 
                           distance=distance_, 
                           deviation=deviation_,
                           index=index)

@app.route('/get_device_data/<index>')
def get_device_data(index):
    index = int(index)
    data = {
        "text": text_,
        "distance": distance_,
        "deviation": deviation_
    }
    return jsonify(data)

@app.route('/video_feed/<int:index>')
def video_feed(index):
    return Response(gen_frames(index), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/calibrate_distance', methods=['POST'])
def calibrate_distance_route():
    global calibrate_distance
    data = request.json
    distance_str = data.get('distance')
    if distance_str and distance_str != "-":
        try:
            distance = float(distance_str.split()[0])  # Convertir solo la parte numérica a float
            calibrate_distance = distance
            save_calibration(calibrate_distance)
            return jsonify({"message": f"Distancia calibrada con éxito en {calibrate_distance} cm"}), 200
        except ValueError:
            return jsonify({"message": "Distancia no válida"}), 400
    return jsonify({"message": "Distancia inválida"}), 400

def parse_data(data_str):
    """Convierte una distancia en formato 'xx.x cm' a float."""
    try:
        return float(data_str.split()[0])  # Obtener la parte numérica y convertirla a float
    except (ValueError, AttributeError):
        return None  # Manejar casos inválidos

@view_app.route('/<int:device_index>')
def view_device(device_index):
    """Vista específica para cada dispositivo."""
    return render_template('view.html', device_index=device_index)

@view_app.route('/get_status/<int:device_index>')
def get_status(device_index):
    """Obtiene el estado actual del dispositivo."""
    #global distance_, calibrate_distance, side_

    current_distance = parse_data(distance_)
    current_angle = parse_data(deviation_)
    signal = IMG_ESTACIONE

    if current_distance is not None:
        if current_distance >= (calibrate_distance - DELTA_DISTANCE) and current_distance <= (calibrate_distance + DELTA_DISTANCE):
            signal = IMG_FRENE
        if current_distance > (calibrate_distance + DELTA_DISTANCE):
            signal = IMG_ESTACIONE

    if side_ == 1:
        signal = IMG_CORRIJA_IZQUIERDA
    if side_ == RIGHT:
        signal = IMG_CORRIJA_DERECHA

    if current_angle is not None:
        if current_angle > MAX_DEVIATION :
            signal = IMG_CORRIJA_ROTAR

    if current_distance is not None:
        if current_distance <= (calibrate_distance - DELTA_DISTANCE):
            signal = IMG_ADELANTE 

    return jsonify({
        "img": signal
    })


def run_server():
    app.run(port=5000, debug=False, host="0.0.0.0", use_reloader=False)

def run_view():
    view_app.run(port=5001, debug=False, host="0.0.0.0", use_reloader=False)

if __name__ == '__main__':
    Thread(target=run_server).start()
    Thread(target=run_view).start()