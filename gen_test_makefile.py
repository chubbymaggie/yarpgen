#!/usr/bin/python3
###############################################################################
#
# Copyright (c) 2015-2016, Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
###############################################################################
# This scripts creates Test_Makefile, basing on configuration file
###############################################################################

import argparse
import logging
import os
import sys
import re

import common

Test_Makefile_name = "Test_Makefile"
license_file_name = "LICENSE.txt"
check_isa_file_name = "check_isa.cpp"
default_test_sets_file_name = "test_sets.txt"

default_config_file = "test_sets.txt"
comp_specs_line = "Compiler specs:"
spec_list_len = 4
test_sets_line = "Testing sets:"
set_list_len = 5

###############################################################################
# Section for Test_Makefile parameters


class MakefileVariable:
    """A special class, which should link together name and value of parameters"""
    def __init__(self, name, value):
        self.name = name
        self.value = value

# I can't use build-in dictionary, because variables should be ordered
Makefile_variable_list = []

cxx_flags = MakefileVariable("CXXFLAGS", "-std=c++11")
Makefile_variable_list.append(cxx_flags)

ld_flags = MakefileVariable("LDFLAGS", "-std=c++11")
Makefile_variable_list.append(ld_flags)

sources = MakefileVariable("SOURCES", "init.cpp driver.cpp func.cpp check.cpp hash.cpp")
Makefile_variable_list.append(sources)

headers = MakefileVariable("HEADERS", "init.h")
Makefile_variable_list.append(headers)

executable = MakefileVariable("EXECUTABLE", "out")
Makefile_variable_list.append(executable)
# Makefile_variable_list.append(Makefile_variable("",""))

###############################################################################
# Section for sde


class SdeTarget (object):
    all_sde_targets = []

    def __init__(self, name, enum_value):
        self.name = name
        self.enum_value = enum_value
        SdeTarget.all_sde_targets.append(self)

SdeArch = dict()
# This list should be ordered!
SdeArch["p4"]  = SdeTarget("p4" , 0)
SdeArch["p4p"] = SdeTarget("p4p", 1)
SdeArch["mrm"] = SdeTarget("mrm", 2)
SdeArch["pnr"] = SdeTarget("pnr", 3)
SdeArch["nhm"] = SdeTarget("nhm", 4)
SdeArch["wsm"] = SdeTarget("wsm", 5)
SdeArch["snb"] = SdeTarget("snb", 6)
SdeArch["ivb"] = SdeTarget("ivb", 7)
SdeArch["hsw"] = SdeTarget("hsw", 8)
SdeArch["bdw"] = SdeTarget("bdw", 9)
SdeArch["skx"] = SdeTarget("skx", 10)
SdeArch["knl"] = SdeTarget("knl", 11)
SdeArch[""] = SdeTarget("", 12)  # It is a fake target and it should always be the last


def define_sde_arch(native, target):
    if target == SdeArch["skx"] and native != SdeArch["skx"]:
        return SdeArch["skx"].name
    if target == SdeArch["knl"] and native != SdeArch["knl"]:
        return SdeArch["knl"].name
    if native.enum_value < target.enum_value:
        return target.name
    return ""

###############################################################################
# Section for targets


class CompilerSpecs (object):
    all_comp_specs = dict()

    def __init__(self, name, exec_name, common_args, arch_prefix):
        self.name = name
        self.comp_name = exec_name
        self.common_args = common_args
        self.arch_prefix = arch_prefix
        self.version = "unknown"
        CompilerSpecs.all_comp_specs[name] = self

    def set_version(self, version):
        self.version = version


class Arch (object):
    def __init__(self, comp_name, sde_arch):
        self.comp_name = comp_name
        self.sde_arch = sde_arch


class CompilerTarget (object):
    all_targets = []

    def __init__(self, name, specs, target_args, arch):
        self.name = name
        self.specs = specs
        self.args = specs.common_args + " " + target_args
        self.arch = arch
        CompilerTarget.all_targets.append(self)


###############################################################################
# Section for config parser

def skip_line(line):
    return line.startswith("#") or re.match(r'^\s*$', line)


def check_config_list(config_list, fixed_len, message):
    common.log_msg(logging.DEBUG, "Adding config list: " + str(config_list))
    if len(config_list) < fixed_len:
        common.print_and_exit(message + str(config_list))
    config_list = [x.strip() for x in config_list]
    return config_list


def add_specs(spec_list):
    spec_list = check_config_list(spec_list, spec_list_len, "Error in spec string, check it: ")
    try:
        CompilerSpecs(spec_list[0], spec_list[1], spec_list[2], spec_list[3])
        common.log_msg(logging.DEBUG, "Finished adding compiler spec")
    except KeyError:
        common.print_and_exit("Can't find key!")


def add_sets(set_list):
    set_list = check_config_list(set_list, set_list_len, "Error in set string, check it: ")
    try:
        CompilerTarget(set_list[0], CompilerSpecs.all_comp_specs[set_list[1]], set_list[2],
                       Arch(set_list[3], SdeArch[set_list[4]]))
        common.log_msg(logging.DEBUG, "Finished adding testing set")
    except KeyError:
        common.print_and_exit("Can't find key!")


def read_compiler_specs(config_iter, function, next_section_name=""):
    for config_line in config_iter:
        if skip_line(config_line):
            continue
        if next_section_name != "" and config_line.startswith(next_section_name):
            return
        specs = config_line.split("|")
        function(specs)


def parse_config(file_name):
    config_file = common.check_and_open_file(file_name, "r")
    config = config_file.read().splitlines()
    config_file.close()
    if not any(s.startswith(comp_specs_line) for s in config) or not any(s.startswith(test_sets_line) for s in config):
        common.print_and_exit("Invalid config file! Check it!")
    config_iter = iter(config)
    for config_line in config_iter:
        if skip_line(config_line):
            continue
        if config_line.startswith(comp_specs_line):
            read_compiler_specs(config_iter, add_specs, test_sets_line)
            read_compiler_specs(config_iter, add_sets)

###############################################################################


def detect_native_arch():
    check_isa_file = os.path.abspath(common.yarpgen_home + os.sep + check_isa_file_name)
    check_isa_binary = os.path.abspath(common.yarpgen_home + os.sep + check_isa_file_name.replace(".cpp", ""))

    sys_compiler = ""
    for key in CompilerSpecs.all_comp_specs:
        exec_name = CompilerSpecs.all_comp_specs[key].comp_name
        if common.if_exec_exist(exec_name):
            sys_compiler = exec_name
            break
    if sys_compiler == "":
        common.print_and_exit("Can't find any compiler")

    if not common.if_exec_exist(check_isa_binary):
        if not os.path.exists(check_isa_file):
            common.print_and_exit("Can't find " + check_isa_file)
        ret_code, output, err_output, time_expired, elapsed_time = \
            common.run_cmd([sys_compiler, check_isa_file, "-o", check_isa_binary], None, 0)
        if ret_code != 0:
            common.print_and_exit("Can't compile " + check_isa_file + ": " + str(err_output, "utf-8"))

    ret_code, output, err_output, time_expired, elapsed_time = common.run_cmd([check_isa_binary], None, 0)
    if ret_code != 0:
        common.print_and_exit("Error while executing " + check_isa_binary)
    native_arch_str = str(output, "utf-8").split()[0]
    for sde_target in SdeTarget.all_sde_targets:
        if sde_target.name == native_arch_str:
            return sde_target
    common.print_and_exit("Can't detect system ISA")


def gen_makefile(out_file_name, force, config_file, only_target=None, inject_blame_opt=None):
    # Somebody can prepare test specs and target, so we don't need to parse config file
    if config_file is not None:
        parse_config(config_file)
    output = ""
    license_file = common.check_and_open_file(os.path.abspath(common.yarpgen_home + os.sep + license_file_name), "r")
    for license_str in license_file:
        output += "#" + license_str
    license_file.close()
    output += "###############################################################################\n" 

    output += "#This file was generated automatically.\n"
    output += "#If you want to make a permanent changes, you should edit gen_test_makefile.py\n"
    output += "###############################################################################\n\n"

    for makefile_variable in Makefile_variable_list:
        output += makefile_variable.name + "=" + makefile_variable.value + "\n"
    output += "\n"

    for target in CompilerTarget.all_targets:
        if only_target is not None and only_target.name != target.name:
            continue
        output += target.name + ": " + "COMPILER=" + target.specs.comp_name + "\n"
        output += target.name + ": " + "OPTFLAGS=" + target.args
        if target.arch.comp_name != "":
            output += " " + target.specs.arch_prefix + target.arch.comp_name
        output += "\n"
        if inject_blame_opt is not None:
            output += target.name + ": " + "BLAMEOPTS=" + inject_blame_opt + "\n"
        output += target.name + ": " + "EXECUTABLE=" + target.name + "_" + executable.value + "\n"
        output += target.name + ": " + "$(addprefix " + target.name + "_, $(SOURCES:.cpp=.o))\n"
        output += "\t" + "$(COMPILER) $(LDFLAGS) $(OPTFLAGS) -o $(EXECUTABLE) $^\n\n" 

    # Force make to rebuild everything
    # TODO: replace with PHONY
    output += "FORCE:\n\n"
    
    for source in sources.value.split():
        source_name = source.split(".")[0]
        output += "%" + source_name + ".o: " + source + " FORCE\n"
        output += "\t" + "$(COMPILER) $(CXXFLAGS) $(OPTFLAGS) -o $@ -c $<"
        if inject_blame_opt is not None and source_name == "func":
            output += " $(BLAMEOPTS)"
        output += "\n\n"

    output += "clean:\n"
    output += "\trm *.o *_$(EXECUTABLE)\n\n"

    native_arch = detect_native_arch()
    for target in CompilerTarget.all_targets:
        if only_target is not None and only_target.name != target.name:
            continue
        output += "run_" + target.name + ": " + target.name + "_" + executable.value + "\n"
        output += "\t" 
        required_sde_arch = define_sde_arch(native_arch, target.arch.sde_arch)
        if required_sde_arch != "":
            output += "sde -" + required_sde_arch + " -- "
        output += "." + os.sep + target.name + "_" + executable.value + "\n\n"

    out_file = None
    if not os.path.isfile(out_file_name):
        out_file = open(out_file_name, "w")
    else:
        if force:
            out_file = open(out_file_name, "w")
        else:
            common.print_and_exit("File already exists. Use -f if you want to rewrite it.")
    out_file.write(output)
    out_file.close()

###############################################################################

if __name__ == '__main__':
    if os.environ.get("YARPGEN_HOME") is None:
        sys.stderr.write("\nWarning: please set YARPGEN_HOME envirnoment variable to point to test generator path, "
                         "using " + common.yarpgen_home + " for now\n")

    description = 'Generator of Test_Makefiles.'
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config-file", dest="config_file",
                        default=os.path.join(common.yarpgen_home, default_test_sets_file_name), type=str,
                        help="Configuration file for testing")
    parser.add_argument("-o", "--output", dest="out_file", default=Test_Makefile_name, type=str,
                        help="Output file")
    parser.add_argument("-f", "--force", dest="force", default=False, action="store_true",
                        help="Rewrite output file")
    parser.add_argument("-v", "--verbose", dest="verbose", default=False, action="store_true",
                        help="Increase output verbosity")
    parser.add_argument("--log-file", dest="log_file", type=str,
                        help="Logfile")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    common.setup_logger(args.log_file, log_level)

    common.check_python_version()
    gen_makefile(os.path.abspath(args.out_file), args.force, args.config_file)
