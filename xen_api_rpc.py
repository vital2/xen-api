from xmlrpc.server import SimpleXMLRPCServer
from security_util import expose, requires_user_privilege, requires_authentication_only, \
    requires_admin_privilege, is_exposed, is_authorized
from xen_api import XenAPI
import socketserver
import configparser

config = configparser.ConfigParser()

# TODO change this to a common config file on a shared location
config.read("/home/vital/config.ini")


# TODO Security to check if requesting user has privilege and callback security model
# TODO or default security model

class XenAPIExposer:
    """ This class exposes the actual xen_api with a remote RPC interface """

    def __init__(self):
        self.prefix = 'xenapi'

    def _dispatch(self, method, params):
        """ This method receives all the calls to the xen_api."""

        # check if method starts with correct prefix
        if not method.startswith(self.prefix + "."):
            raise Exception('method "%s" is not supported' % method)

        method_name = method.partition('.')[2]
        func = getattr(self, method_name)

        if not is_exposed(func):
            raise Exception('method "%s" is not supported' % method)

        is_authorized(func, params[0], params[1])

        return func(*params)

    # TODO - add functionality to check if a user has access to the VM specified
    # TODO - TBD on all functions
    @expose
    @requires_authentication_only
    def start_vm(self, user, passwd, vm_name, vm_options):
        return XenAPI().start_vm(vm_name, vm_options)

    @expose
    @requires_authentication_only
    def stop_vm(self, user, passwd, vm_name):
        XenAPI().stop_vm(vm_name)

    @expose
    @requires_authentication_only
    def save_vm(self, user, passwd, vm_name):
        XenAPI().save_vm(vm_name)

    @expose
    @requires_authentication_only
    def restore_vm(self, user, passwd, vm_name, base_vm):
        XenAPI().restore_vm(vm_name, base_vm)

    @expose
    @requires_authentication_only
    def list_all_vms(self, user, passwd):
        return XenAPI().list_all_vms()

    @expose
    @requires_authentication_only
    def get_dom_details(self, user, passwd):
        return XenAPI().get_dom_details()

    @expose
    @requires_authentication_only
    def list_vm(self, user, passwd, vm_name):
        return XenAPI().list_vm(vm_name)

    @expose
    @requires_authentication_only
    def setup_vm(self, user, passwd, vm_name, base_vm, vif=None):
        XenAPI().setup_vm(vm_name, base_vm, vif)

    @expose
    @requires_authentication_only
    def cleanup_vm(self, user, passwd, vm_name):
        XenAPI().cleanup_vm(vm_name)

    @expose
    @requires_authentication_only
    def kill_zombie_vm(self, user, passwd, vm_id):
        XenAPI().kill_zombie_vm(vm_id)

    @expose
    @requires_authentication_only
    def create_bridge(self, user, passwd, name):
        XenAPI().create_bridge(name)

    @expose
    @requires_authentication_only
    def remove_bridge(self, user, passwd, name):
        XenAPI().remove_bridge(name)

    @expose
    @requires_authentication_only
    def vm_exists(self, user, passwd, name):
        return XenAPI().vm_exists(name)

    @expose
    @requires_authentication_only
    def bridge_exists(self, user, passwd, name):
        return XenAPI().bridge_exists(name)

    @expose
    @requires_authentication_only
    def is_bridge_up(self, user, passwd, name):
        return XenAPI().is_bridge_up(name)


# allows RPC module to handle concurrent requests
class SimpleThreadedXMLRPCServer(socketserver.ThreadingMixIn, SimpleXMLRPCServer):
    pass

server = SimpleThreadedXMLRPCServer((config.get("XenAPI", "IP_ADDRESS"), int(config.get("XenAPI", "PORT"))), logRequests=True, allow_none=True)
server.register_instance(XenAPIExposer())
try:
    print('Use Control-C to exit')
    server.serve_forever()
except KeyboardInterrupt:
    print('Exiting')
