import json
import os
from typing import List, Dict
from web3 import Web3
from web3.exceptions import Web3Exception
from eth_account import Account
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client as SolanaClient

class WalletManager:
    # 定义不同链的钱包文件
    WALLET_FILES = {
        'eth': 'eth_wallets.json',
        'sol': 'sol_wallets.json'
    }
    NETWORKS = {
        'eth': 'ETH_RPC_API',
        'sol': 'SOL_RPC_API'
    }

    def __init__(self, network: str = 'eth'):
        if network not in self.NETWORKS:
            raise ValueError(f"不支持的网络: {network}")
        
        self.network = network
        self.wallet_file = self.WALLET_FILES[network]
        if network == 'sol':
            self.sol_client = SolanaClient(self.NETWORKS[network])
            if not self.sol_client.is_connected():
                raise ConnectionError("无法连接到Solana网络")
        else:
            self.w3 = Web3(Web3.HTTPProvider(self.NETWORKS[network]))
            if not self.w3.is_connected():
                raise ConnectionError("无法连接到以太坊网络")

    def _load_wallets(self) -> List[Dict]:
        """加载指定链的钱包"""
        try:
            if os.path.exists(self.wallet_file):
                with open(self.wallet_file, 'r') as file:
                    return json.load(file)
            return []
        except json.JSONDecodeError:
            print(f"警告: {self.wallet_file} 文件损坏，从空列表开始")
            return []

    def _save_wallets(self, wallets: List[Dict]) -> None:
        """保存指定链的钱包"""
        try:
            with open(self.wallet_file, 'w') as file:
                json.dump(wallets, file, indent=4)
        except IOError as e:
            raise IOError(f"保存 {self.wallet_file} 失败: {e}")

    def create_wallets(self, num_wallets: int, chain: str = 'eth') -> List[Dict]:
        """创建并保存指定数量的新钱包"""
        if num_wallets < 0:
            raise ValueError("钱包数量必须是非负数")
        if chain not in ['eth', 'sol']:
            raise ValueError("仅支持 'eth' 或 'sol' 链")
        if chain != self.network:
            raise ValueError(f"网络 ({self.network}) 与请求链 ({chain}) 不匹配")
            
        wallets = self._load_wallets()
        new_wallets = []
        
        for _ in range(num_wallets):
            if chain == 'eth':
                account = Account.create()
                wallet = {
                    'chain': 'eth',
                    'address': account.address,
                    'private_key': account.key.hex(),
                    'created_at': self.w3.eth.get_block('latest')['timestamp']
                }
            else:  # sol
                keypair = Keypair()
                block_height_resp = self.sol_client.get_block_height()
                block_height = block_height_resp.value if hasattr(block_height_resp, 'value') else int(block_height_resp)
                wallet = {
                    'chain': 'sol',
                    'address': str(keypair.pubkey()),
                    'private_key': keypair.to_bytes().hex(),
                    'created_at': block_height
                }
            new_wallets.append(wallet)
        
        wallets.extend(new_wallets)
        self._save_wallets(wallets)
        return new_wallets

    def get_balance(self, address: str, chain: str = 'eth') -> float:
        """检查钱包余额"""
        try:
            if chain == 'eth':
                balance_wei = self.w3.eth.get_balance(address)
                return float(self.w3.from_wei(balance_wei, 'ether'))
            elif chain == 'sol':
                pubkey = Pubkey.from_string(address)
                response = self.sol_client.get_balance(pubkey)
                return float(response.value) / 1e9  # lamports to SOL
            else:
                raise ValueError("不支持的链类型")
        except (Web3Exception, ValueError) as e:
            print(f"警告: 获取 {address} 的余额失败: {e}")
            return 0.0

    def manage_wallets(self, requested_num: int, chain: str = 'eth') -> List[Dict]:
        """管理指定链的钱包数量"""
        if requested_num < 0:
            raise ValueError("请求数量必须是非负数")
        if chain != self.network:
            raise ValueError(f"网络 ({self.network}) 与请求链 ({chain}) 不匹配")
            
        wallets = self._load_wallets()
        current_num = len(wallets)
        
        if requested_num <= current_num:
            return wallets[:requested_num]
        
        new_wallets = self.create_wallets(requested_num - current_num, chain)
        return wallets + new_wallets

def main():
    try:
        chain = input("请选择链类型 (eth/sol): ").lower()
        if chain not in ['eth', 'sol']:
            raise ValueError("仅支持 'eth' 或 'sol'")
        
        wallet_mgr = WalletManager(chain)
        requested_num = int(input(f"请输入需要的 {chain.upper()} 钱包数量: "))
        wallets = wallet_mgr.manage_wallets(requested_num, chain)
        
        print(f"\n使用或创建了 {len(wallets)} 个 {chain.upper()} 钱包:")
        for idx, wallet in enumerate(wallets, 1):
            balance = wallet_mgr.get_balance(wallet['address'], chain)
            unit = 'ETH' if chain == 'eth' else 'SOL'
            print(f"钱包 {idx}:")
            print(f"  地址: {wallet['address']}")
            print(f"  余额: {balance:.6f} {unit}")
            
    except ValueError as e:
        print(f"输入错误: {e}")
    except ConnectionError as e:
        print(f"网络连接错误: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == "__main__":
    main()