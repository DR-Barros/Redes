#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time
import signal
import os

#funcion que lee desde el socket y lo guarda en un archivo
def Rdr(s, fileout, pack_sz, datosCompartidos):
    with open(fileout, 'wb') as f:
        while True:
            try:
                data=s.recv(pack_sz)
                if not data:
                    break
                datosCompartidos["lock"].acquire()
                if datosCompartidos['ack_expected'] == datosCompartidos['ack_received']:
                    f.write(data)
                    datosCompartidos['ack_received'] = not datosCompartidos['ack_received']
                    datosCompartidos['send_new'].set()
                datosCompartidos["lock"].release()
            except:
                continue

if len(sys.argv) != 6:
    print('Use: '+sys.argv[0]+' pack_sz filein fileout host port')
    sys.exit(1)
#obtenemos las variables de los argumentos
pack_sz = int(sys.argv[1])
filein = sys.argv[2]
fileout = sys.argv[3]


s = jsockets.socket_udp_connect(sys.argv[4], int(sys.argv[5]))
if s is None:
    print('could not open socket')
    sys.exit(1)

# Esto es para dejar tiempo al server para conectar el socket
s.send(b'hola')
s.recv(1024)

datosCompartidos = {
    'send_new': threading.Event(),
    'ack_received': True,
    'ack_expected': True,
    'lock': threading.Lock(),
}
datosCompartidos['send_new'].set()  # inicialmente permitir enviar
# thread para leer desde socket y escribir en fileout
newthread = threading.Thread(target=Rdr, args=(s, fileout, pack_sz, datosCompartidos))
newthread.start() # thread para escribir hacia socket

tiempo = time.time()
# En este otro thread leo desde filein hacia socket:
with open(filein, 'br') as f:
    data = f.read(pack_sz)
    while True:
        datosCompartidos['send_new'].wait(0.5) 
        datosCompartidos['lock'].acquire()
        if datosCompartidos['ack_expected'] == datosCompartidos['ack_received']:
            s.send(data)
        else:
            data = f.read(pack_sz)
            if not data:
                break
            s.send(data)
            datosCompartidos['ack_received'] = not datosCompartidos['ack_received']
        datosCompartidos['send_new'].wait()
        datosCompartidos['send_new'].clear()
        datosCompartidos['lock'].release()


newthread.join(timeout=0.8)
s.close()
print("Usando: pack:", pack_sz, "dist:", 1)
print('Tiempo total:', time.time()-tiempo)
os.kill(os.getpid(), signal.SIGKILL)