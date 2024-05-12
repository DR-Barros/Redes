#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time
import signal
import os

#funcion que lee desde el socket y lo guarda en un archivo
def Rdr(s, fileout, dist, pack_sz, datosCompartidos):
    with open(fileout, 'wb') as f:
        while True:
            try:
                data=s.recv(pack_sz)
            except:
                continue
            if data: 
                f.write(data)
                with datosCompartidos['lock']:
                    datosCompartidos['read'] += 1
                    if datosCompartidos['sent'] - datosCompartidos['read'] <= dist:
                        datosCompartidos['distanciaEvent'].set()

if len(sys.argv) != 7:
    print('Use: '+sys.argv[0]+' pack_sz dist filein fileout host port')
    sys.exit(1)
#obtenemos las variables de los argumentos
pack_sz = int(sys.argv[1])
dist = int(sys.argv[2])
filein = sys.argv[3]
fileout = sys.argv[4]


s = jsockets.socket_udp_connect(sys.argv[5], int(sys.argv[6]))
if s is None:
    print('could not open socket')
    sys.exit(1)

# Esto es para dejar tiempo al server para conectar el socket
s.send(b'hola')
s.recv(1024)

datosCompartidos = {
    'distanciaEvent': threading.Event(),
    'read': 0,
    'sent': 0,
    'lock': threading.Lock(),
}
datosCompartidos['distanciaEvent'].set()  # inicialmente permitir enviar
# thread para leer desde socket y escribir en fileout
newthread = threading.Thread(target=Rdr, args=(s, fileout, dist, pack_sz, datosCompartidos))
newthread.start() # thread para escribir hacia socket

tiempo = time.time()
# En este otro thread leo desde filein hacia socket:
with open(filein, 'br') as f:
    while True:
        datosCompartidos['distanciaEvent'].wait(0.8) # si se excede la distancia, se espera
        data = f.read(pack_sz)
        if not data:
            break
        s.send(data)
        with datosCompartidos['lock']:
            datosCompartidos['sent'] += 1
            if datosCompartidos['sent'] - datosCompartidos['read'] > dist:
                datosCompartidos['distanciaEvent'].clear() 

newthread.join(timeout=0.8)
s.close()
print("Usando: pack:", pack_sz, "dist:", dist)
print('Tiempo total:', time.time()-tiempo)
print('Sent', datosCompartidos['sent'], 'packets')
print('Received', datosCompartidos['read'], 'packets')
os.kill(os.getpid(), signal.SIGKILL)