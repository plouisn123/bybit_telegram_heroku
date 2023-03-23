import requests
import ccxt

##Bybit V2 API
exchange = ccxt.bybit({
    'apiKey': 'WOulQursvU7gL5a3rC',
    'secret': 'Ccwr5oBFJNDUO54NSDmypqn4776Tv58IorLj', 
})

bot_token = '5704355843:AAHk0C4706h3Kn3X8KvF0ZQah-DmkqSB6o4'
channel_id = '@ceinturionskatana'


##Récupère le message dans le canal télégram
last_update_id = 0
dico  = {}
while True:
    response = requests.get(f"https://api.telegram.org/bot5704355843:AAHk0C4706h3Kn3X8KvF0ZQah-DmkqSB6o4/getUpdates?offset={last_update_id+1}&allowed_updates=[\"channel_post\"]").json()
    updates = response["result"]
    for update in updates:
        if "channel_post" in update and "text" in update["channel_post"]:
            message = update["channel_post"]["text"]
            text = message
            last_update_id = update["update_id"]
        else:
            text = ''

        ##Extraction et traitement des données
        if "TP :" in text and "SL :" in text and "Prix" in text and exchange.fetch_balance()['USDT']['free'] > 2:
            
            #LONG or SHORT
            start = text.find("(")
            end = text.find(")", start)
            if start != -1 and end != -1:
                L_S = text[start+1:end]
                BorS = 'Buy' if L_S == 'LONG' else 'Sell'
                close = 'Buy' if BorS == 'Sell' else 'Sell'
                print('Side:',BorS)
                #print(type(BorS))
                #print(type(close))
        
            #Paire    
            start = text.find("")
            end = start + 1
            while end < len(text) and (text[end].isalpha()):
                end += 1
            crypto = text[start+1:end]
            symbol = crypto+'USDT'
            print('Paire:',symbol)
            #print(type(symbol))
            #print(type(crypto))

            #Prix entrée n°1    
            start = text.find("entré")
            end = text.find("-", start)
            if start != -1 and end != -1:
                PE11 = text[start+8:end]
                if ',' in PE11:
                    PE1 = float(PE11.replace(",", "."))
                else:
                    PE1 = float(PE11)
            #print(PE1)

            #Prix d'entrée n°2  
            start = text.find("-")
            end = start + 2
            while end < len(text) and (text[end].isdigit() or text[end] == ","):
                end += 1
            PE22 = text[start+1:end]
            if ',' in PE22:
                PE2 = float(PE22.replace(",", "."))
            else:
                PE2 = float(PE22)
            #print('Prix Entrée 2:',PE2)

            #TP n°i    
            start = text.find("TP")
            end = text.find(" SL", start)
            if start != -1 and end != -1:
                TP = text[start+6:end-3]        
                TPs = TP.split("\n")
                if ',' in TP[2]:
                    TPs[2] = float(TPs[2].replace(",", "."))
                else:
                    TPs[2] = float(TPs[2])
                print('Take Profit:',TPs[2])
                #print(type(TPs[2]))

            #SL    
            start = text.find("SL")
            end = start + 6
            while end < len(text) and (text[end].isdigit() or text[end] == ","):
                end += 1
            SLL = text[start+5:end]
            print('SLL:',SLL)
            if ',' in SLL:
                SL = float(SLL.replace(",", "."))
            else:
                SL = float(SLL)
            print('StopLoss:',SL)
            #print(type(SL))
                
            #Prix d'entrée
            last_price = exchange.fetch_ticker(symbol)['last'] # recupère le dernier prix
            nb_decimals = len(str(last_price)) - str(last_price).index('.') - 1
            index = str(last_price).find('.')
            if PE1 < last_price < PE2:
                if index == -1: #est ce que le prix de la crypto à une virgule ?
                    PE = round(last_price*1.001)
                    print('PE:',PE)
                else:
                    nb_decimals = len(str(last_price)) - index - 1 
                    PE = round(last_price*1.001,nb_decimals)
                    print('PE:',PE)
                    
            if last_price > PE2:
                PE = PE2
                print('PE:',PE)
            if last_price < PE1:
                PE = PE1
                print('PE:',PE)

            #choix levier
            lev_max = exchange.fetch_derivatives_market_leverage_tiers(symbol)[0]['maxLeverage'] #levier maximum
            if 0.1 < last_price < 100:
                if lev_max < 20:
                    levier = lev_max
                else:
                    levier = 20
            if last_price <= 0.1:
                if lev_max < 15:
                    levier = lev_max
                else:
                    levier = 15
            if 100 <= last_price < 500:
                if lev_max < 25:
                    levier = lev_max
                else:
                    levier = 25
            if last_price >= 500:
                if lev_max < 35:
                    levier = lev_max
                else:
                    levier = 35
            print('Levier',levier)

            ##Passage des ordres
            if all(var in globals() for var in ['BorS', 'PE', 'close', 'TPs', 'SL', 'levier']):
                info_leviers=exchange.fetch_positions(symbol) #récupère le gros tas d'info sur la paire
                size = info_leviers[0]['info']['size'] #taille de l'ordre long en court (recuperer nb décimals)
                #leviers
                if len(info_leviers) == 1:
                    levier_LS = info_leviers[0]['leverage']
                else:
                    levier_long = info_leviers[0]['leverage'] 
                    levier_short = info_leviers[1]['leverage'] 
                try: 
                    if levier_LS not in globals():
                        if levier != levier_LS:
                            exchange.set_leverage(symbol=symbol, leverage=levier)
                except: 
                    if BorS == 'Buy':
                        if levier != levier_long:
                            exchange.set_leverage(symbol=symbol, leverage=levier)
                    else:
                        if levier != levier_short:
                            exchange.set_leverage(symbol=symbol, leverage=levier)
                            
                #calcul quantity
                if "." in size:
                    decimals = size.split(".")[1]
                    nb_decimals = decimals.count("0")
                    quantity = round(levier/last_price,nb_decimals)
                    if quantity == 0:
                        quantity = 1/10**nb_decimals
                else:
                    quantity = round(levier/last_price)
                print('Quantity',quantity)

                ## Ordres
                #Entry
                orderPE = exchange.create_order(symbol=symbol, type='Limit', side=BorS, amount=quantity, price=PE) 
                #TP
                orderTP = exchange.create_order(symbol=symbol, type='Limit', side=close, amount=quantity, price=TPs[2])                    
                #SL
                if BorS == 'Buy':
                    orderSL = exchange.create_limit_order(symbol=symbol, side=close, amount=quantity, price=SL, params={'stopLossPrice': SL}) #Close long
                else:
                    orderSL = exchange.create_limit_buy_order(symbol=symbol, amount=quantity, price=SL, params = {'stopPrice': SL}) #Open long
                
                #ajouter les ordres au dico
                dico[symbol]=[]
                dico[symbol].append(orderPE['id']), dico[symbol].append(orderTP['id']), dico[symbol].append(orderSL['id'])
                
    ## Gestion des ordes 
    order_book = exchange.fetch_derivatives_open_orders() #liste des ordres à executer
    if len(order_book) != 0:
        symb = []
        for i in range(len(order_book)):
            symb.append(order_book[i]['info']['symbol']) #nom des paires de tous les ordres dans une liste

        # nombre d'ordres par paire

        dico_actif = {}
        for item in symb:
            if item in dico_actif:
                dico_actif[item] += 1
            else:
                dico_actif[item] = 1
        liste_actif = list(dico_actif.items()) #nombre d'ordres par paire en liste
        #print(liste_actif)

        #récupération des paires de trades en cours
        trade_actif = exchange.fetch_derivatives_positions()
        paire_active = None
        if len(trade_actif) != 0:
            paire_active = []
            for i in range(len(trade_actif)):
                paire_active.append(trade_actif[i]['info']['symbol'])
        
        # cloture des trades inutiles + suppression ID dans le dico
        for i in range(len(dico)):
            if liste_actif[i][1] == 2: # vérifier si le trade n'a pas été fermé ou liquidé quand 2 ordres sont ouverts
                #quel ordre est fermé ? 
                fpe = exchange.fetch_order_status(id = dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                ftp = exchange.fetch_order_status(id = dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                fsl = exchange.fetch_order_status(id = dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i]) 
                #print('222',fpe, ftp, fsl)
                if paire_active != None:
                    if list(dico.keys())[i] not in paire_active:
                        if fpe == 'canceled' or 'closed':
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                        elif ftp == 'canceled' or 'closed':
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                        elif fsl == 'canceled' or 'closed':
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                else:
                    if fpe == 'canceled' or 'closed':
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                    elif ftp == 'canceled' or 'closed':
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                        del dico[list(dico.keys())[i]]
                    elif fsl == 'canceled' or 'closed':
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                        del dico[list(dico.keys())[i]]
                    
            if liste_actif[i][1] == 1: # vérifier si le trade n'a pas été fermé ou liquidé quand 1 ordres sont ouverts
                #quel ordre est fermé ? 
                fpe = exchange.fetch_order_status(id = dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                ftp = exchange.fetch_order_status(id = dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                fsl = exchange.fetch_order_status(id = dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                #print('111',fpe, ftp, fsl) 
                if paire_active != None:
                    if list(dico.keys())[i] not in  paire_active:
                        if (fpe == 'closed' or fpe == 'canceled') and (ftp == 'closed' or ftp =='canceled'): 
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                        elif (fpe == 'closed' or fpe == 'canceled') and (fsl == 'closed' or fsl =='canceled'): 
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                        elif (fsl == 'closed' or fsl == 'canceled') and (ftp == 'closed' or ftp =='canceled'):
                            exchange.cancel_order(id= dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                            del dico[list(dico.keys())[i]]
                else:
                    if (fpe == 'closed' or fpe == 'canceled') and (ftp == 'closed' or ftp =='canceled'):
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][2], symbol=list(dico.keys())[i])
                        del dico[list(dico.keys())[i]]
                    elif (fsl == 'closed' or fsl == 'canceled') and (fpe == 'closed' or fpe =='canceled'):
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][1], symbol=list(dico.keys())[i])
                        del dico[list(dico.keys())[i]]
                    elif (fsl == 'closed' or fsl == 'canceled') and (ftp == 'closed' or ftp =='canceled'):
                        exchange.cancel_order(id= dico[list(dico.keys())[i]][0], symbol=list(dico.keys())[i])
                        del dico[list(dico.keys())[i]]
                    
                    
                    
