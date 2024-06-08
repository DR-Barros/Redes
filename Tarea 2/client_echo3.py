#!/usr/bin/python3
# Echo client program
# Version con dos threads: uno lee de stdin hacia el socket y el otro al revés
import jsockets
import sys, threading
import time

def Rdr(s, fileout):
    with open(fileout, 'wb') as f:
        while True:
            data = s.recv(1500)
            if not data:
                break
            f.write(data)


if len(sys.argv) != 5:
    print('Use: '+sys.argv[0]+' filein fileout host port')
    sys.exit(1)

s = jsockets.socket_tcp_connect(sys.argv[3], int(sys.argv[4]))
filein = sys.argv[1]
fileout = sys.argv[2]
if s is None:
    print('could not open socket')
    sys.exit(1)

# Creo thread que lee desde el socket hacia stdout:
newthread = threading.Thread(target=Rdr, args=(s, fileout))
newthread.start()

# En este otro thread leo desde filein hacia el socket:
tiempo_inicial = time.time()
with open(filein, 'br') as f:
    while True:
        data = f.read(1500)
        if not data:
            break
        s.send(data)

time.sleep(3)  # dar tiempo para que vuelva la respuesta
print('Fin del cliente')
print('Tiempo total:', time.time() - tiempo_inicial)
s.close()

