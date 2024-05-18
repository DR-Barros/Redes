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
            if datosCompartidos['finished'] and len(datosCompartidos['winSendNum']) == 0:
                break
            try:
                data=s.recv(pack_sz)
                if not data:
                    print('break')
                    break
                datosCompartidos['lock'].acquire()
                if int(data[:4]) in datosCompartidos['winRecvNum']:
                    datosCompartidos['winRecvData'][datosCompartidos['winRecvNum'].index(int(data[:4]))] = data[4:]
                    while datosCompartidos['winRecvData'][0] is not None:
                        f.write(datosCompartidos['winRecvData'][0])
                        datosCompartidos['winRecvData'].pop(0) # adelanto la ventana
                        datosCompartidos['winRecvNum'].pop(0) # adelanto la ventana
                        datosCompartidos['winSendNum'].pop(0) # emula el ACK del cliente
                        datosCompartidos['winSendData'].pop(0) # emula el ACK del cliente
                        datosCompartidos['winRecvData'].append(None) #adelanto la ventana
                        datosCompartidos['winRecvNum'].append((datosCompartidos['winRecvNum'][-1] + 1)%10000) #adelanto la ventana
                        datosCompartidos['min_send'] = (datosCompartidos['min_send'] + 1)%10000 #lleva el indice del minimo
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
winR = [None for i in range(win)]
winN = [i for i in range(win)]
datosCompartidos = {
    'send_new': threading.Event(),
    'lock': threading.Lock(),
    'min_send': 0,
    'winSendNum': [],
    'winSendData': [],
    'winRecvNum': winN,
    'winRecvData': winR,
    'finished': False
}
datosCompartidos['send_new'].set()  # inicialmente permitir enviar
# thread para leer desde socket y escribir en fileout
newthread = threading.Thread(target=Rdr, args=(s, fileout, pack_sz, datosCompartidos))
newthread.start() # thread para escribir hacia socket

tiempo = time.time()

# En este otro thread leo desde filein hacia socket:
with open(filein, 'br') as f:
    while not datosCompartidos['finished'] or len(datosCompartidos['winSendNum']) > 0:
        datosCompartidos['lock'].acquire()
        if not datosCompartidos['finished'] and len(datosCompartidos['winSendNum']) < win:
            data = f.read(pack_sz)
            if not data:
                datosCompartidos['finished'] = True
            else:
                s.send(str((datosCompartidos['min_send'] + len(datosCompartidos['winSendNum']))%10000).zfill(4).encode() + data)
                datosCompartidos['winSendNum'].append((datosCompartidos['min_send'] + len(datosCompartidos['winSendNum']))%10000)
                datosCompartidos['winSendData'].append(data)
        else:
            datosCompartidos['lock'].release()
            datosCompartidos['send_new'].wait(0.5)
            datosCompartidos['lock'].acquire()
            for i in range(win):
                if i < len(datosCompartidos['winSendNum']):
                    if datosCompartidos['winRecvData'][i] is None:
                        s.send(str(datosCompartidos['winSendNum'][i]).zfill(4).encode() + datosCompartidos['winSendData'][i])
                else:
                    break
        datosCompartidos['send_new'].clear()
        datosCompartidos['lock'].release()


newthread.join(timeout=0.8)
s.close()
print("Usando: pack:", pack_sz, "win:", sys.argv[2])
print('Tiempo total:', time.time()-tiempo)