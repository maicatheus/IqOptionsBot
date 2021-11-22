from iqoptionapi.stable_api import IQ_Option
import time, json, logging, configparser,os
from datetime import datetime
from dateutil import tz
import threading
import sys, urllib.request
# DEBUG ira desativar o DEBUG, ERROR ira desativar qualquer mensagem de erro vindo da API(cuidado ao utilizar esta)


def banca():
	return API.get_balance()

def perfil(): # Função para capturar informações do perfil
	perfil = json.loads(json.dumps(API.get_profile_ansyc()))
	
	return perfil
	
	'''
		name
		first_name
		last_name
		email
		city
		nickname
		currency
		currency_char 
		address
		created
		postal_index
		gender
		birthdate
		balance		
	'''

def timestamp_converter(x): # Função para converter timestamp
	hora = datetime.strptime(datetime.utcfromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
	hora = hora.replace(tzinfo=tz.gettz('GMT'))
	
	return str(hora)[:-6]
	
def payout(par, timeframe = 1):
	a = API.get_all_profit()
	PAYOUT_BIN = int(100 * a[par]['binary'])
		
	API.subscribe_strike_list(par, timeframe)
	while True:
		d = API.get_digital_current_profit(par, timeframe)
		if d != False:
			d = int(d)
			break
		time.sleep(1)
	API.unsubscribe_strike_list(par, timeframe)
	PAYOUT_DIG = d

	return PAYOUT_BIN, PAYOUT_DIG

def IsOpen(asset):
	
	par = API.get_all_open_time()
	
	OPEN_BIN = par['binary'][asset]['open']
	OPEN_DIG = par['digital'][asset]['open']
	return OPEN_BIN, OPEN_DIG

def DigitalBuy(count,asset, entrada, direcao, timeframe,martingale):
	'''
	Retoran um valor win, loss ou equal e o valor de lucro 
	'''

	direcao = direcao.lower()
	# Martingale
	for i in range(0,martingale+1):
		# Entradas na digital
		_,id = API.buy_digital_spot(asset, entrada, direcao, timeframe)

		if isinstance(id, int):
			while True:
				status,lucro = API.check_win_digital_v2(id)
				if status:
					if lucro > 0:
						print(f'[SINAL {count}]RESULTADO: WIN / LUCRO: {str(round(lucro, 2))}')
					elif lucro <= 0:
						print(f'[SINAL {count}]RESULTADO: LOSS / LUCRO: -{str(entrada)}')
					break
			Stops(lucro)
			if lucro > 0:
				resultado = 'win'
				break
			elif lucro == 0:
				resultado = 'equal'
				lucro = 0
			elif lucro < 0:
				resultado = 'loose'
				lucro = entrada*(-1)
		entrada = entrada*int(configuracao('multiplicador_martingale'))
		print(f'[SINAL {count}] GALE {i+1}')

def BinaryBuy(count,asset, entrada, direcao, timeframe,martingale):
	#Entradas na binaria
	for i in range(0,martingale+1):
		status,id = API.buy(entrada, asset, direcao, timeframe)
		if status:
			lucro = API.check_win_v3(id)
			Stops(lucro)
			if lucro > 0:
				print(f'[SINAL {count}] RESULTADO: win / LUCRO: {str(round(lucro, 2))}')
				break
			if lucro < 0:
				print(f'[SINAL {count}] RESULTADO: loose / LUCRO: {str(round(lucro, 2))}')
				entrada = entrada*int(configuracao('multiplicador_martingale'))
				print(f'[SINAL {count}] GALE {i+1}')
			if lucro == 0:
				print(f'[SINAL {count}] RESULTADO: equal / LUCRO: {str(round(lucro, 2))}')
				break
	#return resultado, round(lucro,2)
global VALORATUAL
VALORATUAL = 0	
global STOP 
STOP = False	
def Stops(lucro):
	global VALORATUAL
	VALORATUAL += lucro
	if VALORATUAL >= int(configuracao('stop_win')):
		print(f'Bateu Stop Win com {VALORATUAL}')
		STOP=True
	if VALORATUAL <= int(configuracao('stop_loss'))*(-1):
		print(f'Bateu Stop Loss com {VALORATUAL}')
		STOP=True
	print(f'Lucro Obtido até o momento: {round(VALORATUAL,2)}\n')

def tendencia(asset,timeframe):
	velas = API.get_candles(asset, int(timeframe)* 60, 20,  time.time())
	ultimo = round(velas[0]['close'], 4)
	primeiro = round(velas[-1]['close'], 4)

	diferenca = abs( round( ( (ultimo - primeiro) / primeiro ) * 100, 3) )
	tendencia = "CALL" if ultimo < primeiro and diferenca > 0.01 else "PUT" if ultimo > primeiro and diferenca > 0.01 else False
	return str(tendencia)

def configuracao(data):
	arquivo = configparser.RawConfigParser()
	arquivo.read('config.txt')	
	d = arquivo.get('GERAL',data)
	return d
  
def carregar_sinais():
	'''
	Formato dos sinais
	25/10/2020;M5;EURJPY-OTC;11:50:00;PUT
	'''
	arquivo = open('sinais.txt', encoding='UTF-8')
	lista = arquivo.read()
	arquivo.close
	
	lista = lista.split('\n')
	
	for index,a in enumerate(lista):
		if a == '':
			del lista[index]
	return lista

def RodarSinais(count,hora,minuto,timeframe,acao,martingale,entrada,delay,asset):
	global STOP
	count = int(count)
	hora= int(hora)
	timeframe = int(timeframe)
	martingale = int(martingale)
	entrada = int(entrada)
	minuto= int(minuto)
	delay = int(delay)
	#print(data)
	#print(dataatual)
	asset = asset.upper()
	#if dataatual == data:
	#print('True')
	

	if minuto == 0:
		minuto = 59
		if hora == 0:
			hora =23
		if hora != 0:
			hora -=1
	elif minuto != 0:
		minuto -=1

	#print(f'sinal {count}hora:{hora}:{minuto}:{segundo}')
	VERIFY = False
	ENTRADA = False
	esperandoentrada =False
	while True:
		if STOP == True:
			break
		if esperandoentrada == False:
			print(f'[SINAL {count}] {asset} Esperando horário de entrada')
			esperandoentrada = True

		#print(hora,minuto)

		horaatual = time.localtime()[3]
		minutoatual = time.localtime()[4]
		segundoatual = time.localtime()[5]
		#print(f'{hora} {horaatual}, {minuto} {minutoatual}, {segundoatual}')
		if horaatual == hora and minutoatual == minuto and segundoatual > (10- delay) and VERIFY == False:
			VERIFY = True
			print(f'[SINAL {count}] {asset} Verificando se o ativo está aberto')
			OPEN_BIN, OPEN_DIG = IsOpen(asset)
			PAYOUT_BIN, PAYOUT_DIG = payout(asset,timeframe)
			print(f'[SINAL {count}] {asset} Verificando Tendencia')
			TENDENCIA = tendencia(asset,timeframe)
			print(f'[SINAL {count}] {asset} Tendencia {TENDENCIA}')
			if acao.upper() != TENDENCIA:
				print(f'[SINAL {count}] Sinal contra tendencia, SAINDO..')
				break

			print(f'[SINAL {count}] {asset} payout bin {PAYOUT_BIN}, payout dig {PAYOUT_DIG}')
			if OPEN_BIN == True and PAYOUT_BIN > PAYOUT_DIG:
				tipo = 'binary'
				payoutescolhido = PAYOUT_BIN
			elif OPEN_DIG == True and PAYOUT_BIN < PAYOUT_DIG:
				tipo = 'digital'
				payoutescolhido = PAYOUT_DIG
			elif OPEN_BIN == True:
				tipo = 'binary'
				payoutescolhido = PAYOUT_BIN
			elif OPEN_DIG == True:
				tipo = 'digital'
				payoutescolhido = PAYOUT_DIG
			print(f'[SINAL {count}] {asset} {tipo.upper()} Melhor payout: {payoutescolhido}')
			ENTRADA=True
		if horaatual == hora and minutoatual == minuto and segundoatual > (59 - delay) and ENTRADA == True:
			
			#------------------------------#
			#------ EFETUAR ENTRADA -------#
			#------------------------------#


			print(f'[SINAL {count}] - ENTROU')
			
			if tipo == 'binary':
				BinaryBuy(count,asset, entrada, acao, timeframe,martingale)
			elif tipo =='digital':
				DigitalBuy(count,asset,entrada,acao,timeframe,martingale)
			break
		time.sleep(1)
	print(f'[SINAL {count}] {asset} Finalizado!')


username = configuracao('seu_email_da_iq')
password = configuracao('sua_senha_da_iq')
try:
	with urllib.request.urlopen('http://35.247.242.142/api/json') as f:
  		data = json.load(f)
except:
	print('Falha na internet, verifique sua conexão.')
	os.system('pause')
	sys.exit()

liberado = False
for i in range(0,len(data)):
	#if username == data[i]['email'] and user_licenca == data[i]['email']   Melhor método, porém o email temq ue ser igual o da IQ
	if data[i]['licenca'] == configuracao('licenca'):
		liberado = True
if liberado == False:
	print('Falha de autenticação, verifique sua licença está válida!')
	os.system('pause')
	sys.exit()

print('Licença Ativa!\n')
logging.disable(level=(logging.DEBUG))
API = IQ_Option(username, password)
API.connect()

try:
	if configuracao('tipo_conta').upper() == "REAL":
		CONTA = 'REAL'
	elif configuracao('tipo_conta').upper() == "TREINAMENTO":
		CONTA =	'PRACTICE'
	API.change_balance(CONTA) # PRACTICE / REAL
except:
	print('**ERRO**\n Escolha um tipo de conta para operar')
	os.system('pause')
	sys.exit()
while True:
	if API.check_connect() == False:
		print('**Erro ao se conectar**\n\n')
		API.connect()
	else:
		print('Conectado com sucesso\n\n\n')
		break
	
	time.sleep(1)

#print(json.dumps(carregar_sinais(), indent=1))

lista = carregar_sinais()
count = 1
for sinal in lista:
	#M1;EURUSD-OTC;20:44;PUT;1G
	dados = sinal.split(';')
	asset = dados[1]
	aux = dados[2] #horário
	aux	= aux.split(':')
	hora = aux[0]
	minuto = aux[1]
	timeframe = dados[0]
	timeframe=timeframe[1:]
	acao = dados[3]
	martingale = dados[4]
	martingale = martingale[0:-1]
	thread = threading.Thread(target = RodarSinais, args = (count,hora, minuto, timeframe, acao, martingale,configuracao('valor_entrada'),configuracao('delay'),asset))	
	thread.start()
	count += 1
input('')
