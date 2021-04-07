#!/usr/bin/env python

import argparse
import os
import subprocess
import tempfile


class VMCreate:
    """
    Create vbox VM of Ubuntu server from cloud image with the following steps:
        - grab the image, unless it exists in XDG_CACHE_HOME
        - convert it to raw, than to VDI, remove raw
        - resize it to the right size
        - create cloud ISO image with some basic bootstrap
        - create and register VM definition
        - tweak its params
        - move disk image to the Machine directory
        - attach disk and iso images to it
        - run and wait for initial bootstrap, than acpishutdown
        - detach iso image and remove it
    """
    CLOUD_IMAGE = "ci.iso"
    CLOUD_INIT_FINISHED_CMD = "test /var/lib/cloud/instance/boot-finished"
    CACHE_DIR = os.environ.get('XDG_CACHE_HOME',
                               os.path.expanduser('~/.cache'))

    def __init__(self, args):
        self.vm_name = args.name
        self.cpus = args.cpus
        self.memory = args.memory
        self.disk_size = args.disk_size
        self.ubuntu_version = args.version
        self._img = f"ubuntu-{self.ubuntu_version}-server-cloudimg-amd64.img"
        self._temp_path = None
        self._disk_img = self.vm_name + '.vdi'
        self._tmp = None

    def run(self):
        try:
            self._prepare_temp()
            self._download_image()
            # self._convert_and_resize()
        finally:
            self._cleanup()

    def _prepare_temp(self):
        self._tmp = tempfile.mkdtemp()

    def _checksum(self):
        expected_sum = None
        fname = 'SHA256SUMS'
        url = "https://cloud-images.ubuntu.com/releases/"
        url += f"{self.ubuntu_version}/release/{fname}"
        # TODO: make the verbosity switch be dependent from verbosity of the
        # script.
        subprocess.call(['wget', url, '-q', '-O',
                         os.path.join(self._tmp, fname)])

        with open(os.path.join(self._tmp, fname)) as fobj:
            for line in fobj.readlines():
                if self._img in line:
                    expected_sum = line.split(' ')[0]
                    break

        if not expected_sum:
            raise AttributeError('Cannot find provided cloud image')

        if os.path.exists(os.path.join(self.CACHE_DIR, self._img)):
            cmd = 'sha256sum ' + os.path.join(self.CACHE_DIR, self._img)
            calulated_sum = subprocess.getoutput(cmd).split(' ')[0]
            return calulated_sum == expected_sum

        return False

    def _download_image(self):
        if self._checksum():
            print(f'Image already downloaded: {self._img}')
            return

        url = "https://cloud-images.ubuntu.com/releases/"
        url += f"{self.ubuntu_version}/release/"
        img = f"ubuntu-{self.ubuntu_version}-server-cloudimg-amd64.img"
        url += img
        print(f'Downloading image {self._img}')
        subprocess.call(['wget', '-q', url, '-O',
                         os.path.join(self.CACHE_DIR, self._img)])

        if not self._checksum():
            # TODO: make some retry mechanism?
            raise AttributeError('Checksum for downloaded image differ from'
                                 ' expected')
        else:
            print(f'downloaded image {self._img}')

    def _cleanup(self):
        subprocess.call(['rm', '-fr', self._tmp])


def _create(args):
    return VMCreate(args).run()


def main():
    parser = argparse.ArgumentParser(description="Automate deployment and "
                                     "maintenance of Ubuntu VMs using "
                                     "VirtualBox and Ubuntu cloud images")
    subparsers = parser.add_subparsers(help='supported commands')
    create = subparsers.add_parser('create')
    create.add_argument('name')
    create.set_defaults(func=_create)
    create.add_argument('-m', '--memory', default=12288, type=int,
                        help="amount of memory in Megabytes, default 12GB")
    create.add_argument('-c', '--cpus', default=6, type=int,
                        help="amount of CPUs to be configured. Default 6.")
    create.add_argument('-d', '--disk-size', default=20480, type=int,
                        help="disk size to be expanded to. By default to 20GB")
    create.add_argument('-v', '--version', default="18.04",
                        help="Ubuntu server version. Default 18.04")

    completion = subparsers.add_parser('completion')
    completion.add_argument('shell', choices=['bash'],
                            help="pick shell to generate completions for")

    args = parser.parse_args()

    try:
        return args.func(args)
    except AttributeError:
        parser.print_help()
        parser.exit()


if __name__ == '__main__':
    main()
