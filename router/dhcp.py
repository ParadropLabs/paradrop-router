import ipaddress
import os

from . import pdosq

from .base import ConfigObject, ConfigOption
from .command import Command, KillCommand, FunctionCommand


class ConfigDhcp(ConfigObject):
    typename = "dhcp"

    options = [
        ConfigOption(name="interface", required=True),
        ConfigOption(name="leasetime"),
        ConfigOption(name="limit", type=int),
        ConfigOption(name="start", type=int),
        ConfigOption(name="dhcp_option", type=list, default=[]),

        # Non-standard options:
        #
        # relay: comma-separated string, specifying a DHCP relay, as with
        #        "<local address>,<server address>[,<interface>]".
        #        Refer to --dhcp-relay in man dnsmasq.
        ConfigOption(name="relay", type=list, default=[])
    ]


class ConfigDomain(ConfigObject):
    typename = "domain"

    options = [
        ConfigOption(name="name", type=str),
        ConfigOption(name="ip", type=str)
    ]

    def getName(self):
        return self.name


class ConfigHost(ConfigObject):
    typename = "domain"

    options = [
        ConfigOption(name="ip", type=str),
        ConfigOption(name="mac", type=str),
        ConfigOption(name="hostid", type=str),
        ConfigOption(name="duid", type=str),
        ConfigOption(name="name", type=str),
        ConfigOption(name="tag", type=str),
        ConfigOption(name="match_tag", type=list, default=[]),
        ConfigOption(name="dns", type=bool, default=False),
        ConfigOption(name="broadcast", type=bool, default=False),
        ConfigOption(name="leasetime", type=str),
        ConfigOption(name="instance", type=str)
    ]

    def getDnsmasqConfOptions(self):
        parts = []
        if self.mac:
            parts.append(self.mac)
        if self.name:
            parts.append(self.name)
        if self.ip:
            parts.append(self.ip)
        if self.leasetime:
            parts.append(self.leasetime)
        return ",".join(parts)


class ConfigDnsmasq(ConfigObject):
    typename = "dnsmasq"

    options = [
        ConfigOption(name="authoritative", type=bool, default=True),
        ConfigOption(name="cachesize", type=int, default=150),
        ConfigOption(name="dhcp_boot"),
        ConfigOption(name="dhcpleasemax", type=int, default=1000),
        ConfigOption(name="domain", type=str),
        ConfigOption(name="enable_tftp", type=bool, default=False),
        ConfigOption(name="expandhosts", type=bool, default=True),
        ConfigOption(name="interface", type=list),
        ConfigOption(name="leasefile", type=str),
        ConfigOption(name="noresolv", type=bool, default=False),
        ConfigOption(name="server", type=list),
        ConfigOption(name="tftp_root")
    ]

    def apply(self, allConfigs):
        commands = list()

        # visibleName will be used in choosing file names for this dnsmasq
        # instance, must be unique if there are multiple dnsmasq instances
        visibleName = self.internalName

        if self.interface is None:
            interfaces = []
            for section in self.findByType(allConfigs, "dhcp", "dhcp"):
                interfaces.append(section.interface)
        else:
            interfaces = self.interface

        self.__leasefile = self.leasefile
        if self.__leasefile is None:
            self.__leasefile = "{}/dnsmasq-{}.leases".format(
                self.manager.writeDir, visibleName)
        pdosq.makedirs(os.path.dirname(self.__leasefile))

        pidFile = "{}/dnsmasq-{}.pid".format(
            self.manager.writeDir, visibleName)
        pdosq.makedirs(os.path.dirname(pidFile))

        outputPath = "{}/dnsmasq-{}.conf".format(
            self.manager.writeDir, visibleName)
        pdosq.makedirs(os.path.dirname(outputPath))

        with open(outputPath, "w") as outputFile:
            outputFile.write("#" * 80 + "\n")
            outputFile.write("# dnsmasq configuration file generated by "
                             "pdconfd\n")
            outputFile.write("# Source: {}\n".format(self.source))
            outputFile.write("# Section: {}\n".format(str(self)))
            outputFile.write("#" * 80 + "\n")
            outputFile.write("\n")
            outputFile.write("dhcp-leasefile={}\n".format(self.__leasefile))

            if self.authoritative:
                outputFile.write("dhcp-authoritative\n")
            outputFile.write("cache-size={}\n".format(self.cachesize))
            if self.dhcp_boot is not None:
                outputFile.write("dhcp-boot={}\n".format(self.dhcp_boot))
            outputFile.write("dhcp-lease-max={}\n".format(self.dhcpleasemax))
            if self.domain:
                outputFile.write("domain={}\n".format(self.domain))
            if self.enable_tftp:
                outputFile.write("enable-tftp\n")
            if self.expandhosts:
                outputFile.write("expand-hosts\n")
            if self.noresolv:
                outputFile.write("no-resolv\n")
            if self.tftp_root is not None:
                outputFile.write("tftp-root={}\n".format(self.tftp_root))

            if self.server:
                for server in self.server:
                    outputFile.write("server={}\n".format(server))

            # TODO: Bind interfaces allows us to have multiple instances of
            # dnsmasq running, but it would probably be better to have one
            # running and reconfigure it when we want to add or remove
            # interfaces.  It is not very disruptive to reconfigure and restart
            # dnsmasq.
            outputFile.write("\n")
            outputFile.write("except-interface=lo\n")
            outputFile.write("bind-interfaces\n")

            for intfName in interfaces:
                interface = self.lookup(allConfigs, "network", "interface", intfName)
                outputFile.write("\n")
                outputFile.write("# Options for section interface {}\n".
                                 format(interface.name))
                outputFile.write("interface={}\n".format(
                                 interface.config_ifname))

                network = ipaddress.IPv4Network(u"{}/{}".format(
                    interface.ipaddr, interface.netmask), strict=False)

                dhcp = self.lookup(allConfigs, "dhcp", "dhcp", intfName)

                outputFile.write("\n")
                outputFile.write("# Options for section dhcp {}\n".
                                 format(interface.name))

                if None not in [dhcp.start, dhcp.limit, dhcp.leasetime]:
                    # TODO: Error checking!
                    firstAddress = network.network_address + dhcp.start
                    lastAddress = firstAddress + dhcp.limit

                    outputFile.write("dhcp-range={},{},{},{}\n".format(
                        str(firstAddress), str(lastAddress), interface.netmask,
                        dhcp.leasetime))

                # Write options sections to the config file.
                for option in dhcp.dhcp_option:
                    outputFile.write("dhcp-option={}\n".format(option))

                for relay in dhcp.relay:
                    outputFile.write("dhcp-relay={}\n".format(relay))
                if dhcp.relay:
                    outputFile.write("dhcp-proxy\n")

            outputFile.write("\n")

            for domain in self.findByType(allConfigs, "dhcp", "domain"):
                outputFile.write("address=/{}/{}\n".format(domain.name, domain.ip))

            outputFile.write("\n")

            for host in self.findByType(allConfigs, "dhcp", "host"):
                outputFile.write("dhcp-host={}\n".format(host.getDnsmasqConfOptions()))

        cmd = ["dnsmasq", "--conf-file={}".format(outputPath),
               "--pid-file={}".format(pidFile)]
        commands.append((self.PRIO_START_DAEMON, Command(cmd, self)))

        self.pidFile = pidFile
        return commands

    def revert(self, allConfigs):
        commands = list()

        commands.append((-self.PRIO_START_DAEMON,
            KillCommand(self.pidFile, self)))

        # Clean up leases and pid files.
        commands.append((-self.PRIO_START_DAEMON,
            FunctionCommand(self, pdosq.safe_remove, self.__leasefile)))
        commands.append((-self.PRIO_START_DAEMON,
            FunctionCommand(self, pdosq.safe_remove, self.pidFile)))

        return commands
