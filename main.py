'''
The portion of the code connecting to the wifi network is from "Connecting to 
the Internet with Raspberry Pi Pico" 
Chapter 3. Getting on the internet with MicroPython
Copyright © 2022 Raspberry Pi Ltd

From the line
...#### SRSS_SENEFFE ####...
mibradoc@gmail.com
Seneffe, Belgium

2023.02.18

'''

from utime import time,gmtime,sleep,localtime
import machine
import network
import socket
import struct
import personal # fichier perso avec ssid et mot de passe wifi

NTP_DELTA = 2208988800
host = "pool.ntp.org"

led = machine.Pin("LED", machine.Pin.OUT)

def set_time():
	NTP_QUERY = bytearray(48)
	NTP_QUERY[0] = 0x1B
	addr = socket.getaddrinfo(host, 123)[0][-1]
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		s.settimeout(1)
		res = s.sendto(NTP_QUERY, addr)
		msg = s.recv(48)
	finally:
		s.close()
	val = struct.unpack("!I", msg[40:44])[0]
	t = val - NTP_DELTA    
	tm = gmtime(t)
	machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(personal.ssid,personal.password)

max_wait = 10
while max_wait > 0:
	if wlan.status() < 0 or wlan.status() >= 3:
		break
	max_wait -= 1
	print('waiting for connection...')
	sleep(1)

if wlan.status() != 3:
	raise RuntimeError('network connection failed')
else:
	print('connected')
	status = wlan.ifconfig()
	print( 'ip = ' + status[0] )

led.on()
sleep(3)
set_time()

led.off()
sleep(1)

###################################    SRSS_SENEFFE    ###############################################

# Le Pico est à l'heure, le programme peut commencer:
# DÉBUT DU CODE PRINCIPAL:

# Notifier par un clignotement lent de 4 allumages (--- --- --- ---) que le pico démarre la séquence srss proprement dite
for i in range(4):
	led.on()
	sleep(.5)
	led(0)
	sleep(.5)

# UN NOM UNIQUE POUR LE FICHIER ".log" est assigné à la variable "logfile":
logfile='srss.log_'+str(int(time()))  

# LE FICHIER ".log" EST CRÉÉ:
with open (logfile,'w')as fi:
	pass

# CRÉATION DES FONCTIONS PROPRES:
def writelog(msg):
	with open(logfile,'a')as fi:
		fi.write(msg+"\r\n")

writelog("START")
writelog(str(time()))
writelog(str(localtime()))

def toEpoch(year,yearday): # prend les données directement ds le fichier srss.dta (pas ds le dico srssD) 
	epochsr=0
	epochss=0
	secondsToNow=0	
	# Ajouter les secondes dans les années complètes écoulées depuis le 1er janvier 1970 à O heures
	for y in range(1970,year):
		secondsToNow += 366*86400 if y%4==0 and y%100!=0 or y%400==0 else 365*86400
	# Ajouter les secondes des jours complets écoulés dans l'année en cours
	secondsToNow += (yearday-1)*86400
	
	with open('srss.dta')as fi:
		for j in range(0,1463,4):
			l=[]
			for x in range(4):
				l.append(int(fi.readline()[:-1]))
			# l est ici 1 liste de 4 items : heures et minutes du lever puis du coucher pour le jour yearday 
			if j//4+1 == yearday: 
				# Ajouter les secondes et les minutes de l'heure du lever
				epochsr += secondsToNow+l[0]*3600+l[1]*60
				# Ajouter les secondes et les minutes de l'heure du coucher
				epochss += secondsToNow+l[2]*3600+l[3]*60
				break # quitter la boucle "for j in range(0,1463,4):"
	return (epochsr,epochss)

# ENREGISTREMENT DU TEMPS EPOCH DE L'HEURE DU LANCEMENT DU PROGRAMME ET DES VALEURS DÉRIVÉES 
starttime = time()
startgmtime = gmtime(starttime) # heure de lancement, au format tuple
year = startgmtime[0]
numjour = startgmtime[7]
writelog(str(starttime)+" - "+str(startgmtime)+" - "+str(year)+" - "+str(numjour))

# BOUCLE SLEEP  
latyStart = False
boucle=0
while True:
	boucle +=1
	writelog('boucle '+str(boucle))
	yearlength = 366 if year%4==0 and year%100!=0 or year%400==0 else 365
	sr_epoch=toEpoch(year,numjour)[0]
	ss_epoch=toEpoch(year,numjour)[1]
	writelog('Calcul des temps époch (sr_epoch et ss_epoch) dans la boucle n°'+str(boucle))
	writelog(str(sr_epoch)+' '+str(ss_epoch))
	if year == startgmtime[0] and numjour == startgmtime[7]: # Première itération dans la boucle
		if starttime < sr_epoch: # Lancement après minuit, avant le lever du soleil:
			led.on()
			writelog("la led s'allume (lancement après minuit, avant le lever du soleil)")
			writelog("sleeping "+str(sr_epoch)+" - "+str(starttime)+ " seconds")
			sleep(sr_epoch - starttime)
			led.toggle()
			writelog("led toggle - lever du soleil "+str(sr_epoch))
			writelog("sleeping "+str(ss_epoch)+' - '+str(sr_epoch)+ " seconds")
			sleep(ss_epoch - sr_epoch)
			led.toggle()
			writelog("led toggle - coucher du soleil "+str(ss_epoch))
			
		if sr_epoch < starttime < ss_epoch: # Lancement entre le lever et le coucher du soleil:
			led(0)
			writelog("la led s'éteint (lancement entre le lever et le coucher du soleil)")
			writelog("sleeping "+str(ss_epoch)+' - '+str(starttime)+ " seconds")
			sleep(ss_epoch - starttime)
			led.toggle()
			writelog("led toggle - coucher du soleil "+str(ss_epoch))
		
		if starttime > ss_epoch: # Lancement après le coucher du soleil, avant minuit:
			led.on()
			writelog("la led s'allume (lancement après le coucher du soleil, avant minuit)")
			latyStart=True
			
	else:
		writelog("*") 
		if latyStart:
			writelog("sleeping "+str(sr_epoch)+" - "+str(starttime)+ " seconds")
			sleep(sr_epoch - starttime)
			latyStart=False
		else:
			writelog("sleeping "+str(sr_epoch)+" - "+str(yesterday_ss_epoch)+ " seconds")
			sleep(sr_epoch - yesterday_ss_epoch)
		led.toggle()
		writelog("led toggle - lever du soleil "+str(sr_epoch))
		writelog("sleeping "+str(ss_epoch)+" - "+str(sr_epoch)+ " seconds")
		sleep(ss_epoch - sr_epoch)
		led.toggle()
		writelog("led toggle - coucher du soleil "+str(ss_epoch))
		writelog('**')
	
	yesterday_ss_epoch = ss_epoch
	writelog("yesterday_ss_epoch =  "+str(yesterday_ss_epoch))
	
	if numjour == yearlength:
		year += 1
		numjour=0
        
	numjour += 1
	writelog("next loop - numjour =  "+str(numjour))

## END CODE


