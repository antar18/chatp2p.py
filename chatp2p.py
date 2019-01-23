#!/usr/bin/python
from socket import *
from threading import Thread
from sys import argv
from sys import stdin
from select import *
import re


#le code associe a chaque commande
START = "1120"
HELLO = "2120"
IPS = "3120"
PM = "4120"
BM = "5120"
#variables globales
nickname = ''
port = 1664
address = ''
socketCnx = socket()
liste_connexions = [] #liste des sockets connectees 
liste_ips=[] #liste des ips connectees
liste_nic=[] #liste des nicknames des utilisateurs connectees
liste_ban=[] #liste des utilisateurs bannis
bufferSize = 4096

#fonction qui permet d'extraire les donnees a partir d'un paquet recu sur une socket
def extraireMsg(data):
    if(len(data) <= 7) :
        raise ValueError("Les donnees recus sont de format incorrecte")
    return (data[5:len(data)-2].split('#'))[1].decode()
#fonction qui prend un des types messages predefinis , un message et une socket. 
#contruire le message et l'envoyer sur la socket passe en parametre 
def envoyerMsg(type,msg,skdest):
    if(type not in ["1120","2120","3120","4120","5120"]) :
        raise ValueError("Commande incorrect")
    if(msg=="") :
        raise ValueError("Message vide")
    #on envoie les donnees et on attend une reponse pour confirmer la reception des donnees
    skdest.send((type + "\001" + msg + "\r\n").encode())

#fonction qui permet d'ajouter les informations d'un nouveau utilisateur qui vient de se connecter pour permettre la connexion avec lui 
def ajouterUtilisateur(ip,sock,nic) :
    liste_ips.append(ip)
    liste_nic.append(nic)
    liste_connexions.append(sock)
    liste_ban.append(False)
#fonction qui prend un message et un nickname.
#Envoie un message prive sur l'ip qui correspond a ce nickname
def pm(nic,msg) :
    i = liste_nic.index(nic)
    if(i == -1) :
        raise ValueError("Nickname inexistant")
    if len(msg) == 0 :
        raise ValueError("Message Vide")
    if liste_ban[i] :
        raise ValueError("Destinataire banni")
    envoyerMsg(PM,"pm#" + msg,liste_connexions[i])
#fonction qui prend un message et l'envoie a tous les utilisateurs connectees sauf ceux qui sont bannis
def bm(msg) :
    if len(liste_nic) == 0 :
        raise ValueError("Pas de connexions actives")
    if len(msg) == 0 :
        raise ValueError("Message Vide")
    for s in liste_connexions :
	i = liste_connexions.index(s)		
	if not liste_ban[i] :
        	envoyerMsg(BM,"bm#" + msg,s)

    
#fonction qui permet de bannir un utilisateur 
def ban(nic) :
    i = liste_nic.index(nic)
    if(i == -1) :
        raise ValueError("Nickname inexistant")
    print("---" + nic + " banned---")
    liste_ban[i] = True
#fonction qui permet de retirer un utilisateur de la liste des bannis
def unban(nic):
    i = liste_nic.index(nic)
    if(i == -1) :
        raise ValueError("Nickname inexistant")
    print("---" + nic + " unbanned---")
    liste_ban[i] = False
#fonction qui permet de fermer toutes les connexions ouvertes
def quit(liste_connections) :
    for sx in liste_connections :
        sx.close()
#fonction qui permet de construire une liste d'ip a partir d'une chaine de caracteres
def construireListeIp(chaineIps) :
    #on filtre le message pour avoir une liste d'ips
    if len(chaineIps) > 4 :
        return chaineIps[1:len(chaineIps)-1].split(',')
    else :
        return []
#fonction qui permet de construire une chaine de caracteres a partir d'une liste d'ip
def construireChaineIp() :
    if len(liste_ips) == 0 :
        return "()"

    res = "("

    for ip in liste_ips :
        res = res + ip + ","
    return res[0:len(res) - 1] + ")"
#fonction qui permet de controller si les donnees au debut du programme sont correctes
def controlArguments() :
    l = len(argv)
    if l > 2 :
        raise ValueError("Nombre darguments incorrect")
    if l == 2 :
	#verification de la validite de l'adresse ip
        RegexIpv4Valide = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
        Ipv4Valide = re.match(RegexIpv4Valide,argv[1])
        if(not Ipv4Valide) :
            raise ValueError("format adresse ip incorrecte")
        return 2 
    return 1
    


#fonction permettant l'initialisation des parametres du programme et l'etablissement des connexions au lancement
def initialisation() :
    #recuperation du nickname a partir du console
    global nickname
    global liste_connexions
    nickname = raw_input("Donner votre nickname : ")
    #initialisation des parametres pour etablir la connexion
    #Si on donne une ip en argument
    if(controlArguments() == 2) :
        soc = socket()
	#soc.setsockopt(SOL_SOCKET,SO_REUSEADDR, 1)
        address = argv[1]
        print("Connexion en cours...")
        soc.connect((address,port))
        print("Connexion reussie")
	#Echange des nicknames
        envoyerMsg(START,"start#" + nickname,soc)
        data =  soc.recv(bufferSize) 
	d2 = data[data.index('\n') + 1 : len(data)] 
	d1 = data[0 : data.index('\n') + 1 ] 
	if len(d2) < 4 :
		d2 = soc.recv(bufferSize)        
	nic = extraireMsg(d1)
	#ajoute des donnees recus
        ajouterUtilisateur(address,soc,nic)
	#reception de la liste des ips des clients
        chaineIps = extraireMsg(d2)
        ips = construireListeIp(chaineIps)
	#connexion a chaque ip
        for ip  in ips : 
            ss = socket()
            ss.connect((ip,port))
            envoyerMsg(HELLO,"hello#" + nickname,ss)
            data = ss.recv(bufferSize)
            nic = extraireMsg(data)
            ajouterUtilisateur(ip,ss,nic)
    #Si on n'a pas donner une ip en argument
    else :
        print("En attente d'une connexion...")
	#En ecoute pour des connexions entrantes
        conn,(addr,pt) = socketCnx.accept()
        chaine_ips = construireChaineIp()
        data = conn.recv(bufferSize)
	#Si quelqu'un connecte on echange les donnees avec lui
        nic = extraireMsg(data)
        ajouterUtilisateur(addr,conn,nic)
        envoyerMsg(HELLO,"hello#" + nickname,conn)
        envoyerMsg(IPS,"ips#" + chaine_ips,conn)
        print(nic + " est connecte")


#fonction qui permet de supprimer tous les donnees d'un utilisateur a partir de son nickname

def deconnecterUtilisateur(nic) :
	i = liste_nic.index(nic)
	liste_connexions.pop(i)
	liste_ban.pop(i)
	liste_ips.pop(i)
	liste_nic.pop(i)
	print(nic + " a quitter.")



try :
    controlArguments()
    socketCnx.bind(('',port))
    socketCnx.listen(5)
    initialisation()
except Exception, e:
    print(e)
    exit()

while True :
	sockets = liste_connexions + [socketCnx,stdin] 
	lin,lout,lex = select(sockets,[],[])
	try :
		for s in lin :
		    #Si c'est quelqu'un qui essaie d'envoyer un message
		    if s in liste_connexions :
			#On recoit le message et on confirme la reception
			data = s.recv(bufferSize)
			#On verifie si ca correspond a un message ou c'est une deconnexion
			if data :			
				i = liste_connexions.index(s)
				#On verifie si l'utilisateur qui a envoyer ce message est banni et si ca correspond a un PM ou un BM
				if(not liste_ban[i]) :
					if(data[0:4] == PM) :
					    print("[prive]" +liste_nic[i] + ": " + extraireMsg(data))
					if(data[0:4] == BM) :
					    print("[public]" + liste_nic[i] + ": " + extraireMsg(data))
			else :
				deconnecterUtilisateur(liste_nic[liste_connexions.index(s)])
		    #Si c'est une nouvelle connexion
		    elif s == socketCnx :
			#On accepte la connexion et on echange les donnees
			sk,(adr,pr) = socketCnx.accept()
			chaine_ips = construireChaineIp()
			data = sk.recv(bufferSize)
			nic = extraireMsg(data)
			ajouterUtilisateur(adr,sk,nic)
			envoyerMsg(HELLO,"hello#" + nickname,sk)
			if data[0:4].decode() == START :
				envoyerMsg(IPS,"ips#" + chaine_ips,sk)
			print("\"" + nic + "\" est connecte")
		    else :
			#Si c'est une entree au console
			data = stdin.readline().strip("\n")
			#On verifie le type de cette entree et en traite chaque cas
			if data[0:2] == "pm":
				args = data.split(" ")
				if len(args) < 3 :
					raise ValueError("Utilisation incorrecte de la commande")
				else :		
					pm(args[1],data[4+len(args[1]):len(data)])
			elif data[0:2] == "bm" :
				args = data.split(" ")
				if len(args) < 2 :
					raise ValueError("Utilisation incorrecte de la commande")
				else :
					bm(data[3:len(data)])
			elif data[0:3] =="ban" : 
				args = data.split(" ")
				if len(args) != 2 :
					raise ValueError("Utilisation incorrecte de la commande")
				else :
					ban(args[1])
			elif data[0:5] == "unban" : 
				args = data.split(" ") 
				if len(args) != 2 :
					raise ValueError("Utilisation incorrecte de la commande")
				else :
					unban(args[1])
			elif data =="quit" :
				socketCnx.close()
				quit(liste_connexions)
				print("Connexion ferme")
				exit()
			else :
				raise ValueError("Commande incorrecte")
	except Exception, e:
		print(">>>Erreur : " + str(e))
		
			
