from subprocess import Popen, PIPE
from shutil import copyfile
from glob import glob
import os, errno
import socket
import sys
import ConfigParser
import logging
import requests

from logging.handlers import RotatingFileHandler
from pyxs import Client, PyXSError
from threading import Thread

config = ConfigParser.ConfigParser()

# TODO change this to a common config file on a shared location
config.read("/home/vlab/config.ini")

# TODO change the logging level and file name to be read from config file
logger = logging.getLogger('xen api')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('/home/vlab/log/xen-api.log', maxBytes=1024*1024*10, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class XenAPI:
    """
    Provides api to xen operations
    """

    def __init__(self):
        pass

    def start_vm(self, vm_name, vm_options):
        """
        starts specified virtual machine
        :param vm_name name of virtual machine
        """
        if not self.vm_exists(vm_name):
            logger.debug('Starting VM - {}'.format(vm_name))
            vm = VirtualMachine(vm_name).start(vm_options)
        else:
            logger.debug('VM already Exists - {}'.format(vm_name))
            vm = self.list_vm(vm_name, None)

            # Start the Monitor Xen VM Script to watch the Xenstored Path
            # And let it run in the background we are not worried about collecting the results
            # cmd = '{} {}/monitor_XenVM.py {}'.format(
            #     sys.executable, os.path.dirname(os.path.realpath(__file__)), vm.id)
            # logger.debug('Watching VM with Xenstore {}'.format(cmd))
            # Popen(cmd.split(), close_fds=True)
            # Using Threading Module to send the function to background

        background_thread = Thread(target=self.listenToVMShutdown, args=(vm.id,))
        background_thread.start()

        return vm

    def stop_vm(self, vm_name):
        """
        stops the specified vm
        :param vm_name: name of the vm to be stopped
        """
        logger.debug('Stopping VM - {}'.format(vm_name))
        VirtualMachine(vm_name).shutdown()

    def list_all_vms(self):
        """
        lists all vms in the server (output of xl list)
        :return List of VirtualMachine with id, name, memory, vcpus, state, uptime
        """
        logger.debug('Listing all VMs..')
        cmd = 'xl list'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            raise Exception('ERROR : cannot list all the vms. \n Reason : %s' % err.rstrip())

        vms = []
        output = out.strip().split("\n")
        for i in range(1, len(output)):
            # removing first line
            line = output[i]
            line = " ".join(line.split())
            val = line.split(" ")

            # creating VirtualMachine instances to return
            vm = VirtualMachine(val[0])
            vm.id = val[1]
            vm.memory = val[2]
            vm.vcpus = val[3]
            vm.state = val[4]
            vm.uptime = val[5]
            vms.append(vm)
        return vms

    def list_vm(self, vm_name, display_port):
        """
        lists specified virtual machine (output of xl list vm_name)
        :param vm_name name of virtual machine
        :param (OPTIONAL) Display Driver used (VNC/Spice)
        :return VirtualMachine with id, name, memory, vcpus, state, uptime
        """
        logger.debug('Listing VM {}'.format(vm_name))
        cmd = 'xl list '+vm_name
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            raise Exception('ERROR : cannot list the vm. \n Reason : %s' % err.rstrip())

        output = out.split("\n")
        line = output[1]
        line = " ".join(line.split())
        val = line.strip().split(" ")

        # creating VirtualMachine instance to return
        vm = VirtualMachine(val[0])
        vm.id = val[1]
        vm.memory = val[2]
        vm.vcpus = val[3]
        vm.state = val[4]
        vm.uptime = val[5]
        vm.vnc_port = None

        if not display_port is None:
            # The display server being used is SPICE
            vm.vnc_port = display_port
        else:
            # even though value of vnc port is set in the config file, if the port is already in use
            # by the vnc server, it allocates a new vnc port without throwing an error.
            # this additional step makes sure that we get the updated vnc-port
            #cmd = 'xenstore-read /local/domain/' + vm.id + '/console/vnc-port'
            #p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
            #out, err = p.communicate()
            #if not p.returncode == 0:
            #    raise Exception('ERROR : cannot start the vm - error while getting vnc-port. '
            #                    '\n Reason : %s' % err.rstrip())
            #vm.vnc_port = out.rstrip()
            with Client() as c:
                vm.vnc_port = c[b'/local/domain/{}/console/vnc-port'.format(vm.id)]

        if vm.vnc_port is None:
            raise Exception('ERROR : cannot start the vm - error while getting vnc-port.')

        logger.debug('Display Port for VM Id {} is {}'.format(vm.id, vm.vnc_port))
        return vm

    def vm_exists(self, vm_name):
        """
        checks if the specified vm exists or not
        :param vm_name: domain name of the vm
        :return: boolean based on if domain exists or not
        """
        logger.debug('Checking if VM {} exists'.format(vm_name))
        cmd = 'xl list ' + vm_name
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode == 0:
            logger.debug('Result :'+out.rstrip())
            return True
        else:
            return False

    def server_stats(self):
        pass

    def setup_vm(self, vm_name, base_vm, vif=None):
        """
        registers a new vm
        :param vm_name name of the new VM
        :param base_vm name of base vm qcow and conf
        :param vif virtual interface string for vm
        """
        logger.debug('Setting up VM - {}'.format(vm_name))
        VirtualMachine(vm_name).setup(base_vm, vif)

    def cleanup_vm(self, vm_name):
        """
        registers a new vm
        :param vm_name:
        """
        logger.debug('Cleaning VM - {}'.format(vm_name))
        VirtualMachine(vm_name).cleanup()

    def save_vm(self, vm_name):
        VirtualMachine(vm_name).save()

    def restore_vm(self, vm_name, base_vm):
        VirtualMachine(vm_name).restore(base_vm)

    def kill_zombie_vm(self, vm_id):
        VirtualMachine('zombie').kill_zombie_vms(vm_id)

    def create_bridge(self, name):
        logger.debug('Creating bridge - {}'.format(name))
        cmd = 'brctl addbr '+name
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            logger.error('Error while creating bridge - {}'.format(cmd))
            logger.error('Error while creating bridge - {}'.format(err.rstrip()))
            raise Exception('ERROR : cannot create the bridge. \n Reason : %s' % err.rstrip())
        else:
            logger.debug('Created bridge - {}'.format(name))
            logger.debug('Starting bridge - {}'.format(name))
            cmd = 'ifconfig ' + name + ' up'
            p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            if not p.returncode == 0:
                logger.error('Error while starting bridge - {}'.format(cmd))
                logger.error('Error while starting bridge - {}'.format(err.rstrip()))
                raise Exception('ERROR : cannot start the bridge. \n Reason : %s' % err.rstrip())
            logger.debug('Started bridge - {}'.format(name))

    def remove_bridge(self, name):
        logger.debug('Stopping bridge - {}'.format(name))
        cmd = 'ifconfig ' + name + ' down'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            if 'No such device' in err.rstrip():
                pass
            else:
                logger.error('Error while stopping bridge - {}'.format(cmd))
                logger.error('Error while stopping bridge - {}'.format(err.rstrip()))
                raise Exception('ERROR : cannot stop the bridge. \n Reason : %s' % err.rstrip())
        else:
            logger.debug('Stopped bridge - {}'.format(name))
            logger.debug('Removing bridge - {}'.format(name))
            cmd = 'brctl delbr ' + name
            p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            if not p.returncode == 0:
                if 'No such device' in err.rstrip():
                    pass
                else:
                    logger.error('Error while removing bridge - {}'.format(cmd))
                    logger.error('Error while removing bridge - {}'.format(err.rstrip()))
                    raise Exception('ERROR : cannot remove the bridge. \n Reason : %s' % err.rstrip())
            logger.debug('Removed bridge - {}'.format(name))

    def bridge_exists(self, name):
        logger.debug('Checking if bridge {} exists'.format(name))
        cmd = 'ip a show ' + name
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode == 0:
            if out.rstrip() == '' or 'does not exist' in out.rstrip():
                return False
            else:
                return True
        else:
            return False

    def is_bridge_up(self,name):
        logger.debug('Checking if bridge {} is up'.format(name))
        cmd = 'ip a show ' + name + ' up'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode == 0:
            if out.rstrip() == '' or 'does not exist' in out.rstrip():
                return False
            else:
                return True
        else:
            return False

    def listenToVMShutdown(self, dom_id):
        with Client() as c:
          # the sys.arg is the domid which is to be passed to the function call
          # dom_id = int(sys.argv[1])
          dom_name = c['/local/domain/{}/name'.format(dom_id)]
          user_id = dom_name.split('_')[0]
          vm_id = dom_name.split('_')[2]
          logger.debug('VM {}, {}'.format(user_id, vm_id))
          path = c.get_domain_path(dom_id)
          path = path + '/control/shutdown'
          api_key = config.get('Security', 'INTERNAL_API_KEY')
          logger.debug('{}: {}'.format(config.get("VITAL", "SERVER_NAME"), api_key))

          with c.monitor() as m:
            # watch for any random string
            m.watch(path, b'baz')
            logger.debug('Watching path {}'.format(path))
            next(m.wait())

            if next(m.wait()) is not None:
                logger.debug('Event on path {}'.format(path))
                params = {'api_key': api_key, 'user_id': user_id, 'vm_id': vm_id}

            requests.get('https://' + config.get("VITAL", "SERVER_NAME") + '/vital/users/release-vm/', params=params)

    def get_dom_details(self):
        """
        lists all vms in the server (output of xentop)
        :return List of VirtualMachine with name, state, cpu, memory and network details
        """
        logger.debug('Listing Xentop..')
        cmd = 'xentop -b -i1'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            raise Exception('ERROR : cannot list all the vms. \n Reason : %s' % err.rstrip())

        vms = []
        output = out.strip().split("\n")
        for i in range(1, len(output)):
            # removing first line
            line = output[i]
            line = " ".join(line.split())
            val = line.split(" ")

            # creating VirtualMachine instances to return
            vm = VirtualMachine(val[0])
            vm.state = val[1]
            vm.cpu_secs = val[2]
            vm.cpu_per = val[3]
            vm.mem = val[4]
            vm.mem_per = val[5]
            vm.vcpus = val[8]
            vm.nets = val[9]
            vms.append(vm)
        return vms


class VirtualMachine:
    """
    References virtual machines which Xen maintains
    """

    def __init__(self, name):
        self.name = name

    def get_free_tcp_port(self):
        """
        Starts a socket connection to grab a free port (Involves a race
            condition but will do for now)
        :return: An open port in the system
        """
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(('', 0))
        _, port = tcp.getsockname()
        tcp.close()
        return port

    def start(self, vm_options):
        """
        starts specified virtual machine
        :return: virtual machine stats with id, name, memory, vcpus, state, uptime, vnc_port
        """
        # Check if display server is to be spice if yes grab an open port and assign to spice port
        spice_port = None
        if vm_options:
            spice_port = self.get_free_tcp_port()
            vm_options = vm_options.replace('spiceport="0"', 'spiceport="{}"'.format(spice_port))

        cmd = 'xl create {}/{}.conf {}'.format(
            config.get("VMConfig", "VM_CONF_LOCATION"), self.name, vm_options)
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if p.returncode != 0:
            logger.error(' Error while starting VM - {}'.format(cmd))
            logger.error(err.rstrip())
            raise Exception('ERROR : cannot start the vm. \n Reason : %s' % err.rstrip())
        else:
            logger.debug('VM started - {}'.format(self.name))
            vm = XenAPI().list_vm(self.name, spice_port)

            # Start the Monitor Xen VM Script to watch the Xenstored Path
            # And let it run in the background we are not worried about collecting the results
            # cmd = '{} {}/monitor_XenVM.py {}'.format(
            #    sys.executable, os.path.dirname(os.path.realpath(__file__)), vm.id)
            # logger.debug('Watching VM with Xenstore {}'.format(cmd))
            # Popen(cmd.split(), close_fds=True)

            return vm

    def shutdown(self):
        """
        this forcefully shuts down the virtual machine
        :param vm_name name of the vm to be shutdown
        """
        # xl destroy is used to forcefully shut down the vm
        # xl shutdown gracefully shuts down the vm but does not guarantee the shutdown
        cmd = 'xl destroy '+self.name
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            if 'invalid domain identifier' in err.rstrip():
                logger.error(' Cannot find VM to be stopped - {}'.format(cmd))
                pass
            else:
                raise Exception('ERROR : cannot stop the vm '
                                '\n Reason : %s' % err.rstrip())
        logger.debug('VM stopped - {}'.format(self.name))

        # this is an additional step to deal with old
        # xen-traditional model. Can be removed later
        # self.kill_zombie_vms(self.id)

    #  This is an additional step to kill zombie VMs if the device model is set to
    #  qemu-traditional in xl conf. SET model to qemu-xen
    def kill_zombie_vms(self, vm_id):

        cmd = 'ps -ef | grep qemu-dm | grep "d ' + vm_id+'"'
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            logger.error(' Error while finding zombie VMs - {}'.format(cmd))
            raise Exception('ERROR : trying to find zombie vms. \n Reason : %s' % err.rstrip())

        output = out.split("\n")
        if len(output) > 2:
            cnt = 0

            line = output[0]
            # fix for when process id if grep is small than actual pid
            for out_line in output:
                if cmd not in out_line:
                    line = output[cnt]
                    break
                cnt += 1

            line = " ".join(line.split())
            val = line.strip().split(" ")
            cmd = 'kill ' + val[1]
            p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()

            if not p.returncode == 0:
                logger.error('Cannot kill zombie vms.\n Reason : %s' % (err.rstrip()))
                pass

    def setup(self, base_vm, vif):
        """
        registers a new vm for the student - creates qcow and required conf files
        :param base_vm: name of the base vm which is replicated
        :param vif : vif to be assigned to the vm
        """
        try:
            copyfile(config.get("VMConfig", "VM_DSK_LOCATION") + '/clean/' + base_vm + '.qcow',
                     config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.qcow')
            logger.debug('Setup qcow file for ' + self.name)
        except Exception as e:
            logger.error(' Error while creating new VM dsk - {}'.format(self.name))
            logger.error(str(e).rstrip())
            raise Exception('ERROR : cannot setup the vm - qcow '
                            '\n Reason : %s' % str(e).rstrip())

        try:
            copyfile(config.get("VMConfig", "VM_CONF_LOCATION") + '/clean/' + base_vm + '.conf',
                     config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf')
        except Exception as e:
            logger.error(' Error while creating VM conf - {}'.format(self.name))
            logger.error(str(e).rstrip())
            raise Exception('ERROR : cannot setup the vm - conf '
                            '\n Reason : %s' % str(e).rstrip())

        f = open(config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf', 'r')
        file_data = f.read()
        f.close()

        new_data = file_data.replace('<VM_NAME>', self.name)
        if vif is not None:
            new_data = new_data + '\nvif=[' + vif + ']'

        f = open(config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf', 'w')
        f.write(new_data)
        f.close()
        logger.debug('Setup conf file for ' + self.name)
        logger.debug('Finished setting up '+self.name)

    def cleanup(self):
        """
        un-registers vm for the student - removes qcow and required conf files
        """
        try:
            for filename in glob(config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.*'):
                os.remove(filename)
            logger.debug('Removed qcow file for ' + self.name)
        except Exception as e:
            logger.error(' Error while removing VM dsk - {}'.format(self.name))
            logger.error(str(e).rstrip())
            raise Exception('ERROR : cannot unregister the vm - qcow '
                            '\n Reason : %s' % str(e).rstrip())

        try:
            os.remove(config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf')
            logger.debug('Removed conf file for ' + self.name)
        except OSError as e:
            if e.errno != errno.ENOENT:
                logger.error(' Error while removing VM conf - {}'.format(self.name))
                logger.error(str(e).rstrip())
                raise Exception('ERROR : cannot unregister the vm - conf '
                                '\n Reason : %s' % str(e).rstrip())
        logger.debug('Finished removing ' + self.name)

    # TODO : IDEA :: Auto save - for forced VM shutdowns .autosaved
    def save(self):
        """
        saves the current state of vms to restore to in future
        """
        cmd = 'xl save -c ' + self.name + ' ' + config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.saved'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            logger.error(' Error while saving VM - {}'.format(cmd))
            raise Exception('ERROR : cannot create snapshot the vm \n Reason : %s' % err.rstrip())

    def restore(self, base_vm):
        """
        restores from previous saved state or rebases from clean files
        """
        if os.path.isfile(config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.saved'):
            cmd = 'xl restore ' + config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.saved'
            p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
            out, err = p.communicate()
            if not p.returncode == 0:
                logger.error(' Error while restoring VM - {}'.format(cmd))
                raise Exception('ERROR : cannot restore snapshot the vm \n Reason : %s' % err.rstrip())
        else:
            self.setup(base_vm)
