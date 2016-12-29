from subprocess import Popen, PIPE
from shutil import copyfile
from glob import glob
import os, errno
import ConfigParser
import logging

config = ConfigParser.ConfigParser()

# TODO change this to a common config file on a shared location
config.read("/home/vlab/config.ini")

# TODO change the logging level and file name to be read from config file
logging.basicConfig(filename='/home/vlab/log/xen-api.log',
                    level=logging.DEBUG, format='%(asctime)s-%(levelname)s:%(message)s')


class XenAPI:
    """
    Provides api to xen operations
    """

    def __init__(self):
        pass

    def start_vm(self, vm_name):
        """
        starts specified virtual machine
        :param vm_name name of virtual machine
        """
        logging.debug('Starting VM - {}'.format(vm_name))
        return VirtualMachine(vm_name).start()

    def stop_vm(self, vm_name):
        """
        stops the specified vm
        :param vm_name: name of the vm to be stopped
        """
        try:
            logging.debug('Stopping VM - {}'.format(vm_name))
            vm = self.list_vm(vm_name)
            vm.shutdown()
        except Exception:
            logging.exception("Error while shutting down VM - {}".format(vm_name))
            pass

    def list_all_vms(self):
        """
        lists all vms in the server (output of xl list)
        :return List of VirtualMachine with id, name, memory, vcpus, state, uptime
        """
        logging.debug('Listing all VMs..')
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

    def list_vm(self, vm_name):
        """
        lists specified virtual machine (output of xl list vm_name)
        :param vm_name name of virtual machine
        :return VirtualMachine with id, name, memory, vcpus, state, uptime
        """
        logging.debug('Listing VM {}'.format(vm_name))
        cmd = 'xl list '+vm_name
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
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

        # even though value of vnc port is set in the config file, if the port is already in use
        # by the vnc server, it allocates a new vnc port without throwing an error. this additional
        # step makes sure that we get the updated vnc-port
        cmd = 'xenstore-read /local/domain/' + vm.id + '/console/vnc-port'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            raise Exception('ERROR : cannot start the vm - error while getting vnc-port. '
                            '\n Reason : %s' % err.rstrip())
        vm.vnc_port = out.rstrip()
        return vm

    def server_stats(self):
        pass

    def setup_vm(self, vm_name, base_vm, vif=None):
        """
        registers a new vm
        :param vm_name name of the new VM
        :param base_vm name of base vm qcow and conf
        :param vif virtual interface string for vm
        """
        VirtualMachine(vm_name).setup(base_vm, vif)

    def cleanup_vm(self, vm_name):
        """
        registers a new vm
        :param vm_name:
        """
        VirtualMachine(vm_name).cleanup()

    def save_vm(self, vm_name):
        VirtualMachine(vm_name).save()

    def restore_vm(self, vm_name, base_vm):
        VirtualMachine(vm_name).restore(base_vm)

    def kill_zombie_vm(self, vm_id):
        VirtualMachine('zombie').kill_zombie_vms(vm_id)


class VirtualMachine:
    """
    References virtual machines which Xen maintains
    """

    def __init__(self, name):
        self.name = name

    def start(self):
        """
        starts specified virtual machine
        :return: virtual machine stats with id, name, memory, vcpus, state, uptime, vnc_port
        """
        cmd = 'xl create ' + config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            logging.error(' Error while starting VM - {}'.format(cmd))
            raise Exception('ERROR : cannot start the vm. \n Reason : %s' % err.rstrip())
        else:
            return XenAPI().list_vm(self.name)

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
            # silently ignore if vm is already destroyed
            if 'invalid domain identifier' not in err.rstrip():
                logging.error(' Cannot find VM to be stopped - {}'.format(cmd))
                raise Exception('ERROR : cannot stop the vm '
                                '\n Reason : %s' % err.rstrip())

        # this is an additional step to deal with old
        # xen-traditional model. Can be removed later
        self.kill_zombie_vms(self.id)

    #  This is an additional step to kill zombie VMs if the device model is set to
    #  qemu-traditional in xl conf. SET model to qemu-xen
    def kill_zombie_vms(self, vm_id):

        cmd = 'ps -ef | grep qemu-dm | grep "d ' + vm_id+'"'
        p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            logging.error(' Error while finding zombie VMs - {}'.format(cmd))
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
                logging.error('Cannot kill zombie vms.\n Reason : %s' % (err.rstrip()))
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
        except Exception as e:
            logging.error(' Error while creating new VM dsk - {}'.format(self.name))
            raise Exception('ERROR : cannot setup the vm - qcow '
                            '\n Reason : %s' % str(e).rstrip())

        try:
            copyfile(config.get("VMConfig", "VM_CONF_LOCATION") + '/clean/' + base_vm + '.conf',
                     config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf')
        except Exception as e:
            logging.error(' Error while creating VM conf - {}'.format(self.name))
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

    def cleanup(self):
        """
        un-registers vm for the student - removes qcow and required conf files
        """
        try:
            for filename in glob(config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.*'):
                os.remove(filename)
        except Exception as e:
            logging.error(' Error while removing VM dsk - {}'.format(self.name))
            raise Exception('ERROR : cannot unregister the vm - qcow '
                            '\n Reason : %s' % str(e).rstrip())

        try:
            os.remove(config.get("VMConfig", "VM_CONF_LOCATION") + '/' + self.name + '.conf')
        except OSError as e:
            if e.errno != errno.ENOENT:
                logging.error(' Error while removing VM conf - {}'.format(self.name))
                raise Exception('ERROR : cannot unregister the vm - conf '
                                '\n Reason : %s' % str(e).rstrip())

    # TODO : IDEA :: Auto save - for forced VM shutdowns .autosaved
    def save(self):
        """
        saves the current state of vms to restore to in future
        """
        cmd = 'xl save -c ' + self.name + ' ' + config.get("VMConfig", "VM_DSK_LOCATION") + '/' + self.name + '.saved'
        p = Popen(cmd.split(), stdout=PIPE, stderr=PIPE)
        out, err = p.communicate()
        if not p.returncode == 0:
            logging.error(' Error while saving VM - {}'.format(cmd))
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
                logging.error(' Error while restoring VM - {}'.format(cmd))
                raise Exception('ERROR : cannot restore snapshot the vm \n Reason : %s' % err.rstrip())
        else:
            self.setup(base_vm)
