# Muon SA

This implementation represents Muon-SA (Signature Aggregator) version of [pyfrost](https://github.com/SAYaghoubnejad/pyfrost) library to issue signatures.

## How to Setup

To create a virtual environment (`venv`) and install the required packages, run the following commands:

```bash
$ git clone https://github.com/mchitgarha78/muon-sa.git 
$ cd muon-sa
$ virtualenv -p python3.10 venv
$ source venv/bin/activate
(venv) $ pip install -r requirements.txt
(venv) $ pip install quart-trio
```

**Note:** The required Python version is `3.10`.

After these installations, configure `.env` file. The file `.env.example` has the example of thie environment variables. So you can type the following command:
```bash
(venv) $ cp .env.example .env
```

Change your settings in the `.env` file:
```
PRIVATE_KEY=<your-sa-private>
PORT=5039
HOST=0.0.0.0
API_HOST=0.0.0.0
API_PORT=5040
APPS_LIST_URL=<your-apps-url>
```

You also need to configure your `nodes.json` file in `abstract` directory:

```bash
(venv) $ cp ./abstract/nodes.json.example ./abstract/nodes.json
```

Get your nodes data and add it to `nodes.json` file. 



## How to Run

Type the following command to run Muon node:



```bash
(venv) $ python main.py
```

If you want to get signature from the `simple_oracle`, you can test it using the following CURL command:
```bash
(venv) $ curl -X POST -H "Content-Type: application/json" -d '{"app": "simple_oracle", "method": "price", "reqId": "12345", "data": {"params": {"unit": "USD", "token": "BNB"}, "result": {"price":267},"signParams":[{"name":"appId","type":"uint256","value":"55248038324285368712633359989377918216711324138169494581107010692219814301235"},{"name":"reqId","type":"uint256","value":"12345"},{"type":"uint32","value":227},{"type":"string","value":"BNB"},{"type":"string","value":"USD"}],"hash":"0x7e92cff17408096d2fa9c73b7a818a1c51f0eeeab5a91c19d60cf8395a5a6c53"}}' http://127.0.0.1:5040/v1/
```


