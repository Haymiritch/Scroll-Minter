import web3
from web3 import Web3  
from web3.middleware import geth_poa_middleware

import random
import requests
import json
import ua_generator
import datetime

from time import sleep
from os import system
from inquirer import prompt, List
from colorama import Fore, Style

from config import (RETRY, MAX_GWEI, WAIT_CHEAPER_GAS, REFERAL, SCROLL_RPC, CONTRACT_ADDRESS, WAITING, LOGO, CONTRACT_ABI)
from database import Database


def getDateTime() -> str:
    now = datetime.datetime.now()
    return now.strftime("%H:%M:%S")

def getWeb3Provider(rpc_link: str) -> dict:
    web3 = Web3(Web3.HTTPProvider(endpoint_uri=rpc_link))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return web3

    
def getBaseAddress(web3: dict, private_key: str) -> str:
    account = web3.eth.account.from_key(private_key=private_key)
    address = account.address
    return address
    

def checkCanvasMint(web3: dict, address: str) -> bool:
    contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
    getprofile = contract.functions.getProfile(address).call()
    is_canvas_minted = contract.functions.isProfileMinted(getprofile).call()
    return is_canvas_minted


def getSignature(referal: str, address: str, proxy: str) -> str:
    ua = ua_generator.generate(device='desktop', browser=('chrome', 'edge'))
    headers = {
        "Host": "canvas.scroll.cat",
        "Accept": "*/*",
        "Accept-Language": "en-EN",
        "Sec-Ch-Ua": ua.ch.brands,
        "Sec-Ch-Ua-Mobile": ua.ch.mobile,
        "Sec-Ch-Ua-Platform": ua.ch.platform,
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Origin": "https://scroll.io",
        "Referer": "https://scroll.io/",
        "Priority": "u=1, i",
        "User-Agent": ua.text
    }
    
    try:
        r = requests.get(f"https://canvas.scroll.cat/code/{referal}/sig/{address}", headers=headers, proxies=dict(http=f"http://{proxy}"))
        data = r.json()
        signature = data.get("signature")
        return signature
        
    except Exception as err:
        print(f"{Fore.RED}{getDateTime()} | [-] Ошибка при получении сигнатуры | {err} | {address}{Fore.WHITE}")    


def getGas(web3: dict, tx_params: dict) -> int:    
    gas = int(web3.eth.estimate_gas(tx_params) * 1.1)*10
    #print(gas)
    return gas


def getGasPrice(web3: dict) -> bool:
    gwei = Web3.from_wei(web3.eth.gas_price, 'gwei')
    
    if gwei > MAX_GWEI:
        if WAIT_CHEAPER_GAS:
            while gwei > MAX_GWEI:
                sleep(20)
                gwei = Web3.from_wei(web3.eth.gas_price, 'gwei')
                
            return True
        else:
            return False
    else:
        return True


def mintCanvas(web3: dict, address: str, nickname: str, referal: str, proxy: str, private_key: str) -> dict:
    try:
        if not getGasPrice(web3):
            print(f"{Fore.RED}{getDateTime()} | [-] Цена газа оказалась слишком большой | {address}{Fore.WHITE}")
            return False
        contract_txn = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
        tx_params = {
            'chainId': web3.eth.chain_id,
            'nonce': web3.eth.get_transaction_count(address),
            'from': address,
            'value': web3.to_wei(0.0005, 'ether'),
        }
        tx_params['gas'] = getGas(web3, tx_params)
        
        tx_completed = contract_txn.functions.mint(nickname, getSignature(referal, address, proxy)).build_transaction(tx_params)
        signed_tx = web3.eth.account.sign_transaction(tx_completed, private_key)
        raw_tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = web3.to_hex(raw_tx_hash)
            
        try:
            data = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=200)
            #print(data)
            if 'status' in data and data['status'] == 1:
                print(f"{Fore.GREEN}{getDateTime()} | [+] Успешно заминтили | {tx_hash} | {address}{Fore.WHITE}")
                return True
            else:
                print(f"{Fore.RED}{getDateTime()} | [-] Ошибка на транзакции минта | {data['transactionHash']} | {address}{Fore.WHITE}")
                return False
        except Exception as err:
            print(f"{Fore.RED}{getDateTime()} | [-] Непонятная ошибка по время транзакции | {err} | {address}{Fore.WHITE}")
            return False

    except Exception as err:
        if retrys <= RETRY:
            retrys = retrys + 1
            return mintCanvas(web3, address, nickname, referal, proxy, private_key)
        else:
            retrys = 0
            
        print(f"{Fore.RED}{getDateTime()} | [-] Ошибка при минте | {err} | {address} | Повторов: {retrys}{Fore.WHITE}")


def chooseMode() -> str:
    questions = [
        List('prefered_path', message="Выбери действие",
             choices=[
                '1 | Начать минтить на кошельках сначало',
                '2 | Продолжить с последнего использованного кошелька',
             ])]
    mode = prompt(questions)['prefered_path']
    return mode


def main(mode: str) -> None:
    with open("data/privatekeys.txt", "r", encoding="utf-8") as file:  
        lines_prv_keys = file.readlines()
        line_count = len(lines_prv_keys)

    with open("data/nicknames.txt", "r", encoding="utf-8") as file:  
        lines_nicknames = file.readlines()  
    
    with open("data/proxy.txt", "r", encoding="utf-8") as file:  
        lines_proxy = file.readlines()  
    
    if mode == "1 | Начать минтить на кошельках сначало":
        db.truncate_table()
        start_line = 0
    else:
        last_line_id = db.getLast_line_id()
        start_line = last_line_id
    
    system("cls")
    print(Fore.GREEN+LOGO+Style.RESET_ALL)
    print(f"{Fore.WHITE}{getDateTime()} | [●] Начинаю работать с кошельками" if mode == "1 | Начать минтить на кошельках сначало" else f"{Fore.WHITE}{getDateTime()} | [●]  Продолжаю работу с кошельками")
    
    for line in range(start_line, line_count):
        private_key = lines_prv_keys[line].strip() # -- приват кей
        
        proxy = lines_proxy[line].strip().split(":")
        proxy = f"{proxy[2]}:{proxy[3]}@{proxy[0]}:{proxy[1]}" # -- прокся
        
        referal = random.choice(REFERAL) # -- реферал код
        nickname = lines_nicknames[line].strip() # -- никнейм
            
        try:    
            sleeptime = random.randint(WAITING[0], WAITING[1])
            print(f"\n{Fore.WHITE}{getDateTime()} | [●] Отдыхаем перед началом работы с кошельком | {sleeptime} сек.")
            sleep(sleeptime)
            
            w3 = getWeb3Provider(SCROLL_RPC)
            db.add_to_db(private_key, line)
            
            address = getBaseAddress(w3, private_key)
            print(f"{Fore.WHITE}{getDateTime()} | [●] Начинаю минтить | {address}")
            
            is_canvas_minted = checkCanvasMint(w3, address)
            if is_canvas_minted:
                print(f"{Fore.GREEN}{getDateTime()} | [+] Canvas уже заминчен | {address}")
                continue # -- для скипа
            
            mint = mintCanvas(w3, address, nickname, referal, proxy, private_key)
            if mint:
                print(f"{Fore.GREEN}{getDateTime()} | [+] Успешно закончили работу с кошельком | {address}")
            else:
                print(f"{Fore.RED}{getDateTime()} | [-] Неудачно закончили работу с кошельком | {address}")
                
        except Exception as err:
            print(f"{Fore.RED}{getDateTime()} | [-] Ошибка при начале работы с кошельком | {address}")
    
    input(f"\n{Fore.GREEN}{getDateTime()} | [+] Закончил работу с кошельками | Нажмите ентер для продолжения{Fore.WHITE}")




if __name__ == "__main__":
    system('cls')
    retrys = 0 # -- kostyl
    db = Database()
    print(Fore.GREEN+LOGO+Style.RESET_ALL)
    print("Добро пожаловать!\n")
    mode = chooseMode()
    main(mode)