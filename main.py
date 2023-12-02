from api import app
import trio
from multiprocessing import Process

async def gateway_process():
    # run gateway loops and processes
    pass


    

if __name__ == '__main__':
    # TODO: Use WSGI or uvicorn
    flask_process = Process(target = lambda: app.run(debug = True, use_reloader = False))
    trio_process = Process(target = lambda: trio.run(gateway_process))

    flask_process.start()
    trio_process.start()

    flask_process.join()
    trio_process.join()
    