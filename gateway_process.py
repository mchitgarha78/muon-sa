from muon_frost_py.signature_aggregator.signature_aggregator import SignatureAggregator
from sa_config import PRIVATE
from muon_frost_py.common.configuration_settings import ConfigurationSettings
from dns import DNS
from typing import List

import sys

import trio
import logging

async def run_dkg(gateway : SignatureAggregator, all_nodes: List[str], threshold: int, n: int, app_name: str, seed: int=42) -> None:

    # Begin DKG protocol
    is_completed = False
    dkg_key = None
    while not is_completed:
        dkg_key = await gateway.request_dkg(threshold, n, all_nodes, app_name, seed)
        if dkg_key['dkg_id'] == None:
            exit()
        
        result = dkg_key['result']
        logging.info(f'The DKG result is {result}')
        if result == 'SUCCESSFUL':
            is_completed = True
        #break

    return dkg_key

async def run(gateway_id: str, total_node_number: int, threshold: int, n: int, num_signs: int) -> None:
    """
    Sets up and runs a gateway node in a distributed network using libp2p.

    :param gateway_id: Identifier of the gateway node.
    :param threshold: Threshold number of parties for the DKG protocol.
    :param n: Total number of nodes in party in the DKG protocol.
    """
    dns = DNS()

    # List of peer IDs in the network
    all_nodes = dns.get_all_nodes(total_node_number)

    # Initialize the Gateway with DNS lookup for the current node
    # TODO: Findout how to handle the tradeoff between number of semaphores and timeout..
    gateway = SignatureAggregator(dns.lookup_gateway(gateway_id), PRIVATE, 
                               dns, max_workers = 0, default_timeout = 50)
    app_name = 'sample_oracle'

    async with trio.open_nursery() as nursery:
        # Start gateway and maintain nonce values for each peer
        nursery.start_soon(gateway.run)

        await gateway.maintain_nonces(all_nodes)
        


        dkg_key = await run_dkg(gateway, all_nodes, threshold, n, app_name)

        
        dkg_id = dkg_key['dkg_id']

        
        # Request signature using the generated DKG key
        for i in range(num_signs):
            logging.info(f'Get signature {i} for app {app_name} with DKG id {dkg_id}')
            signature = await gateway.request_signature(dkg_key, threshold)
            logging.info(f'Signature data: {signature}')

        # Stop the gateway
        gateway.stop()
        nursery.cancel_scope.cancel()


if __name__ == "__main__":

    # Define the logging configurations
    ConfigurationSettings.set_logging_options('logs', 'gateway.log')
    
    # Increase the string max limit for integer string conversion
    sys.set_int_max_str_digits(0)

    # Define the gateway identifier and DKG parameters
    gateway_peer_id = '16Uiu2HAmGVUb3nZ3yaKNpt5kH7KZccKrPaHmG1qTB48QvLdr7igH'
    total_node_number = int(sys.argv[1])
    dkg_threshold = int(sys.argv[2])
    num_parties = int(sys.argv[3])
    num_signs = int(sys.argv[4])

    try:
        # Run the gateway with specified parameters
        trio.run(run, gateway_peer_id, total_node_number, dkg_threshold, num_parties, num_signs)
    except KeyboardInterrupt:
        # Handle graceful shutdown on keyboard interrupt
        pass
