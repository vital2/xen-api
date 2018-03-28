import sys
import logging
import requests
import ConfigParser

from logging.handlers import RotatingFileHandler
from pyxs import Client, PyXSError

logger = logging.getLogger('xen-store')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('/home/vlab/log/xen-api.log', maxBytes=1024*1024*10, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

config_ini = ConfigParser.ConfigParser()
config_ini.optionxform=str

# TODO change to common config file in shared location
config_ini.read("/home/vlab/config.ini")

with Client() as c:
    # the sys.arg is the domid which is to be passed to the function call
    dom_id = int(sys.argv[1])
    dom_name = c['/local/domain/{}/name'.format(dom_id)]
    user_id = dom_name.split('_')[0]
    vm_id = dom_name.split('_')[2]
    logger.debug('VM {}, {}'.format(user_id, vm_id))
    path = c.get_domain_path(dom_id)
    path = path + '/control/shutdown'
    api_key = config_ini.get('Security', 'INTERNAL_API_KEY')
    logger.debug('{}: {}'.format(config_ini.get("VITAL", "SERVER_NAME"), api_key))

    with c.monitor() as m:
	# watch for any random string
        m.watch(path, b'baz')
        logger.debug('Watching path {}'.format(path))
        next(m.wait())
        # print(next(m.wait()))
        if next(m.wait()) is not None:
            logger.debug('Event on path {}'.format(path))
            params = {'api_key': api_key, 'user_id': user_id, 'vm_id': vm_id}
	    requests.get('https://' + config_ini.get("VITAL", "SERVER_NAME") + '/vital/users/release-vm/', params=params)
