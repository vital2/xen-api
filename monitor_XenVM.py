import sys
import logging
import requests

from logging.handlers import RotatingFileHandler
from pyxs import Client, PyXSError

logger = logging.getLogger('xen-store')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('/home/vlab/log/xen-api.log', maxBytes=1024*1024*10, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

with Client() as c:
    # the sys.arg is the domid which is to be passed to the function call
    dom_id = int(sys.argv[1])
    dom_name = c['/local/domain/{}/name'.format(dom_id)]
    user_id = dom_name.split('_')[0]
    vm_id = dom_name.split('_')[2]
    path = c.get_domain_path(dom_id)
    path = path + '/control/shutdown'

    with c.monitor() as m:
	# watch for any random string
        m.watch(path, b"baz")
        logger.debug('Watching path {}'.format(path))
        next(m.wait())
        # print(next(m.wait()))
        if next(m.wait()) is not None:
            logger.debug('Event on path {}'.format(path))
            params = {
	    'user_id': user_id,
	    'vm_id': vm_id
	    }
	    requests.get("https://vital-dev2.poly.edu/vital/users/release-vm/", params=params)
        # Do the necassary action like calling the script
        # the script may call the vital api to do th enecessary actions
        # maybe we can also send the required domid along with the request 
