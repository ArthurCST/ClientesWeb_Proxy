# coding: utf-8

import random
import math
import simpy


#parametros
mss = 1460 #Tamanho máximo do segmento TCP
ovhdTCP = 20 #overhead TCP
ovhdIP = 20 #overhead IP
ovhdFrame = 18 #overhead Frame
larguraBanda = 10 #Mbps
latenciaRot = 50 #us
larguraBandaLink = 0.056 #Mbps
taxaDadosDoc = 20 #KBps
rtt = 100 #ms
taxabrowser = 0.3 #pedidos/segundo
numClientes = 150
porcetangemAtiva = 0.1
reqHttp = 290 #tamanho médio da requisição HTTP


#retorna o número de datagramas necessários para enviar uma mensagem com m bytes
def nDatagramas(m):
    return math.ceil(m/mss)

#calculo do overhead por mensagem
def overhead(m):
    return nDatagramas(m)*(ovhdTCP+ovhdIP+ovhdFrame)

#tempo gasto por uma mensagem na rede de tamanho m bytes em uma rede com largura b Mbps
def tempoRede(m,b):
    return 8*(m+overhead(m))/(1000000*b)

#gera um documento com tamanho aleatorio
def tamanhoDoc():
    r=random.random()
    if r<0.35:
        return 0.8
    if r<0.85:
        return 5.5
    if r<0.99:
        return 80
    return 800

#Classe principal da simulação.
class Web(object):
    def __init__(self, env, num_lan, num_linkSai , num_linkEnt):
        self.env = env
        self.qlanReq = simpy.Resource(env,num_lan)
        self.qlinkSai = simpy.Resource(env,num_linkSai)
        self.qlinkEnt = simpy.Resource(env, num_linkEnt)

    #Serviço LAN HTTP Request
    def lanReq(self, cliente,tamDoc):
        yield self.env.timeout(tempoRede(reqHttp,larguraBanda))

    #Serviço Roteador
    def rotReq(self, cliente, tamDoc):
        yield self.env.timeout(latenciaRot/1000000)

    #Serviço Link de Saída
    def linkSai(self,cliente):
        yield self.env.timeout(tempoRede(reqHttp,larguraBandaLink)+3*tempoRede(0.00001,larguraBandaLink))

    #Serviço ISP
    def isp(self,cliente, tamDoc):
        yield self.env.timeout((2*rtt/1000)+(tamDoc/taxaDadosDoc))

    #Serviço Link Entrada
    def linkEnt(self, cliente, tamDoc):
        yield self.env.timeout(tempoRede(tamDoc*1024,larguraBandaLink)+2*tempoRede(0.00001,larguraBandaLink))

    #Serviço Roteador Resposta
    def rotResp(self, cliente, tamDoc):
        yield self.env.timeout((nDatagramas(tamDoc*1024)+5)*latenciaRot/1000000)

    #Serviço LAN Resposta Servidor -> Navegador
    def lanResp(self, cliente, tamDoc):
        yield self.env.timeout(tempoRede(tamDoc*1024,larguraBanda))


def cliente(env, nome, web):
    #variaveis globais
    global TOTAL_ARRIVALS
    global TOTAL_DEPARTURES
    global TOTAL_SERVICE_TIME_LAN
    global TOTAL_WAIT_TIME_LAN
    global TOTAL_SERVICE_TIME_ROT
    global TOTAL_SERVICE_TIME_LS
    global TOTAL_WAIT_TIME_LS
    global TOTAL_SERVICE_TIME_ISP
    global TOTAL_SERVICE_TIME_LE
    global TOTAL_WAIT_TIME_LE
    global CURRENT_Q_LAN
    global LONGEST_Q_LAN
    global CURRENT_Q_LINKSAIDA
    global LONGEST_Q_LINKSAIDA
    global CURRENT_Q_LINKENTRADA
    global LONGEST_Q_LINKENTRADA

    #variaveis auxiliares para cálculo de estatisticas
    AUX_SERVICE_TIME_LAN = 0
    AUX_WAIT_TIME_LAN = 0
    AUX_SERVICE_TIME_ROT = 0
    AUX_SERVICE_TIME_LS = 0
    AUX_WAIT_TIME_LS = 0
    AUX_SERVICE_TIME_ISP = 0
    AUX_SERVICE_TIME_LE = 0
    AUX_WAIT_TIME_LE = 0
    startService = 0
    startWait = 0

    TOTAL_ARRIVALS += 1
    tamDoc = tamanhoDoc()
    #tamDoc = 22.23
    print('cliente %s entra no tempo %.2f com documento de tamanho %f.' % (nome, env.now,tamDoc))

    startWait = env.now;
    CURRENT_Q_LAN += 1
    if CURRENT_Q_LAN > LONGEST_Q_LAN:
        LONGEST_Q_LAN = CURRENT_Q_LAN

    with web.qlanReq.request() as request_lan:#fila na lan requisição
        yield request_lan
        #cliente sera servido
        AUX_WAIT_TIME_LAN += env.now - startWait;
        CURRENT_Q_LAN -= 1

        startService = env.now
        yield env.process(web.lanReq(nome,tamDoc))
        AUX_SERVICE_TIME_LAN += env.now - startService
        print('cliente %s servido na lan tempo %.2f.' % (nome, env.now))

    startService = env.now
    yield env.process(web.rotReq(nome, tamDoc))#delay roteador
    AUX_SERVICE_TIME_ROT += env.now - startService
    print('cliente %s servido pelo roteador tempo %.2f.' % (nome, env.now))

    startWait = env.now;
    CURRENT_Q_LINKSAIDA += 1
    if CURRENT_Q_LINKSAIDA > LONGEST_Q_LINKSAIDA:
        LONGEST_Q_LINKSAIDA = CURRENT_Q_LINKSAIDA

    with web.qlinkSai.request() as request_linkSai:#fila na lan requisição
        yield request_linkSai
        #cliente servido no link de saida
        AUX_WAIT_TIME_LS += env.now - startWait;
        CURRENT_Q_LINKSAIDA -= 1

        startService = env.now
        yield env.process(web.linkSai(nome))
        AUX_SERVICE_TIME_LS += env.now - startService
        print('cliente %s servido no link de saida tempo %.2f.' % (nome, env.now))

    startService = env.now
    yield env.process(web.isp(nome, tamDoc))#delay internet
    AUX_SERVICE_TIME_ISP += env.now - startService
    print('cliente %s servido no isp tempo %.2f.' % (nome, env.now))

    startWait = env.now;
    CURRENT_Q_LINKENTRADA += 1
    if CURRENT_Q_LINKENTRADA > LONGEST_Q_LINKENTRADA:
        LONGEST_Q_LINKENTRADA = CURRENT_Q_LINKENTRADA

    with web.qlinkEnt.request() as request_linkEnt:#fila na lan requisição
        yield request_linkEnt
        #cliente servido no link de entrada
        AUX_WAIT_TIME_LE += env.now - startWait;
        CURRENT_Q_LINKENTRADA -= 1

        startService = env.now
        yield env.process(web.linkEnt(nome, tamDoc))
        AUX_SERVICE_TIME_LE += env.now - startService
        print('cliente %s servido no link de entrada tempo %.2f.' % (nome, env.now))

    startService = env.now
    yield env.process(web.rotResp(nome, tamDoc))
    AUX_SERVICE_TIME_ROT += env.now - startService
    print('cliente %s servido no roteador (resposta) tempo %.2f.' % (nome, env.now))

    startWait = env.now;
    CURRENT_Q_LAN += 1
    if CURRENT_Q_LAN > LONGEST_Q_LAN:
        LONGEST_Q_LAN = CURRENT_Q_LAN

    with web.qlanReq.request() as request_lan:#fila na lan resposta
        yield request_lan
        #cliente sera servido
        AUX_WAIT_TIME_LAN += env.now - startWait;
        CURRENT_Q_LAN -= 1

        startService = env.now
        yield env.process(web.lanResp(nome,tamDoc))
        AUX_SERVICE_TIME_LAN += env.now - startService
        print('cliente %s servido na lan (resposta) tempo %.2f.' % (nome, env.now))

    print('cliente %s saiu no tempo %.2f.' % (nome, env.now))
    TOTAL_DEPARTURES += 1

    #Adiciona o valor dos tempos de serviço e espera do cliente em cada recurso às variáveis globais de estatística
    TOTAL_SERVICE_TIME_LAN += AUX_SERVICE_TIME_LAN
    TOTAL_WAIT_TIME_LAN += AUX_WAIT_TIME_LAN
    TOTAL_SERVICE_TIME_ROT += AUX_SERVICE_TIME_ROT
    TOTAL_SERVICE_TIME_LS += AUX_SERVICE_TIME_LS
    TOTAL_WAIT_TIME_LS += AUX_WAIT_TIME_LS
    TOTAL_SERVICE_TIME_ISP += AUX_SERVICE_TIME_ISP
    TOTAL_SERVICE_TIME_LE += AUX_SERVICE_TIME_LE
    TOTAL_WAIT_TIME_LE += AUX_WAIT_TIME_LE

    """
    with web.qlanResp.request() as request_lanr:#fila na lan requisição
        yield request_lanr
        yield env.process(web.lanResp(nome, tamDoc))
        print('cliente %s saiu no tempo %.2f.' % (nome, env.now))    """

def setup(env, num_lan, num_linkSai , num_linkEnt ):
    web = Web(env, num_lan, num_linkSai , num_linkEnt)
    i = 0
    while 1:
        yield env.timeout(0.2)
        i += 1
        env.process(cliente(env, '%d' % i, web))
    #cria cliente

"""Variáveis de estatística"""
TOTAL_ARRIVALS = 0 #Numero de chegadas
TOTAL_DEPARTURES = 0 #numero de saidas
TOTAL_SERVICE_TIME_LAN = 0 #tempo total de serviço LAN
TOTAL_WAIT_TIME_LAN = 0 #tempo total de espera LAN
TOTAL_SERVICE_TIME_ROT = 0 #tempo total de serviço Roteador
TOTAL_SERVICE_TIME_LS = 0 #tempo total de serviço Link de Saída
TOTAL_WAIT_TIME_LS = 0 #tempo total de espera Link de Saida
TOTAL_SERVICE_TIME_ISP = 0 #tempo total de serviço ISP
TOTAL_SERVICE_TIME_LE = 0 #tempo total de serviço Link de Entrada
TOTAL_WAIT_TIME_LE = 0 #tempo total de espera Link de Entrada
CURRENT_Q_LAN = 0 #tamanho atual da fila LAN
LONGEST_Q_LAN = 0 #tamanho da maior fila LAN
CURRENT_Q_LINKSAIDA = 0 #tamanho atual da fila Link de Saida
LONGEST_Q_LINKSAIDA = 0 #tamanho da maior da fila Link de Saida
CURRENT_Q_LINKENTRADA = 0 #tamanho atual da fila Link de Entrada
LONGEST_Q_LINKENTRADA = 0 #tamanho da maior da fila Link de Entrada


SIM_TIME = 12
NUM_LINKSAI= 1
NUM_LAN  = 1
NUM_LINKENT = 1
random.seed(120)

env = simpy.Environment()
env.process(setup(env, NUM_LAN, NUM_LINKSAI , NUM_LINKENT ))
env.run(until = SIM_TIME)

"""Tempos totais de residência para cada recurso"""
TOTAL_RESIDENCE_TIME_LAN = TOTAL_SERVICE_TIME_LAN + TOTAL_WAIT_TIME_LAN
TOTAL_RESIDENCE_TIME_LS = TOTAL_SERVICE_TIME_LS + TOTAL_WAIT_TIME_LS
TOTAL_RESIDENCE_TIME_ISP = TOTAL_SERVICE_TIME_ISP
TOTAL_RESIDENCE_TIME_LE = TOTAL_SERVICE_TIME_LE + TOTAL_WAIT_TIME_LE
TOTAL_RESIDENCE_TIME = TOTAL_RESIDENCE_TIME_LAN+TOTAL_SERVICE_TIME_ROT+TOTAL_RESIDENCE_TIME_ISP + TOTAL_RESIDENCE_TIME_LS+TOTAL_RESIDENCE_TIME_LE

"""Relatório estatístico"""
print("ESTATISTICAS GERAIS")
print("Total chegadas %d"%TOTAL_ARRIVALS)
print("Total saidas %d"%TOTAL_DEPARTURES)
print("Tempo de residencia LAN %f"%TOTAL_RESIDENCE_TIME_LAN)
print("Tempo de residencia Roteador %f"%TOTAL_SERVICE_TIME_ROT)
print("Tempo de residencia Link de Saída %f"%TOTAL_RESIDENCE_TIME_LS)
print("Tempo de residencia Internet %f"%TOTAL_SERVICE_TIME_ISP)
print("Tempo de residencia Link de Entrada %f"%TOTAL_RESIDENCE_TIME_LE)
print("Tempo de residencia total %f"%TOTAL_RESIDENCE_TIME)
print("Utilização LAN %f"%(TOTAL_RESIDENCE_TIME_LAN/TOTAL_RESIDENCE_TIME*100))
print("Utilização Roteador %f"%(TOTAL_SERVICE_TIME_ROT/TOTAL_RESIDENCE_TIME*100))
print("Utilização Link de Saída %f"%(TOTAL_RESIDENCE_TIME_LS/TOTAL_RESIDENCE_TIME*100))
print("Utilização Internet %f"%(TOTAL_RESIDENCE_TIME_ISP/TOTAL_RESIDENCE_TIME*100))
print("Utilização Link de Entrada %f"%(TOTAL_RESIDENCE_TIME_LE/TOTAL_RESIDENCE_TIME*100))
print("Taxa de Processamento: %f"%(TOTAL_DEPARTURES/TOTAL_RESIDENCE_TIME))
