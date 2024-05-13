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
                with datosCompartidos['lock']:
                    #si el dato recibido esta dentro de la ventana, se guarda en el arreglo de recepcion
                    # y si es el esperado(min_send), se escribe en el archivo y se avanza la ventana
                    if int(data[:4]) in datosCompartidos['winN']:
                        datosCompartidos['winR'][datosCompartidos['winN'].index(int(data[:4]))] = data[4:]
                        while datosCompartidos['winR'][0] is not None:
                            f.write(datosCompartidos['winR'][0])
                            datosCompartidos['winR'].pop(0)
                            datosCompartidos['winN'].pop(0)
                            datosCompartidos['winR'].append(None)
                            datosCompartidos['winN'].append((datosCompartidos['winN'][-1] + 1)%10000)
                            datosCompartidos['min_send'] = (datosCompartidos['min_send'] + 1)%10000
                        datosCompartidos['send_new'].set()
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
    'winS' : [], # ventana de envio
    'winR' : [None for i in range(win)], # ventana de recepcion con win elementos
    'winN' : [i for i in range(win)], # numeros de secuencia de la ventana de recepcion
}
datosCompartidos['send_new'].set()  # inicialmente permitir enviar
# thread para leer desde socket y escribir en fileout
newthread = threading.Thread(target=Rdr, args=(s, fileout, pack_sz, datosCompartidos))
newthread.start() # thread para escribir hacia socket

tiempo = time.time()

finished = False
# En este otro thread leo desde filein hacia socket:
with open(filein, 'br') as f:
    while not finished or len(datosCompartidos['winS']) > 0:
        datosCompartidos['send_new'].wait(0.5) 
        with datosCompartidos['lock']:
            if not finished and len(datosCompartidos['winS']) < win:
                data = f.read(pack_sz)
                if not data:
                    finished = True
                else:
                    s.send(str((datosCompartidos['min_send'] + len(datosCompartidos['winS']))%10000).zfill(4).encode() + data)
                    print('enviado:', (datosCompartidos['min_send'] + len(datosCompartidos['winS']))%10000)
                    datosCompartidos['winS'].append(data)
            else:
                print('ventana llena')
                for i in range(win):
                    if i < len(datosCompartidos['winS']):
                        # chequeo si el paquete no se ha llegado, se reenvia
                        if datosCompartidos['winR'][i] is not None:
                            s.send(str((datosCompartidos['min_send'] + i)%10000).encode() + datosCompartidos['winS'][i])
                    else:
                        break
            datosCompartidos['send_new'].wait()
            datosCompartidos['send_new'].clear()



newthread.join(timeout=0.8)
s.close()
print("Usando: pack:", pack_sz, "win:", sys.argv[2])
print('Tiempo total:', time.time()-tiempo)
os.kill(os.getpid(), signal.SIGKILL)