import os
import requests
import sys
import subprocess


HELP_MESSAGE = """
ENVIRONMENT VARIABLES TO SET:
  
  Required variables:
    
    \33[32mPUBLIC_SLAVE_HOSTS\33[0m
      comma-separated list of public agents' private IPs
    
    \33[32mSLAVE_HOSTS\33[0m
      comma-separated list of private agents' private IPs
    
    \33[32mMASTER_HOSTS\33[0m
      comma-separated list of masters' private IPs
    
    \33[32mSSH_KEY_PATH\33[0m
      full path to the private key for your cluster
    
    \33[32mSSH_USER\33[0m
      ssh user for your Cluster
  
    \33[32mMASTER_PUBLIC_IPS\33[0m
      comma-separated list of masters' public IPs
  
  
  EE-only variables
    
    \33[32mDCOS_LOGIN_UNAME\33[0m
      dcos username for logging into your cluster
      
    \33[32mDCOS_LOGIN_PW\33[0m
      dcos password for logging into your cluster
  
  
  Open-only variables
    
    \33[32mDCOS_ACS_TOKEN\33[0m
      Obtain this token by logging into your cluster from your web browser.
      If you run integration tests before setting this variable, you will 
      no longer be able to log into your cluster.
"""


def print_red(text):
    CRED = '\033[91m'
    CEND = '\033[0m'
    print(CRED + text + CEND)


def set_required_env_var(dcos_env_vars, env_var_name):
    env_var = os.getenv(env_var_name)
    if env_var is None:
        print_red("ERROR: required environment variable '{}' is not set!".format(env_var_name))
        print(HELP_MESSAGE)
        sys.exit(1)
    dcos_env_vars[env_var_name] = env_var


def load_env_vars():
    dcos_env_vars = {}
    required_env_vars = ['PUBLIC_SLAVE_HOSTS', 'SLAVE_HOSTS', 'MASTER_HOSTS', 'SSH_KEY_PATH', 'SSH_USER',
                         'MASTER_PUBLIC_IPS']
    non_required_env_vars = ['DCOS_LOGIN_UNAME', 'DCOS_LOGIN_PW', 'DCOS_ACS_TOKEN']

    for e in required_env_vars:
        set_required_env_var(dcos_env_vars, e)

    for e in non_required_env_vars:
        v = os.getenv(e)
        if v:
            dcos_env_vars[e] = v

    return dcos_env_vars


def get_leader_ip(masters):
    masters = masters.split(',')
    master = masters[0]
    r = requests.get('http://{}/exhibitor/exhibitor/v1/cluster/status'.format(master))
    assert r.status_code == 200
    assert len(r.json()) == len(masters)

    for master_info in r.json():
        if master_info['isLeader']:
            return master_info['hostname']

    raise Exception('leader not found')


def main():
    test_dir = 'packages/dcos-integration-test/extra'
    cwd = os.getcwd()
    if len(cwd) < len(test_dir) or cwd[len(cwd) - len(test_dir):] != test_dir:
        print_red("ERROR: you must run dcos-pytest in the dcos/packages/dcos-integration-test/extra or dcos-enterprise/packages/dcos-integration-test/extra directories!")
        sys.exit(1)

    if '--help' in sys.argv or '-h' in sys.argv:
        print(HELP_MESSAGE)

    env_vars = load_env_vars()
    leader_ip = get_leader_ip(env_vars['MASTER_PUBLIC_IPS'])

    subprocess.run('scp -i {} test_* get_test_group.py conftest.py {}@{}:/tmp'.format(
        env_vars['SSH_KEY_PATH'], env_vars['SSH_USER'], leader_ip), shell=True)

    export_cmds = ''
    for k, v in env_vars.items():
        export_cmds += 'export {}={} && '.format(k, v)

    pytest_cmd = 'dcos-shell pytest ' + ' '.join(sys.argv[1:])
    subprocess.run("ssh -t -i {} {}@{} '{}cd /tmp && {}'".format(
        env_vars['SSH_KEY_PATH'], env_vars['SSH_USER'], leader_ip, export_cmds, pytest_cmd), shell=True)
