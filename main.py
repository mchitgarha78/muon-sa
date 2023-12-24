from api import app
import trio
from multiprocessing import Process
from muon_sa import MuonSA
from config import PRIVATE, SA_INFO
from abstract.node_info import NodeInfo
import logging
import os
import sys


if __name__ == '__main__':

    file_path = 'logs'
    file_name = 'sa.log'
    log_formatter = logging.Formatter('%(asctime)s - %(message)s', )
    root_logger = logging.getLogger()
    if not os.path.exists(file_path):
        os.mkdir(file_path)
    with open(f'{file_path}/{file_name}', 'w'):
        pass
    file_handler = logging.FileHandler(f'{file_path}/{file_name}')
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)
    total_node_number = int(sys.argv[1])
    registry_url = ''
    node_info = NodeInfo()
    muon_sa = MuonSA(total_node_number, registry_url,
                     SA_INFO, PRIVATE, node_info)

    # TODO: Use WSGI or uvicorn
    app.config['SA'] = muon_sa
    flask_process = Process(target=lambda: app.run(
        debug=True, use_reloader=False))
    sa_process = Process(target=lambda: trio.run(muon_sa.run_process))

    flask_process.start()
    sa_process.start()

    flask_process.join()
    sa_process.join()
