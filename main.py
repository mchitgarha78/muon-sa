from muon_frost_py.common.configuration_settings import ConfigurationSettings
from api import app
import trio
from multiprocessing import Process
from sa_process import SAProcess

import sys

# Define the logging configurations
    

    

if __name__ == '__main__':
    
    ConfigurationSettings.set_logging_options('logs', 'SA.log')
    
    # Increase the string max limit for integer string conversion
    sys.set_int_max_str_digits(0)

    
    sa_peer_id = '16Uiu2HAmGVUb3nZ3yaKNpt5kH7KZccKrPaHmG1qTB48QvLdr7igH'
    total_node_number = int(sys.argv[1])
    registry_url = ''
    sa_process = SAProcess(sa_peer_id, total_node_number, registry_url)


    # TODO: Use WSGI or uvicorn
    app.config['SA'] = sa_process
    
    flask_process = Process(target = lambda: app.run(debug = True, use_reloader = False))
    sa_trio_process = Process(target = lambda: trio.run(sa_process.run))

    flask_process.start()
    sa_trio_process.start()

    flask_process.join()
    sa_trio_process.join()
    