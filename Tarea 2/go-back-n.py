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
                datosCompartidos['lock'].acquire()
                if int(data[:4]) == datosCompartidos['min_send']:
                    f.write(data[4:])
                    datosCompartidos['ventana'].pop(0)
                    datosCompartidos['min_send'] = (datosCompartidos['min_send'] + 1)%10000
                    datosCompartidos['send_new'].set()
                datosCompartidos['lock'].release()
            except:
                continue

if len(sys.argv) != 7:
    print('Use: '+sys.argv[0]+' pack_sz win filein fileout host port')
    sys.exit(1)
#obtenemos las variables de los argumentos
pack_sz = int(sys.argv[1])
win = int(sys.argv[2])
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
    'send_new': threading.Event(),
    'min_send': 0, # numero entre 0 y 9999
    'lock': threading.Lock(),
    'ventana' : []
}
datosCompartidos['send_new'].set()  # inicialmente permitir enviar
# thread para leer desde socket y escribir en fileout
newthread = threading.Thread(target=Rdr, args=(s, fileout, pack_sz, datosCompartidos))
newthread.start() # thread para escribir hacia socket

tiempo = time.time()

finished = False
# En este otro thread leo desde filein hacia socket:
with open(filein, 'br') as f:
    while not finished or len(datosCompartidos['ventana']) > 0:
        datosCompartidos['send_new'].wait(0.5) 
        datosCompartidos['lock'].acquire()
        if not finished and len(datosCompartidos['ventana']) < win:
            data = f.read(pack_sz)
            if not data:
                finished = True
            else:
                s.send(str((datosCompartidos['min_send'] + len(datosCompartidos['ventana']))%10000).zfill(4).encode() + data)
                datosCompartidos['ventana'].append(data)
        else:
            for i in range(win):
                if i < len(datosCompartidos['ventana']):
                    s.send(str((datosCompartidos['min_send'] + i)%10000).encode() + datosCompartidos['ventana'][i])
                else:
                    break
        datosCompartidos['send_new'].wait()
        datosCompartidos['send_new'].clear()
        datosCompartidos['lock'].release()



newthread.join(timeout=0.8)
s.close()
print("Usando: pack:", pack_sz, "win:", sys.argv[2])
print('Tiempo total:', time.time()-tiempo)
os.kill(os.getpid(), signal.SIGKILL)