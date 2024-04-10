#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time

#funcion que lee desde el socket y lo guarda en un archivo
def Rdr(s, fileout, dist, pack_sz, datosCompartidos):
    while True:
        try:
            data=s.recv(pack_sz)
        except:
            data = None
        if not data: 
            break
        with open(fileout, 'ab') as f:
            f.write(data)
        datosCompartidos['lock'].acquire()
        datosCompartidos['read'] += 1
        if datosCompartidos['sent'] - datosCompartidos['read'] > dist:
            datosCompartidos['distanciaEvent'].clear() # si se excede la distancia, se espera
        else:
            datosCompartidos['distanciaEvent'].set()
        datosCompartidos['lock'].release()

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
    'lock': threading.Lock()

}
# thread para leer desde socket y escribir en fileout
newthread = threading.Thread(target=Rdr, args=(s, fileout, dist, pack_sz, datosCompartidos))
newthread.start() # thread para escribir hacia socket


for i in range(10):
    tiempo = time.time()
    # En este otro thread leo desde filein hacia socket:
    with open(filein, 'br') as f:
        while True:
            datosCompartidos['distanciaEvent'].wait(0.8) # si se excede la distancia, se espera
            data = f.read(pack_sz)
            if not data:
                break
            s.send(data)
            datosCompartidos['lock'].acquire()
            datosCompartidos['sent'] += 1
            datosCompartidos['lock'].release()   

    time.sleep(3)  # dar tiempo para que vuelva la respuesta
    print('Time:', time.time()-tiempo)
    print('Sent', datosCompartidos['sent'], 'packets')
    print('Received', datosCompartidos['read'], 'packets')

s.close()