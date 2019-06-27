import xmlrpc
from pprint import pprint

proxy = xmlrpc.ServerProxy('http://192.168.35.11:8000')
user = ''
paswd = ''

print("Listing all VMs...")
print(proxy.xenapi.list_all_vms(user, paswd))

# print "Registering new VM..."
# proxy.xenapi.register_vm(user, paswd, '2_3_2', "3_2")  # <<studentid_courseid_vmid>>

# print "Stopping vm if exists..."
# proxy.xenapi.stop_vm(user, paswd, '2_3_2')

# print "Starting VM..."
# vm = proxy.xenapi.start_vm(user, paswd, '2_3_2')
# pprint(vm)

# print "Listing specific VM..."
# pprint(proxy.xenapi.list_vm(user, paswd, '2_3_2'))

# print "Stopping created VM..."
# proxy.xenapi.stop_vm(user, paswd, '2_3_2')

# print "Listing all VMs..."
# print proxy.xenapi.list_all_vms(user, paswd)

# print "Unregistering VM"
# proxy.xenapi.unregister_vm(user, paswd, '2_3_2')

# print "Listing all VMs..."
# print proxy.xenapi.list_all_vms(uzer, paswd)

# NOTE - variable was changed from 'uzer' to 'user'
print("Checking if vm exists")
print(proxy.xenapi.vm_exists(user, paswd, '2_3_2'))
print(proxy.xenapi.vm_exists(user, paswd, 'Domain-0'))

print("Checking if bridge exists")
print(proxy.xenapi.bridge_exists(user, paswd, 'Net-220'))
print(proxy.xenapi.bridge_exists(user, paswd, 'Net-221'))
print(proxy.xenapi.bridge_exists(user, paswd, 'Net-2211'))

print("Checking if bridge is up")
print(proxy.xenapi.is_bridge_up(user, paswd, 'Net-220'))
print(proxy.xenapi.is_bridge_up(user, paswd, 'Net-221'))
print(proxy.xenapi.is_bridge_up(user, paswd, 'Net-2211'))
