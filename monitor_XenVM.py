import sys
from pyxs import Client, PyXSError

with Client() as c:
    # the sys.arg is the domid which is to be passed to the function call
    path = c.get_domain_path(int(sys.argv[1]))
    # print(path)
    path = path + '/control/shutdown'

    with c.monitor() as m:
	# watch for any random string
        m.watch(path, b"baz")
        # print('Watching ... {}.'.format(path))
        next(m.wait())
        # print(next(m.wait()))
        if next(m.wait()) is not None:
            pass
        # Do the necassary action like calling the script
        # the script may call the vital api to do th enecessary actions
        # maybe we can also send the required domid along with the request 