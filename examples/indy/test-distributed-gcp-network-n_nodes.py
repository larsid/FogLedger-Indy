from typing import List
from fogbed import (
    Container, VirtualInstance,
    setLogLevel, FogbedDistributedExperiment, Worker
)
import time
import os

from fogledgerIndy.Node import Node
from fogledgerIndy.IndyBasic import IndyBasic
setLogLevel('info')


def add_datacenters_to_worker(worker: Worker, datacenters: List[VirtualInstance]):
    for device in datacenters:
        worker.add(device, reachable=True)


if (__name__ == '__main__'):

    exp = FogbedDistributedExperiment()

    # Webserver to check metrics
    cloud = exp.add_virtual_instance('cloud')
    instanceWebserver = exp.add_docker(
        container=Container(
            name='webserver',
            dimage='larsid/fogbed-indy-webserver:v1.0.2-beta',
            port_bindings={8000: 8080, 6543: 6543},
            environment={
                'MAX_FETCH': 50000,
                'RESYNC_TIME': 120,
                'WEB_ANALYTICS': True,
                'REGISTER_NEW_DIDS': True,
                'LEDGER_INSTANCE_NAME': "fogbed",
                'INFO_SITE_TEXT': "Node Container @ GitHub",
                'INFO_SITE_URL': "https://github.com/hyperledger/indy-node-container",
                'LEDGER_SEED': "000000000000000000000000Trustee1",
                'GENESIS_FILE': "/pool_transactions_genesis"
            },
            volumes=[
                f'tmp:/var/log/indy',
            ],
            ip='34.95.142.126'
        ),
        datacenter=cloud)

    
    # Define Indy network in cloud
    indyCloud = IndyBasic(
        exp=exp, trustees_path='examples/tmp/trustees.csv', config_nodes=[
            Node(name = 'node1', port_bindings =  {9701: 9701, 9702: 9702}, ip = '35.199.124.171'),
            Node(name = 'node2', port_bindings = {9701: 9701, 9702: 9702}, ip =  '34.76.173.182'),
            Node(name = 'node3', port_bindings = {9701: 9701, 9702: 9702}, ip =  '34.87.194.83'),
            Node(name = 'node4', port_bindings = {9701: 9701, 9702: 9702}, ip =  '35.189.132.181'),
        ])
    workers = []

    # Add worker for cli
    workerServer = exp.add_worker(f'146.148.47.210')
    workers.append(exp.add_worker(f'35.199.124.171'))
    workers.append(exp.add_worker(f'34.76.173.182'))
    workers.append(exp.add_worker(f'34.87.194.83'))
    workers.append(exp.add_worker(f'35.189.132.181'))

    workerServer.add(cloud, reachable=True)
    for i in range(0, len(workers)):
        workers[i].add(indyCloud.ledgers[i], reachable=True)
    for i in range(0, len(workers)):
        exp.add_tunnel(workerServer, workers[i])

    try:
        exp.start()
        indyCloud.start_network()
        cloud.containers['webserver'].cmd(
            f"echo '{indyCloud.genesis_content}' > /pool_transactions_genesis")
        print('Starting Webserver')
        time.sleep(10)
        cloud.containers['webserver'].cmd(
            './scripts/start_webserver.sh > output.log 2>&1 &')
        input('Press any key...')
    except Exception as ex:
        print(ex)
    finally:
        exp.stop()
