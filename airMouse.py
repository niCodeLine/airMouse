# -*- coding: utf-8 -*-

# AGREGAR QUE SI LOS DEDOS ESTAN CERCA EL MOUSE SE MUEVA MAS LENTO

from Quartz import (
    CGEventCreateMouseEvent, CGEventPost, kCGMouseButtonLeft,
    kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventMouseMoved,
    kCGHIDEventTap)

import cv2
from mediapipe import solutions as mps

import math
import osascript
import os

import dictoat

import pyautogui
import pync # notificacion
import time

pyautogui.FAILSAFE = False # avoid warnings

pync.notify('move your right hand to control the mouse', title='airMouse')

# finger's parts ID:
# p -> punta
# a -> abajo

pulgar_p = 4
pulgar_a = 2

indice_p = 8
indice_a = 5
indice_n = 6

fuck_p = 12
fuck_a = 9

anular_p = 16
anular_a = 13

menique_p = 20
menique_a = 17

palma = 0

puntas = [pulgar_p,indice_p,fuck_p,anular_p,menique_p]

# screen size, for scaling
width, height = pyautogui.size()

holdin = False

class Detector:
    def __init__(self, mode: bool = False, maxManos: int = 2, detectionCon: int = 1, trackCon: int = 1):
        '''
        Detecting Hands and Landmarks in the frames.

        :param maxManos: maximum of hands to be detected

        '''
        self.mode = mode
        self.maxManos = maxManos
        self.detectionCon = detectionCon
        self.trackCon = trackCon

        self.mpManos = mps.hands
        self.manos = self.mpManos.Hands() # self.mode,self.maxManos,self.detectionCon,self.trackCon
        self.mpDraw = mps.drawing_utils

    def detectandoMano(self, img, demarcar = True):
        '''
        gets the hand in the image
        '''

        self.imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.results = self.manos.process(self.imgRGB)

        # if marks detected, paint the lines
        if self.results.multi_hand_landmarks:
            for self.puntitos in self.results.multi_hand_landmarks:
                if demarcar:
                    self.mpDraw.draw_landmarks(img, self.puntitos,self.mpManos.HAND_CONNECTIONS)
        return img

    def posiciones(self, img, demarcar = True):
        '''
        gets the positions of the fingers
        '''
        lista = []
        
        # getting coordenates of fingers
        if self.results.multi_hand_landmarks:
            for id, lm in enumerate(self.puntitos.landmark):
                altura, ancho, canal = img.shape
                cx, cy, cz = int(lm.x*ancho), int(lm.y*altura), int(lm.z*altura)
                
                # if marks detected, paint the dots
                if id in puntas and demarcar:
                    cv2.circle(img, (cx,cy),7,(255,0,255),cv2.FILLED)
                lista.append([id,cx,cy,cz])
        
        return lista


def control_mouse(x, y, action='move'):
    if action == 'move':
        event = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, event)

    elif action == 'down':
        event = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, event)

    elif action == 'up':
        event = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft)
        CGEventPost(kCGHIDEventTap, event)

def lista_a_mano(lista, indices):
    def punto(idx):
        return {'x': lista[idx][1], 'y': lista[idx][2], 'z': lista[idx][3]}

    data = {
        'palma': punto(indices['palma']),
        'indice': {
            'punta': punto(indices['indice'][0]),
            'abajo': punto(indices['indice'][1]),
            'neutro': punto(indices['indice'][2]),
        },
        'pulgar': {
            'punta': punto(indices['pulgar'][0]),
            'abajo': punto(indices['pulgar'][1]),
        },
        'menique': {
            'punta': punto(indices['menique'][0]),
            'abajo': punto(indices['menique'][1]),
        },
        'anular': {
            'punta': punto(indices['anular'][0]),
            'abajo': punto(indices['anular'][1]),
        },
        'fuck': {
            'punta': punto(indices['fuck'][0]),
            'abajo': punto(indices['fuck'][1]),
        }
    }

    return dictoat.Dictoat(data, safety= False)

def set_brightness(level: float):
    """
    Change screen brightness.
    :param level: float entre 0 y 100
    """
    level = level/100
    os.system(f"brightness {level}")

def set_volume(level: int):
    """
    Change output volume.
    :param level: int entre 0 y 100
    """
    osascript.run(f'set volume output volume {level}')

def bubblegum(val, MAX_THICK: int = 15, MIN_THICK: int = 2):
    if val < 20:
        return MAX_THICK
    elif val > 100:
        return MIN_THICK
    else:
        m = (MIN_THICK-MAX_THICK)/(100-20)
        b = MAX_THICK - m*20
        return int(m * val + b)


def main():
    cap = cv2.VideoCapture(0)  # Cambiar camara con num
    detectante = Detector()

    cam = True # show video of camera
    demarcar = cam # show dots and lines of the hand recognition in the video
    
    mouse = True # control the mouse
    active = True
    drag = False # <------- this still in process, dont touch

    while cap.isOpened():
        # getting frames and data
        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        if not ret:
            print("Couldnt capture image. Finalizing...")
            break
        
        frame = detectante.detectandoMano(frame,demarcar)
        lista = detectante.posiciones(frame,demarcar)

        altura, ancho, _ = frame.shape

        # do not touch, necesary to stay as is
        tres = False
        dos = False
        puno = False
        spiderman = False
        last_x = 0
        last_y = 0

        # analsys finger position, all the magic happens here
        if len(lista) != 0 and (lista[pulgar_p][1] < lista[menique_a][1]):
            
            # coordinates, fingers and hand
            dedos = {
                'palma': palma,
                'pulgar': [pulgar_p, pulgar_a],
                'indice': [indice_p, indice_a, indice_n],
                'fuck': [fuck_p, fuck_a],
                'anular': [anular_p, anular_a],
                'menique': [menique_p, menique_a],}

            # ex: Mano.indice.punta.x
            Mano = lista_a_mano(lista, dedos)

            # posisicones

            # se usa la distancia desde el punto abajo de la palma como referencia.
            # Y todo se saca a un ratio en relacion a la longitud de la palma.
            # Con esto solucionamos que estando más cerca o más lejos de la cámara
            # las distancias entre los dedos sean generales.
            
            # con esta funcion normalizamos la distancia entre los puntos
            def norma(x_1,x_2,y_1,y_2):
                return round((((x_2 - x_1)**2)+((y_2-y_1)**2))**(1/2),2)

            h_p_pg_a = norma(Mano.pulgar.punta.x, Mano.anular.abajo.x, Mano.pulgar.punta.y, Mano.anular.abajo.y) # el pulgar se relaciona con el anular
            h_a_pg_a = norma(Mano.pulgar.abajo.x, Mano.anular.abajo.x, Mano.pulgar.abajo.y, Mano.anular.abajo.y)

            # hipotenusa punta/abajo _ dedo
            hp_i = norma(Mano.palma.x,Mano.indice.punta.x,Mano.palma.y,Mano.indice.punta.y) 
            hp_f = norma(Mano.palma.x,Mano.fuck.punta.x,Mano.palma.y,Mano.fuck.punta.y)
            hp_a = norma(Mano.palma.x,Mano.anular.punta.x,Mano.palma.y,Mano.anular.punta.y)
            hp_m = norma(Mano.palma.x,Mano.menique.punta.x,Mano.palma.y,Mano.menique.punta.y)

            ha_i = norma(Mano.palma.x,Mano.indice.abajo.x,Mano.palma.y,Mano.indice.abajo.y)
            ha_f = norma(Mano.palma.x,Mano.fuck.abajo.x,Mano.palma.y,Mano.fuck.abajo.y)
            ha_a = norma(Mano.palma.x,Mano.anular.abajo.x,Mano.palma.y,Mano.anular.abajo.y)
            ha_m = norma(Mano.palma.x,Mano.menique.abajo.x,Mano.palma.y,Mano.menique.abajo.y)

            # distancia entre los dedos indicados
            pulgar_indice = norma(Mano.pulgar.punta.x, Mano.indice.punta.x, Mano.pulgar.punta.y, Mano.indice.punta.y)
            pulgar_fuck = norma(Mano.pulgar.punta.x, Mano.fuck.punta.x, Mano.pulgar.punta.y ,Mano.fuck.punta.y)
            pulgar_anular = norma(Mano.pulgar.punta.x, Mano.anular.punta.x, Mano.pulgar.punta.y, Mano.anular.punta.y)
            pulgar_menique = norma(Mano.pulgar.punta.x, Mano.menique.punta.x, Mano.pulgar.punta.y, Mano.menique.punta.y)

            # dedos arribados o abajados
            pulgar_arriba = (h_p_pg_a > h_a_pg_a)
            indice_arriba = (hp_i > ha_i)
            fuck_arriba = (hp_f > ha_f)
            anular_arriba = (hp_a > ha_a)
            menique_arriba = (hp_m > ha_m)

            pulgar_abajo = (h_p_pg_a < h_a_pg_a)
            indice_abajo = (hp_i < ha_i)
            fuck_abajo = (hp_f < ha_f)
            anular_abajo = (hp_a < ha_a)
            menique_abajo = (hp_m < ha_m)

            # referencia de longitudes. Encontré que este valor es el q mejor funciona para los 'click'
            # bajar para aumentar sensibilidad
            ratio = ha_m/4

            # touching fingers
            t_pulgar_indice = True if pulgar_indice <= ratio else False
            t_pulgar_fuck = True if pulgar_fuck <= ratio else False
            t_pulgar_anular = True if pulgar_anular <= ratio else False
            t_pulgar_menique = True if pulgar_menique <= ratio else False

            # signs
            tres = anular_arriba and fuck_arriba and indice_arriba and t_pulgar_menique
            dos = anular_abajo and fuck_arriba and indice_arriba and t_pulgar_anular
            puno = indice_abajo and fuck_abajo and anular_abajo and menique_abajo and pulgar_abajo
            pistola = hp_f < ha_f and hp_a < ha_a and hp_m < ha_m and hp_i > ha_i
            spiderman = pulgar_arriba and indice_arriba and menique_arriba and anular_abajo and fuck_abajo


            # angulo y diseñitos
            d_x = Mano.indice.neutro.x-Mano.indice.abajo.x
            r = round(math.sqrt((Mano.indice.abajo.x-Mano.indice.neutro.x)*(Mano.indice.abajo.x-Mano.indice.neutro.x)+(Mano.indice.abajo.y-Mano.indice.neutro.y)*(Mano.indice.abajo.y-Mano.indice.neutro.y)),1)
            angulo = round(math.acos(d_x/r)*180/math.pi)
            
            if Mano.indice.neutro.y > Mano.indice.abajo.y:
                # angulo = 360 - angulo
                angulo = angulo*-1
            
            if demarcar:
                cv2.putText(frame, str(int(angulo)) + ' deg', (int(Mano.indice.punta.x + 3*ratio), int(Mano.indice.punta.y - 3*ratio)), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 2, (255, 0, 0), 3)

            def cleanVal():
                val = round((pulgar_indice/(ratio*0.8))-1,1)*10
                val = 100 if val >= 100 else val
                val = 0 if val <= 8 else val
                return val

            # mouse y funciones
            if active:
                # zona segura
                val_rectangulo = 187
                
                escala_x = width / (ancho - 2 * val_rectangulo)
                escala_y = height / (altura - 2 * val_rectangulo)

                x_target = (Mano.palma.x - val_rectangulo) * escala_x
                y_target = (Mano.palma.y - val_rectangulo) * escala_y

                # if fingers are close move slower
                if (pulgar_indice <= 3 * ratio and pulgar_indice > ratio) or (pulgar_fuck <= 3 * ratio and pulgar_fuck > ratio):
                    suavizado = 0.7  # lento si dedos cerca
                else:
                    suavizado = 0.7

                # interpolar con la posición anterior
                x_mouse = last_x + (x_target - last_x) * suavizado
                y_mouse = last_y + (y_target - last_y) * suavizado

                mouse = False if pistola or spiderman or t_pulgar_anular else True # t pulgar fuck

                if mouse:
                    # pyautogui.moveTo(x_mouse,y_mouse)
                    control_mouse(x_mouse,y_mouse)

                    if t_pulgar_fuck and menique_arriba and not drag:
                        control_mouse(x_mouse, y_mouse, action='down')
                        drag = True
                        time.sleep(0.1)

                    # si estaba haciendo drag y dejó de hacer el gesto
                    if drag and not (t_pulgar_fuck and menique_arriba):
                        control_mouse(x_mouse, y_mouse, action='up')
                        drag = False
                
                # left click
                # if t_pulgar_fuck and menique_arriba and not drag:
                #     # pyautogui.mouseDown(x_mouse,y_mouse,button='left')
                #     pyautogui.click(button='left')
                #     drag = True
                #     time.sleep(0.3)

                # right click
                if t_pulgar_anular and menique_arriba:
                    pyautogui.click(button='right')
                    time.sleep(0.3)
                
                # Mission Control
                if x_mouse >= 1900 and y_mouse <= 0:
                    osascript.osascript('tell application "System Events" to key code 160')
                    time.sleep(0.25)
                
                # volume
                if pistola:
                    val = cleanVal()
                    set_volume(val)
                    
                    if demarcar:
                        cv2.line(frame, (Mano.pulgar.punta.x, Mano.pulgar.punta.y), (Mano.indice.punta.x, Mano.indice.punta.y), color=(0, 0, 255), thickness=bubblegum(val))
                        cv2.putText(frame, f'Volume: {str(int(val))}', (Mano.indice.punta.x, int(Mano.indice.punta.y - 1*ratio)), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 2, (255, 0, 0), 3)

                # brightness      
                if spiderman:
                    val = cleanVal()
                    set_brightness(val)
                    
                    if demarcar:
                        cv2.line(frame, (Mano.pulgar.punta.x, Mano.pulgar.punta.y), (Mano.indice.punta.x, Mano.indice.punta.y), color=(0, 0, 255), thickness=bubblegum(val))
                        cv2.putText(frame, f'Brightness: {str(int(val))}', (Mano.indice.punta.x, int(Mano.indice.punta.y - 1*ratio)), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 2, (0, 255, 255), 3)

                # scroll
                if t_pulgar_indice and not pistola:
                    #  pyautogui.hscroll(10) 
                    if angulo < 109:
                        pyautogui.scroll(1)
                        pyautogui.scroll(1)
                    if angulo > 120:
                        pyautogui.scroll(-1)
                        pyautogui.scroll(-1)

                # if not t_pulgar_fuck and drag:
                #     drag = False
                    # pyautogui.mouseUp(button='left')
                
                # escribir los deditos
                if demarcar:
                    if pulgar_arriba:
                        pulgar_detalle = ('Arriba', (0,255,0))
                    if not pulgar_arriba:
                        pulgar_detalle = ('Abajo', (0,255,255))
                    cv2.putText(frame, f'Pulgar', (20, altura - 160), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, pulgar_detalle[1], 2)

                    if indice_arriba:
                        indice_detalle = ('Arriba', (0,255,0))
                    if not indice_arriba:
                        indice_detalle = ('Abajo', (0,255,255))
                    cv2.putText(frame, f'Indice', (20, altura - 120), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, indice_detalle[1], 2)

                    if fuck_arriba:
                        fuck_detalle = ('Arriba', (0,255,0))
                    if not fuck_arriba:
                        fuck_detalle = ('Abajo', (0,255,255))
                    cv2.putText(frame, f'Fuck', (20, altura - 90), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, fuck_detalle[1], 2)

                    if anular_arriba:
                        anular_detalle = ('Arriba', (0,255,0))
                    if not anular_arriba:
                        anular_detalle = ('Abajo', (0,255,255))
                    cv2.putText(frame, f'Anular', (20, altura - 60), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, anular_detalle[1], 2)

                    if menique_arriba:
                        menique_detalle = ('Arriba', (0,255,0))
                    if not menique_arriba:
                        menique_detalle = ('Abajo', (0,255,255))
                    cv2.putText(frame, f'Menique', (20, altura - 30), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, menique_detalle[1], 2)

                last_x = x_mouse
                last_y = y_mouse

            print(f"🧠 Tracking: x={int(x_mouse)}, y={int(y_mouse)}", end='\r')

        if cam:
            nuevo_ancho = int(ancho / 2)
            nuevo_alto = int((altura / ancho) * nuevo_ancho)
            frame = cv2.resize(frame, (nuevo_ancho, nuevo_alto))
            cv2.imshow('Mano Tracking', frame)


        if puno:
            if active == True:
                pync.notify('ciego', title='camarouse',appIcon='/Users/nicospok/Pictures/pngwing.com-6.png')
                active = False
        if dos:
            if active == False:
                pync.notify('vidente', title='camarouse',appIcon='/Users/nicospok/Pictures/pngwing.com-6.png')
                active = True
                
        if active and tres:
            pync.notify('chau', title='camarouse',appIcon='/Users/nicospok/Pictures/pngwing.com-6.png')
            break
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
# %%